import os
import sys
import subprocess
import re
import copy
from collections import Counter

import zstandard as zstd
import byml

from PyQt6.QtWidgets import QFileDialog, QMessageBox
from PyQt6.QtCore import Qt

from translations import t
from components import WECheckWorker, WEDownloadWorker, CacheBuilderWorker
from ui_layout import CacheDialog
from utils import (log, get_last_rsdb_dir, set_last_rsdb_dir, get_last_save_dir, 
                   set_last_save_dir, CACHE_DIR)
from tree_handler import TreeHandler

class EditorBackendMixin:
    def open_rsdb_folder(self):
        last_dir = get_last_rsdb_dir()
        folder_path = QFileDialog.getExistingDirectory(self, t("btn_open"), last_dir)
        if not folder_path: return
            
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
            QMessageBox.information(self, t("success_title"), "Aucun fichier n'a été modifié, aucune sauvegarde nécessaire.")
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
                QMessageBox.critical(self, t("err_title"), f"Erreur de sauvegarde {file_name} : {e}")
                return
                
        if saved_count > 0:
            self.modified_files.clear()
            QMessageBox.information(self, t("success_title"), f"{t('msg_save_success')} ({saved_count} fichier(s) modifié(s))")
        else:
            QMessageBox.information(self, t("success_title"), "Aucun fichier n'a été modifié, aucune sauvegarde nécessaire.")

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
        expected_images = {"Dummy.png"}
        
        if self.weapon_main_file and self.weapon_main_file in self.rsdb_data:
            for w in self.rsdb_data[self.weapon_main_file]:
                _, img, _, _ = self.data_manager.guess_image_and_name(w.get("__RowId", ""))
                expected_images.add(img)
                
        if self.weapon_sub_file and self.weapon_sub_file in self.rsdb_data:
            for w in self.rsdb_data[self.weapon_sub_file]:
                _, img, _, _ = self.data_manager.guess_image_and_name(w.get("__RowId", ""))
                expected_images.add(img)

        if self.weapon_special_file and self.weapon_special_file in self.rsdb_data:
            for w in self.rsdb_data[self.weapon_special_file]:
                _, img, _, _ = self.data_manager.guess_image_and_name(w.get("__RowId", ""))
                expected_images.add(img)

        missing_images = set()
        for img in expected_images:
            path = os.path.join(CACHE_DIR, img)
            if not os.path.exists(path) or os.path.getsize(path) == 0:
                missing_images.add(img)
                
        if missing_images:
            has_existing_cache = os.path.exists(CACHE_DIR) and len(os.listdir(CACHE_DIR)) > 5
            
            self.cache_worker = CacheBuilderWorker(missing_images, self.get_image_urls)
            self._pending_missing_images = missing_images
            
            if has_existing_cache:
                log("[CACHE] Local cache detected. Checking for new images in background...")
                self.cache_worker.finished.connect(self.on_background_cache_finished)
                self.cache_worker.start()
                self.finalize_rsdb_load()
            else:
                log("[CACHE] Cache missing or incomplete. Displaying download window...")
                self.cache_worker.progress.connect(self.update_cache_progress)
                self.cache_worker.finished.connect(self.on_cache_finished)
                
                self.cache_dialog = CacheDialog(self)
                self.cache_dialog.progress.setMaximum(len(missing_images))
                self.cache_dialog.show()
                self.cache_worker.start()
        else:
            log("[CACHE] All images are valid and present.")
            self.finalize_rsdb_load()

    def update_cache_progress(self, current, total):
        if hasattr(self, 'cache_dialog') and self.cache_dialog.isVisible():
            self.cache_dialog.progress.setValue(current)

    def on_cache_finished(self):
        if hasattr(self, 'cache_dialog') and self.cache_dialog.isVisible():
            self.cache_dialog.setWindowFlags(Qt.WindowType.Dialog)
            self.cache_dialog.accept()
        self.finalize_rsdb_load()
        
    def on_background_cache_finished(self):
        really_missing = []
        for img in getattr(self, '_pending_missing_images', []):
            path = os.path.join(CACHE_DIR, img)
            if not os.path.exists(path) or os.path.getsize(path) == 0:
                really_missing.append(img)
                
        if really_missing:
            log(f"[CACHE] Verification finished. {len(really_missing)} images not found (Normal 404 for placeholders): {', '.join(really_missing)}")
        else:
            log("[CACHE] Verification finished. All missing images processed successfully.")

        self.build_easy_mode_options()
        self.refresh_left_panel()
        self._restore_table_selection()
        if self.is_easy_mode and isinstance(self.current_table_name, int):
            self.load_easy_mode_weapon(self.current_table_name)

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