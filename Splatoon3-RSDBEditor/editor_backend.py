import os
import sys
import subprocess
import re
import copy
import queue
import threading
import itertools
from collections import Counter
import requests
from requests.adapters import HTTPAdapter

import zstandard as zstd
import byml

from PyQt6.QtWidgets import QFileDialog, QMessageBox
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from translations import t
from components import WECheckWorker, WEDownloadWorker
from utils import (log, get_last_rsdb_dir, set_last_rsdb_dir, get_last_save_dir, 
                   set_last_save_dir, CACHE_DIR)
from tree_handler import TreeHandler

class ProgressiveCacheWorker(QThread):
    progress = pyqtSignal(int, int)
    image_loaded = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, missing_images, url_resolver, priority_count=0):
        super().__init__()
        self.missing_images = missing_images
        self.url_resolver = url_resolver
        self.priority_count = priority_count
        self.is_cancelled = False
        
        self.task_queue = queue.PriorityQueue()
        self.counter = itertools.count()
        self.lock = threading.Lock()
        self.completed_set = set()
        self.in_progress_set = set()
        self.total_count = len(missing_images)
        self.completed_count = 0

    def prioritize(self, img_name):
        with self.lock:
            if img_name in self.completed_set or img_name in self.in_progress_set:
                return
            self.task_queue.put((0, next(self.counter), img_name))

    def run(self):
        if self.total_count == 0:
            self.finished.emit()
            return

        session = requests.Session()
        adapter = HTTPAdapter(pool_connections=16, pool_maxsize=16, max_retries=1)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        for idx, img in enumerate(self.missing_images):
            priority_level = 1 if idx < self.priority_count else 2
            self.task_queue.put((priority_level, next(self.counter), img))

        def worker_loop():
            while not self.is_cancelled:
                try:
                    prio, _, img_name = self.task_queue.get(timeout=0.2)
                except queue.Empty:
                    with self.lock:
                        if self.completed_count >= self.total_count:
                            break
                    continue

                with self.lock:
                    if img_name in self.completed_set:
                        self.task_queue.task_done()
                        continue
                    self.in_progress_set.add(img_name)

                urls = self.url_resolver(img_name)
                local_path = os.path.join(CACHE_DIR, img_name)
                success = False

                for url in urls:
                    if self.is_cancelled:
                        break
                    try:
                        resp = session.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
                        if resp.status_code == 200 and len(resp.content) > 0:
                            with open(local_path, 'wb') as f:
                                f.write(resp.content)
                            success = True
                            break
                    except Exception:
                        pass

                with self.lock:
                    self.in_progress_set.discard(img_name)
                    if img_name not in self.completed_set:
                        self.completed_set.add(img_name)
                        self.completed_count += 1
                    cur_completed = self.completed_count

                self.task_queue.task_done()

                if success:
                    self.image_loaded.emit(img_name)
                self.progress.emit(cur_completed, self.total_count)

        threads = []
        for _ in range(10):
            t_thread = threading.Thread(target=worker_loop)
            t_thread.daemon = True
            t_thread.start()
            threads.append(t_thread)

        for t_thread in threads:
            t_thread.join()

        try:
            session.close()
        except Exception:
            pass
        self.finished.emit()

    def cancel(self):
        self.is_cancelled = True

class EditorBackendMixin:
    def open_rsdb_folder(self):
        last_dir = get_last_rsdb_dir()
        folder_path = QFileDialog.getExistingDirectory(self, t("btn_open"), last_dir)
        if not folder_path: return
            
        rsdb_subfolder = os.path.join(folder_path, "RSDB")
        if os.path.isdir(rsdb_subfolder):
            folder_path = rsdb_subfolder
        else:
            try:
                for item in os.listdir(folder_path):
                    if item.lower() == "rsdb" and os.path.isdir(os.path.join(folder_path, item)):
                        folder_path = os.path.join(folder_path, item)
                        break
            except Exception as e:
                log(f"[RSDB] Error searching for RSDB subfolder: {e}")

        set_last_rsdb_dir(folder_path)
        self.current_folder_path = folder_path
        self.estimate_and_display_version(folder_path)
        
        self._saved_splitter_sizes = self.splitter.sizes()
        self.load_rsdb_files(folder_path)

    def load_rsdb_files(self, folder_path):
        self.rsdb_data.clear()
        self.original_rsdb_data.clear()
        self.modified_files.clear()
        self.tree_item_cache.clear()
        
        self.weapon_main_file = None
        self.weapon_sub_file = None
        self.weapon_special_file = None
        self.badge_file = None
        
        dctx = zstd.ZstdDecompressor()
        
        for file in os.listdir(folder_path):
            if file.endswith(".rstbl.byml.zs"):
                filepath = os.path.join(folder_path, file)
                try:
                    with open(filepath, 'rb') as f:
                        compressed_data = f.read()
                    
                    decompressed_data = dctx.decompress(compressed_data)
                    byml_obj = byml.Byml(decompressed_data)
                    parsed_data = byml_obj.parse()
                    
                    self.rsdb_data[file] = parsed_data
                    self.original_rsdb_data[file] = copy.deepcopy(parsed_data)
                    
                    if file.startswith("WeaponInfoMain.Product."): self.weapon_main_file = file
                    elif file.startswith("WeaponInfoSub.Product."): self.weapon_sub_file = file
                    elif file.startswith("WeaponInfoSpecial.Product."): self.weapon_special_file = file
                    elif file.startswith("BadgeInfo.Product."): self.badge_file = file
                    
                except Exception as e:
                    log(f"[RSDB] Error loading {file}: {e}")

        versions_found = set()
        for target_file in [self.weapon_main_file, self.weapon_sub_file, self.weapon_special_file]:
            if target_file:
                match = re.search(r'\.([0-9a-fA-F]{3})\.rstbl\.byml\.zs$', target_file)
                if match:
                    versions_found.add(match.group(1))

        if len(versions_found) > 1:
            QMessageBox.warning(self, t("err_version_mismatch_title"), t("err_version_mismatch_desc", ", ".join(versions_found)))
            
        missing_parts = []
        if not self.weapon_sub_file: missing_parts.append("WeaponInfoSub.Product.XXX.rstbl.byml.zs")
        if not self.weapon_special_file: missing_parts.append("WeaponInfoSpecial.Product.XXX.rstbl.byml.zs")
        
        if not self.weapon_main_file:
            pass
        elif missing_parts:
            QMessageBox.warning(self, t("err_missing_files_title"), t("err_missing_files_desc", "\n- ".join(missing_parts)))

        self.start_global_cache()

    def save_rsdb_folder(self):
        if not self.rsdb_data or not self.current_folder_path: return
            
        if not self.is_easy_mode and self.current_table_name and isinstance(self.current_table_name, str):
            self.rsdb_data[self.current_table_name] = TreeHandler.build_dict(self.tree_w.invisibleRootItem())
            self.modified_files.add(self.current_table_name)
            
        if not self.modified_files:
            QMessageBox.information(self, t("success_title"), t("msg_no_modifications"))
            return

        out_dir = QFileDialog.getExistingDirectory(self, t("btn_save"), get_last_save_dir())
        if not out_dir: return
        set_last_save_dir(out_dir)
            
        cctx = zstd.ZstdCompressor()
        saved_count = 0
        
        for file_name in self.modified_files:
            if file_name not in self.rsdb_data: continue
            
            ui_data = self.rsdb_data[file_name]
            try:
                try:
                    writer = byml.Writer(ui_data, be=False, version=7)
                    binary_data = writer.get_bytes()
                except AttributeError:
                    binary_data = byml.Byml(ui_data).get_bytes()
                    
                compressed_data = cctx.compress(binary_data)
                out_path = os.path.join(out_dir, file_name)
                with open(out_path, 'wb') as f:
                    f.write(compressed_data)
                    
                self.original_rsdb_data[file_name] = copy.deepcopy(ui_data)
                saved_count += 1
            except Exception as e:
                log(f"[RSDB] Error saving {file_name}: {e}")
                QMessageBox.critical(self, t("err_title"), t("err_save_failed", file_name, str(e)))
                return
                
        if saved_count > 0:
            self.modified_files.clear()
            QMessageBox.information(self, t("success_title"), t("msg_save_success_count", saved_count))
        else:
            QMessageBox.information(self, t("success_title"), t("msg_no_modifications"))

    def estimate_and_display_version(self, folder_path):
        codes = []
        try:
            for file in os.listdir(folder_path):
                match = re.search(r'\.([0-9a-fA-F]{3})\.rstbl\.byml\.zs$', file)
                if match: codes.append(match.group(1))
        except: pass
            
        if not codes:
            self.version_lbl.setText(t("msg_no_version"))
            return
            
        most_common_code = Counter(codes).most_common(1)[0][0]
        try:
            major, minor, patch = int(most_common_code[0], 16), int(most_common_code[1], 16), int(most_common_code[2], 16)
            est_version = f"{major}.{minor}.{patch}"
        except:
            est_version = most_common_code
        self.version_lbl.setText(t("msg_version_estimate", est_version))

    def get_image_urls(self, img_filename):
        if img_filename == "Dummy.png": 
            return ["https://leanny.github.io/splat3/images/subspe/Dummy.png"]
        elif img_filename == "Wsb_SalmonBuddy00.png" or img_filename == "SakelienSmall.png": 
            return ["https://github.com/JeremKOYTB/Splatoon3-RSDBEditor/blob/main/cache/Wsb_SalmonBuddy00.png?raw=true"]
        elif img_filename == "Wsp_SpDroneBuddySdodr00.png": 
            return ["https://github.com/JeremKOYTB/Splatoon3-RSDBEditor/blob/main/cache/Wsp_SpDroneBuddySdodr00.png?raw=true"]
        elif img_filename == "Wsp_Shachihoko.png": 
            return ["https://leanny.github.io/splat3/images/weapon/Wsp_Shachihoko.png"]
        elif img_filename.startswith("Badge_"): 
            return [f"https://leanny.github.io/splat3/images/badge/{img_filename}"]
        elif img_filename.startswith("Wsp_") or img_filename.startswith("Wsb_"): 
            return [f"https://leanny.github.io/splat3/images/subspe/{img_filename}"]
        elif img_filename.startswith("Path_"): 
            return [f"https://leanny.github.io/splat3/images/weapon_flat/{img_filename}"]
        else:
            return [
                f"https://leanny.github.io/splat3/images/weapon_flat/Path_{img_filename}",
                f"https://leanny.github.io/splat3/images/weapon/{img_filename}",
                f"https://leanny.github.io/splat3/images/weapon_flat/{img_filename}"
            ]

    def start_global_cache(self):
        log("[CACHE] Initializing cache verification...")
        
        self.finalize_rsdb_load()

        ordered_images = []
        seen = set()
        priority_seen = set()

        priority_imgs = []
        if getattr(self, 'is_easy_mode', False):
            if getattr(self, 'easy_mode_page', 0) == 0:
                curr_item = getattr(self, 'table_w', None) and self.table_w.currentItem()
                curr_idx = curr_item.data(Qt.ItemDataRole.UserRole) if curr_item else 0
                if isinstance(curr_idx, int) and self.weapon_main_file and self.weapon_main_file in self.rsdb_data:
                    if 0 <= curr_idx < len(self.rsdb_data[self.weapon_main_file]):
                        w_data = self.rsdb_data[self.weapon_main_file][curr_idx]
                        _, w_img, _, _ = self.data_manager.guess_image_and_name(w_data.get("__RowId", ""))
                        if w_img:
                            priority_imgs.append(w_img)
                        sub_p = w_data.get("SubWeapon", "")
                        for p, _, im, _ in getattr(self, 'sub_options', []):
                            if p == sub_p and im:
                                priority_imgs.append(im)
                                break
                        sp_p = w_data.get("SpecialWeapon", "")
                        for p, _, im, _ in getattr(self, 'special_options', []):
                            if p == sp_p and im:
                                priority_imgs.append(im)
                                break

                if getattr(self, '_current_weapon_img', None):
                    priority_imgs.append(self._current_weapon_img)

                if hasattr(self, 'table_w'):
                    for r in range(min(self.table_w.rowCount(), 30)):
                        it = self.table_w.item(r, 0)
                        if it:
                            im = it.data(Qt.ItemDataRole.UserRole + 1)
                            if im:
                                priority_imgs.append(im)
            else:
                if hasattr(self, 'badge_list_w'):
                    for r in range(min(self.badge_list_w.count(), 50)):
                        b_it = self.badge_list_w.item(r)
                        if b_it:
                            im = b_it.data(Qt.ItemDataRole.UserRole + 1)
                            if im:
                                priority_imgs.append(im)

        for img in priority_imgs:
            if img and img not in seen:
                seen.add(img)
                priority_seen.add(img)
                ordered_images.append(img)

        badge_imgs = []
        if self.badge_file and self.badge_file in self.rsdb_data:
            for b in self.rsdb_data[self.badge_file]:
                _, img = self.data_manager.guess_badge_info(b)
                badge_imgs.append(img)

        weapon_imgs = []
        if self.weapon_main_file and self.weapon_main_file in self.rsdb_data:
            for w in self.rsdb_data[self.weapon_main_file]:
                _, img, _, _ = self.data_manager.guess_image_and_name(w.get("__RowId", ""))
                weapon_imgs.append(img)

        first_group = badge_imgs if getattr(self, 'easy_mode_page', 0) == 1 else weapon_imgs
        second_group = weapon_imgs if getattr(self, 'easy_mode_page', 0) == 1 else badge_imgs

        for img in first_group + second_group:
            if img and img not in seen:
                seen.add(img)
                ordered_images.append(img)

        if self.weapon_sub_file and self.weapon_sub_file in self.rsdb_data:
            for w in self.rsdb_data[self.weapon_sub_file]:
                _, img, _, _ = self.data_manager.guess_image_and_name(w.get("__RowId", ""))
                if img and img not in seen:
                    seen.add(img)
                    ordered_images.append(img)

        if self.weapon_special_file and self.weapon_special_file in self.rsdb_data:
            for w in self.rsdb_data[self.weapon_special_file]:
                _, img, _, _ = self.data_manager.guess_image_and_name(w.get("__RowId", ""))
                if img and img not in seen:
                    seen.add(img)
                    ordered_images.append(img)

        missing_images = []
        priority_count = 0
        for img in ordered_images:
            path = os.path.join(CACHE_DIR, img)
            if not os.path.exists(path) or os.path.getsize(path) == 0:
                missing_images.append(img)
                if img in priority_seen:
                    priority_count += 1

        if missing_images:
            if hasattr(self, 'cache_worker') and self.cache_worker and self.cache_worker.isRunning():
                self.cache_worker.cancel()
                self.cache_worker.wait()

            self.cache_worker = ProgressiveCacheWorker(missing_images, self.get_image_urls, priority_count=priority_count)
            self.cache_worker.progress.connect(self.update_cache_progress)
            self.cache_worker.image_loaded.connect(self.on_single_image_cached)
            self.cache_worker.finished.connect(self.on_cache_finished)
            self.cache_worker.start()
        else:
            log("[CACHE] All images are valid and present.")

    def show_we_notice(self):
        self.btn_we.setEnabled(False)
        self.btn_we.setText(t("we_checking"))
        self.we_check_worker = WECheckWorker()
        self.we_check_worker.finished.connect(self.on_we_checked)
        self.we_check_worker.start()

    def on_we_checked(self, exists, local_ver, remote_ver, download_url, we_path):
        self.btn_we.setEnabled(True)
        self.btn_we.setText(t("btn_we"))
        self.we_download_url = download_url
        self.we_path = we_path
        
        if not exists:
            if self.ask_yes_no(t("btn_we"), t("we_not_installed")): self.start_we_download()
        else:
            update_available = (remote_ver != "0.0.0" and local_ver != remote_ver)
            if update_available:
                box = QMessageBox(self)
                box.setWindowTitle(t("we_update_title"))
                box.setText(t("we_update_avail", remote_ver, local_ver))
                btn_launch = box.addButton(t("btn_launch"), QMessageBox.ButtonRole.AcceptRole)
                btn_update = box.addButton(t("btn_update_now"), QMessageBox.ButtonRole.ActionRole)
                box.addButton(t("btn_cancel"), QMessageBox.ButtonRole.RejectRole)
                box.exec()
                if box.clickedButton() == btn_launch: self.launch_we()
                elif box.clickedButton() == btn_update: self.start_we_download()
            else:
                if self.ask_yes_no(t("btn_we"), t("we_launch_prompt")): self.launch_we()

    def start_we_download(self):
        if not getattr(self, 'we_download_url', None):
            QMessageBox.critical(self, t("err_title"), t("we_err_url"))
            return
        self.btn_we.setEnabled(False)
        self.btn_we.setText(t("we_downloading"))
        self.we_dl_worker = WEDownloadWorker(self.we_download_url)
        self.we_dl_worker.progress.connect(lambda msg: self.btn_we.setText(msg))
        self.we_dl_worker.finished.connect(self.on_we_downloaded)
        self.we_dl_worker.start()

    def on_we_downloaded(self, success, error_msg, we_path):
        self.btn_we.setEnabled(True)
        self.btn_we.setText(t("btn_we"))
        if success:
            self.we_path = we_path
            if self.ask_yes_no(t("we_install_done"), t("we_install_success")): self.launch_we()
        else:
            QMessageBox.critical(self, t("err_title"), t("we_err_install", error_msg))

    def launch_we(self):
        if hasattr(self, 'we_path') and os.path.exists(self.we_path):
            we_dir = os.path.dirname(self.we_path)
            
            possible_roots = [
                os.path.abspath(os.path.join(we_dir, "..")),
                we_dir
            ]
            
            bat_found = False
            for root in possible_roots:
                for bat_name in ["start.bat", "Start.bat"]:
                    bat_path = os.path.join(root, bat_name)
                    if os.path.exists(bat_path):
                        kwargs = {'cwd': root}
                        if os.name == 'nt': kwargs['creationflags'] = 0x00000010
                        subprocess.Popen([bat_path], **kwargs)
                        bat_found = True
                        break
                if bat_found:
                    break
                    
            if not bat_found:
                subprocess.Popen([sys.executable, self.we_path], cwd=we_dir)
        else:
            QMessageBox.critical(self, t("err_title"), t("we_err_main"))