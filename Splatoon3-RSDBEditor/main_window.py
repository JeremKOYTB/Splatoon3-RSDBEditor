import os
import sys
import darkdetect
import byml
import subprocess

from PyQt6.QtWidgets import (QApplication, QMainWindow, QMessageBox, QTableWidgetItem, QMenu, QDialog, QTreeWidgetItem, QAbstractItemView)
from PyQt6.QtGui import QIcon, QPixmap, QImage, QPainter, QColor
from PyQt6.QtCore import Qt, QTimer, QEvent, QSize

from translations import t
from components import ImageDownloadWorker, ComboIconWorker, UpdateCheckWorker, UpdatePromptDialog
from ui_layout import UILayoutMixin, get_app_icon, get_stylesheet
from splatoon_data import SplatoonDataManager
from tree_handler import TreeHandler
from editor_backend import EditorBackendMixin

from utils import (get_editor_mode, save_editor_mode, get_saved_language, save_language, 
                   save_hide_filenames, save_hide_coop, save_hide_mission, save_hide_notfound, CACHE_DIR, log)

class SplatoonRSDBEditor(QMainWindow, UILayoutMixin, EditorBackendMixin):
    def __init__(self, app_version):
        super().__init__()
        self.APP_VERSION = app_version
        self.setWindowTitle(t("window_title"))
        self.resize(1250, 780)

        self.last_is_dark = darkdetect.isDark()
        self.setWindowIcon(get_app_icon())

        self.rsdb_data = {}            
        self.original_rsdb_data = {}  
        self.current_folder_path = None
        self.current_table_name = None
        self.modified_files = set() 
        self.tree_item_cache = {}
        self.cancel_operation = False
        
        self.languages = {
            "English (US)": "USen",
            "Français (EU)": "EUfr",
            "English (EU)": "EUen",
            "Español (EU)": "EUes",
            "Deutsch (EU)": "EUde",
            "Italiano (EU)": "EUit",
            "Nederlands (EU)": "EUnl",
            "日本語 (JA)": "JPja"
        }
        
        self.data_manager = SplatoonDataManager()
        
        self.is_easy_mode = get_editor_mode()
        self.weapon_main_file = None
        self.weapon_sub_file = None
        self.weapon_special_file = None
        
        self.sub_options = []
        self.special_options = []
        self.img_worker = None
        self.combo_workers = []
        
        self.setup_ui()
        self.tree_w.itemExpanded.connect(TreeHandler.on_item_expanded)
        self.setup_menus()
        self.ui_update_texts()
        
        saved_lang = get_saved_language()
        if saved_lang in self.languages:
            self.lang_combo.setCurrentText(saved_lang)
            self.on_language_changed(saved_lang)
        else:
            self.lang_combo.setCurrentText("English (US)")
            self.on_language_changed("English (US)")
        
        self.theme_timer = QTimer(self)
        self.theme_timer.timeout.connect(self.check_system_theme)
        self.theme_timer.start(2000)

        self.selection_timer = QTimer(self)
        self.selection_timer.setSingleShot(True)
        self.selection_timer.timeout.connect(self._process_delayed_selection)
        
        self._pending_current_data = None
        self._pending_previous_data = None
        self._is_loading_tree = False

        QTimer.singleShot(1000, self.check_for_updates)

    def closeEvent(self, event):
        if getattr(self, '_is_loading_tree', False):
            log("[INFO] Operation cancelled by user via Window Close.")
            self.cancel_operation = True
            event.ignore()
        else:
            event.accept()

    def preload_ram(self):
        if not self.rsdb_data: return
        
        if not self.ask_yes_no(t("warn_title"), t("msg_preload_warn"), default_no=True):
            return
        
        self.expert_progress_container.setVisible(True)
        self.btn_preload.setEnabled(False)
        self.expert_chk_container.setVisible(False)
        self.table_w.setEnabled(False) 
        self.btn_mode.setEnabled(False)
        self.btn_open.setEnabled(False)
        self.btn_save.setEnabled(False)
        
        self._is_loading_tree = True
        self.cancel_operation = False
        
        self._files_to_load = [f for f in self.rsdb_data.keys() if f not in self.tree_item_cache and f != self.current_table_name]
        self._total_preload_files = len(self._files_to_load)
        self._current_preload_idx = 0
        
        if self._total_preload_files > 0:
            self.expert_progress.setMaximum(self._total_preload_files)
            self.expert_progress.setValue(0)
            
            self.spinner_idx = getattr(self, 'spinner_idx', 0)
            self.spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
            
            QTimer.singleShot(0, self._process_next_preload)
        else:
            self.expert_progress_container.setVisible(False)
            self.btn_preload.setEnabled(True)
            self.table_w.setEnabled(True)
            self.btn_mode.setEnabled(True)
            self.btn_open.setEnabled(True)
            self.btn_save.setEnabled(True)
            if not self.is_easy_mode:
                self.expert_chk_container.setVisible(True)
            self._is_loading_tree = False
            QMessageBox.information(self, t("success_title"), t("msg_preload_done"))

    def _process_next_preload(self):
        if self.cancel_operation:
            self.expert_progress_container.setVisible(False)
            self.btn_preload.setEnabled(True)
            self.table_w.setEnabled(True)
            self.btn_mode.setEnabled(True)
            self.btn_open.setEnabled(True)
            self.btn_save.setEnabled(True)
            if not self.is_easy_mode:
                self.expert_chk_container.setVisible(True)
            self._is_loading_tree = False
            self.cancel_operation = False
            return
            
        if self._current_preload_idx >= self._total_preload_files:
            self.expert_progress.setValue(self._total_preload_files)
            self.expert_progress_container.setVisible(False)
            self.btn_preload.setEnabled(True)
            self.table_w.setEnabled(True)
            self.btn_mode.setEnabled(True)
            self.btn_open.setEnabled(True)
            self.btn_save.setEnabled(True)
            if not self.is_easy_mode:
                self.expert_chk_container.setVisible(True)
            self._is_loading_tree = False
            QMessageBox.information(self, t("success_title"), t("msg_preload_done"))
            return

        fname = self._files_to_load[self._current_preload_idx]
        self.expert_progress.setValue(self._current_preload_idx)
        self.spinner_idx = (self.spinner_idx + 1) % len(self.spinner_chars)
        self.expert_spinner.setText(self.spinner_chars[self.spinner_idx])

        data = self.rsdb_data[fname]
        
        items = []
        dummy_parent = QTreeWidgetItem()
        TreeHandler.add_items(dummy_parent, data, tree=True, is_cancelled_cb=lambda: self.cancel_operation, force_expand=True)
        
        if self.cancel_operation:
            self._process_next_preload()
            return
            
        while dummy_parent.childCount() > 0:
            items.append(dummy_parent.takeChild(0))
                
        self.tree_item_cache[fname] = items

        self._current_preload_idx += 1
        QTimer.singleShot(5, self._process_next_preload)

    def _attempt_expand(self, is_auto):
        if self.tree_w.topLevelItemCount() == 0:
            return

        is_massive = False
        for i in range(self.tree_w.topLevelItemCount()):
            if self.tree_w.topLevelItem(i).data(1, Qt.ItemDataRole.UserRole) == "chunk_folder":
                is_massive = True
                break
        if self.tree_w.topLevelItemCount() > 200:
            is_massive = True

        if is_massive:
            msg = t("msg_massive_auto_expand_warn") if is_auto else t("msg_massive_expand_warn")
            if not self.ask_yes_no(t("warn_title"), msg, default_no=True):
                if not is_auto:
                    self.chk_expand_all.blockSignals(True)
                    self.chk_expand_all.setChecked(False)
                    self.chk_expand_all.blockSignals(False)
                return

        self._is_loading_tree = True 
        self.cancel_operation = False
        self.table_w.setEnabled(False) 
        self.btn_mode.setEnabled(False)
        self.btn_open.setEnabled(False)
        self.btn_save.setEnabled(False)
        
        self.expert_chk_container.setVisible(False)
        self.expert_progress_container.setVisible(True)
        self.expert_progress.setMaximum(0)
        self.expert_spinner.setText("⠋")
        QApplication.processEvents()
        
        self.spinner_idx = getattr(self, 'spinner_idx', 0)
        self.spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        
        def prog_cb(c, t_val):
            self.spinner_idx = (self.spinner_idx + 1) % len(self.spinner_chars)
            self.expert_spinner.setText(self.spinner_chars[self.spinner_idx])
        
        TreeHandler.expand_all_safely(self.tree_w, lambda: self.cancel_operation, prog_cb)
        
        self.expert_progress_container.setVisible(False)
        self.expert_progress.setMaximum(100)
        if not self.is_easy_mode:
            self.expert_chk_container.setVisible(True)
        
        self.table_w.setEnabled(True) 
        self.btn_mode.setEnabled(True)
        self.btn_open.setEnabled(True)
        self.btn_save.setEnabled(True)
        self._is_loading_tree = False 
        self.cancel_operation = False

    def on_expand_all_toggled(self, state):
        if state:
            self.chk_collapse_all.blockSignals(True)
            self.chk_collapse_all.setChecked(False)
            self.chk_collapse_all.blockSignals(False)
            self._attempt_expand(is_auto=False)

    def on_collapse_all_toggled(self, state):
        if state:
            self.chk_expand_all.blockSignals(True)
            self.chk_expand_all.setChecked(False)
            self.chk_expand_all.blockSignals(False)
            if self.tree_w.topLevelItemCount() > 0:
                self._is_loading_tree = True 
                self.table_w.setEnabled(False)
                self.btn_mode.setEnabled(False)
                self.btn_open.setEnabled(False)
                self.btn_save.setEnabled(False)
                
                self.expert_chk_container.setVisible(False)
                self.expert_progress_container.setVisible(True)
                self.expert_progress.setMaximum(0)
                self.expert_spinner.setText("⠋")
                QApplication.processEvents()
                
                self.spinner_idx = getattr(self, 'spinner_idx', 0)
                self.spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
                
                def prog_cb(c, t_val):
                    self.spinner_idx = (self.spinner_idx + 1) % len(self.spinner_chars)
                    self.expert_spinner.setText(self.spinner_chars[self.spinner_idx])
                
                self.tree_w.setUpdatesEnabled(False)
                self.tree_w.collapseAll()
                self.tree_w.setUpdatesEnabled(True)
                
                self.expert_progress_container.setVisible(False)
                self.expert_progress.setMaximum(100)
                self.expert_chk_container.setVisible(True)
                
                self.table_w.setEnabled(True)
                self.btn_mode.setEnabled(True)
                self.btn_open.setEnabled(True)
                self.btn_save.setEnabled(True)
                self._is_loading_tree = False

    def update_action_buttons(self):
        if not self.is_easy_mode:
            self.btn_preload.setVisible(True)
            self.btn_zero_all.setVisible(False)
        else:
            self.btn_preload.setVisible(False)
            if self.right_stack.currentIndex() == 1:
                self.btn_zero_all.setVisible(True)
            else:
                self.btn_zero_all.setVisible(False)

    def eventFilter(self, obj, event):
        if hasattr(self, 'btn_update') and obj == self.btn_update and event.type() == QEvent.Type.Resize:
            y = (self.btn_update.height() - 24) // 2
            self.update_icon_overlay.move(12, y)
            return False
            
        if event.type() == QEvent.Type.Wheel:
            if hasattr(self, 'spin_special_points') and obj == self.spin_special_points:
                delta = event.angleDelta().y()
                step = 10 if delta > 0 else -10
                try:
                    current_val = int(self.spin_special_points.text() or "0")
                    new_val = max(0, min(999999999999, current_val + step))
                    self.spin_special_points.setText(str(new_val))
                except ValueError:
                    pass
                return True
            elif hasattr(self, 'combo_sub') and obj in (self.combo_sub, self.combo_special):
                delta = event.angleDelta().y()
                step = -1 if delta > 0 else 1
                new_idx = obj.currentIndex() + step
                while 0 <= new_idx < obj.count():
                    size_hint = obj.itemData(new_idx, Qt.ItemDataRole.SizeHintRole)
                    if size_hint != QSize(0, 0):
                        obj.setCurrentIndex(new_idx)
                        break
                    new_idx += step
                return True

        return super().eventFilter(obj, event)

    def get_text_icon(self, text):
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        if text:
            painter = QPainter(pixmap)
            font = self.btn_update.font()
            painter.setFont(font)
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)
            painter.end()
        return pixmap

    def clear_update_icon(self):
        self.update_icon_overlay.clear()

    def check_for_updates(self):
        self.update_spinner_idx = 0
        self.update_spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.update_spinner_timer = QTimer(self)
        self.update_spinner_timer.timeout.connect(self.tick_update_spinner)
        self.update_spinner_timer.start(100)
        
        self.update_worker = UpdateCheckWorker(self.APP_VERSION)
        self.update_worker.finished.connect(self.on_update_checked)
        self.update_worker.start()

    def tick_update_spinner(self):
        char = self.update_spinner_chars[self.update_spinner_idx]
        self.update_icon_overlay.setPixmap(self.get_text_icon(char))
        self.update_spinner_idx = (self.update_spinner_idx + 1) % len(self.update_spinner_chars)

    def on_update_checked(self, status, new_version, data_str):
        if hasattr(self, 'update_spinner_timer'):
            self.update_spinner_timer.stop()

        if status == 1:
            self.start_blinking_warning("‼️")
            
            dialog = UpdatePromptDialog(self.APP_VERSION, new_version, data_str, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.launch_updater()
                
        elif status == 0:
            self.update_icon_overlay.setPixmap(self.get_text_icon("✅"))
            QTimer.singleShot(5000, self.clear_update_icon)
            
        elif status == -1:
            self.update_icon_overlay.setPixmap(self.get_text_icon("❌"))
            QTimer.singleShot(5000, self.clear_update_icon)
            box = QMessageBox(self)
            box.setWindowIcon(get_app_icon())
            box.setWindowTitle(t("err_title"))
            box.setIcon(QMessageBox.Icon.Warning)
            box.setText(t("update_err_msg", data_str, self.APP_VERSION))
            box.exec()
            
        elif status == 2:
            self.start_blinking_warning("⚠️")
            
            if self.ask_yes_no(t("dev_warn_title"), t("dev_warn_msg", self.APP_VERSION, new_version), default_no=True):
                self.launch_updater()

    def start_blinking_warning(self, symbol):
        self.blink_symbol = symbol
        self.blink_state = False
        
        if hasattr(self, 'blink_timer') and self.blink_timer.isActive():
            self.blink_timer.stop()
            
        self.blink_timer = QTimer(self)
        self.blink_timer.timeout.connect(self.tick_blink)
        self.blink_timer.start(800)

    def tick_blink(self):
        if self.blink_state:
            self.update_icon_overlay.setPixmap(self.get_text_icon(self.blink_symbol))
        else:
            self.update_icon_overlay.clear()
        self.blink_state = not self.blink_state

    def launch_updater(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        updater_path = os.path.abspath(os.path.join(current_dir, "..", "updater.py"))
        
        if not os.path.exists(updater_path):
            QMessageBox.critical(self, t("err_title"), "updater.py missing.")
            return
            
        subprocess.Popen([sys.executable, updater_path, "--install-dir", os.path.abspath(os.path.join(current_dir, ".."))])
        sys.exit(0)

    def _restore_table_selection(self, preferred_data=None):
        if self.table_w.rowCount() == 0: 
            return
        
        target_item = None
        search_data = preferred_data if preferred_data is not None else self.current_table_name
        
        if not self.is_easy_mode and isinstance(search_data, int):
            search_data = self.weapon_main_file
        elif self.is_easy_mode and isinstance(search_data, str):
            search_data = 0
            
        if search_data is not None:
            for row in range(self.table_w.rowCount()):
                item = self.table_w.item(row, 0)
                if item and item.data(Qt.ItemDataRole.UserRole) == search_data:
                    target_item = item
                    break
                    
        if target_item is None:
            for row in range(self.table_w.rowCount()):
                if not self.table_w.isRowHidden(row):
                    target_item = self.table_w.item(row, 0)
                    break
                    
        if target_item is None:
            target_item = self.table_w.item(0, 0)
            
        if target_item:
            self.table_w.setCurrentItem(target_item)
            self.table_w.scrollToItem(target_item, QAbstractItemView.ScrollHint.PositionAtCenter)

    def on_language_changed(self, lang_name):
        import translations
        if "Français" in lang_name:
            translations.CURRENT_LANG = "fr"
        else:
            translations.CURRENT_LANG = "en"
            
        lang_code = self.languages.get(lang_name, "USen")
        save_language(lang_name)
        self.data_manager.fetch_leanny_localization(lang_code)
        
        self.ui_update_texts()
        
        if self.rsdb_data:
            self.build_easy_mode_options()
            self.refresh_left_panel()
            self._restore_table_selection()

    def on_filter_toggled(self, state):
        if not self.is_easy_mode:
            return
            
        save_hide_filenames(self.chk_hide_filenames.isChecked())
        save_hide_coop(self.chk_hide_coop.isChecked())
        save_hide_mission(self.chk_hide_mission.isChecked())
        save_hide_notfound(self.chk_hide_notfound.isChecked())
        
        current_item = self.table_w.currentItem()
        saved_user_data = current_item.data(Qt.ItemDataRole.UserRole) if current_item else None

        self.refresh_left_panel()
        self.build_easy_mode_options()
        self._restore_table_selection(preferred_data=saved_user_data)

    def toggle_mode(self):
        if not self.is_easy_mode and self.current_table_name and isinstance(self.current_table_name, str) and self.current_table_name in self.rsdb_data:
            try:
                self.rsdb_data[self.current_table_name] = TreeHandler.build_dict(self.tree_w.invisibleRootItem())
                self.modified_files.add(self.current_table_name)
            except: pass
            
        self.is_easy_mode = not self.is_easy_mode
        save_editor_mode(self.is_easy_mode)
        
        self.apply_mode()

    def get_weapon_display_name(self, row_id):
        translated, is_hardcoded = self.data_manager.get_exact_translation(row_id, row_id, return_is_hardcoded=True)
        
        if not self.chk_hide_filenames.isChecked():
            if is_hardcoded:
                return translated
                
            if translated.startswith(row_id) and not is_hardcoded:
                return translated
                
            clean_translated = translated
            if clean_translated.endswith(")") and " (" in clean_translated:
                parts = clean_translated.rsplit(" (", 1)
                clean_translated = f"{parts[0]} - {parts[1][:-1]}"
                
            return f"{row_id} ({clean_translated})"
        return translated

    def _is_row_filtered(self, row_id, img_name):
        if self.chk_hide_coop.isChecked() and "Coop" in row_id: 
            return True
            
        if self.chk_hide_mission.isChecked():
            if any(m in row_id for m in ["Mission", "Msn", "Hero", "Rival", "Sdodr", "SalmonBuddy"]): 
                return True
            if "SplkuraShoot" in row_id:
                return True
                
        if hasattr(self, 'chk_hide_notfound') and self.chk_hide_notfound.isChecked():
            translated = self.data_manager.get_exact_translation(row_id, row_id)
            icon_path = os.path.join(CACHE_DIR, img_name)
            
            is_dummy = (img_name == "Dummy.png")
            if not is_dummy:
                if not os.path.exists(icon_path) or os.path.getsize(icon_path) == 0:
                    is_dummy = True
                else:
                    img = QImage(icon_path)
                    if img.isNull():
                        is_dummy = True
            
            if "NotFound" in translated or is_dummy: 
                return True
            
        return False

    def on_table_context_menu(self, pos):
        item = self.table_w.itemAt(pos)
        if not item: return
        menu = QMenu(self)
        copy_action = menu.addAction(t("ctx_copy_name"))
        action = menu.exec(self.table_w.viewport().mapToGlobal(pos))
        if action == copy_action:
            QApplication.clipboard().setText(item.text())

    def on_tree_context_menu(self, pos):
        item = self.tree_w.itemAt(pos)
        if not item: return
        menu = QMenu(self)
        copy_prop = menu.addAction(t("ctx_copy_prop"))
        copy_val = menu.addAction(t("ctx_copy_val"))
        action = menu.exec(self.tree_w.viewport().mapToGlobal(pos))
        if action == copy_prop:
            QApplication.clipboard().setText(item.text(0))
        elif action == copy_val:
            QApplication.clipboard().setText(item.text(1))

    def on_title_context_menu(self, pos):
        if not self.lbl_weapon_title.text(): return
        menu = QMenu(self)
        copy_action = menu.addAction(t("ctx_copy_name"))
        action = menu.exec(self.lbl_weapon_title.mapToGlobal(pos))
        if action == copy_action:
            QApplication.clipboard().setText(self.lbl_weapon_title.text())

    def on_combo_sub_context_menu(self, pos):
        if self.combo_sub.count() == 0: return
        menu = QMenu(self)
        copy_action = menu.addAction(t("ctx_copy_name"))
        action = menu.exec(self.combo_sub.mapToGlobal(pos))
        if action == copy_action:
            QApplication.clipboard().setText(self.combo_sub.currentText())

    def on_combo_special_context_menu(self, pos):
        if self.combo_special.count() == 0: return
        menu = QMenu(self)
        copy_action = menu.addAction(t("ctx_copy_name"))
        action = menu.exec(self.combo_special.mapToGlobal(pos))
        if action == copy_action:
            QApplication.clipboard().setText(self.combo_special.currentText())

    def refresh_left_panel(self):
        self.table_w.blockSignals(True)
        self.table_w.setRowCount(0)
        
        if not self.rsdb_data:
            self._last_total = 0
            self._last_displayed = 0
            self.count_lbl.setText(t("count_info", 0, 0, 0, 0))
            self.table_w.blockSignals(False)
            return

        total_files = 0
        displayed_count = 0

        if self.is_easy_mode:
            if not self.weapon_main_file or self.weapon_main_file not in self.rsdb_data:
                self._last_total = 0
                self._last_displayed = 0
                self.count_lbl.setText(t("count_info", 0, 0, 0, 0))
                self.table_w.blockSignals(False)
                return
            
            total_files = len(self.rsdb_data[self.weapon_main_file])
            row = 0
            for i, weapon in enumerate(self.rsdb_data[self.weapon_main_file]):
                row_id = weapon.get("__RowId", f"Weapon_{i}")
                _, img_name, _, _ = self.data_manager.guess_image_and_name(row_id)
                
                if self._is_row_filtered(row_id, img_name): 
                    continue
                
                name = self.get_weapon_display_name(row_id)
                self.table_w.insertRow(row)
                item = QTableWidgetItem(name)
                item.setData(Qt.ItemDataRole.UserRole, i)
                
                icon_path = os.path.join(CACHE_DIR, img_name)
                img = QImage()
                if os.path.exists(icon_path):
                    img.load(icon_path)
                    
                if img.isNull():
                    dummy_path = os.path.join(CACHE_DIR, "Dummy.png")
                    if os.path.exists(dummy_path):
                        img.load(dummy_path)

                if not img.isNull():
                    scaled = img.scaled(28, 28, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    square = QImage(28, 28, QImage.Format.Format_ARGB32_Premultiplied)
                    square.fill(Qt.GlobalColor.transparent)
                    painter = QPainter(square)
                    painter.drawImage((28 - scaled.width()) // 2, (28 - scaled.height()) // 2, scaled)
                    painter.end()
                    item.setIcon(QIcon(QPixmap.fromImage(square)))
                    
                self.table_w.setItem(row, 0, item)
                row += 1
            displayed_count = row
        else:
            total_files = len(self.rsdb_data.keys())
            row = 0
            for file in self.rsdb_data.keys():
                self.table_w.insertRow(row)
                item = QTableWidgetItem(file)
                item.setData(Qt.ItemDataRole.UserRole, file)
                self.table_w.setItem(row, 0, item)
                row += 1
            self.table_w.sortItems(0, Qt.SortOrder.AscendingOrder)
            displayed_count = row
            
        self._last_total = total_files
        self._last_displayed = displayed_count
        current_row = self.get_current_visible_row_number()
        self.count_lbl.setText(t("count_info", total_files, displayed_count, current_row, displayed_count))
        self.table_w.blockSignals(False)

    def finalize_rsdb_load(self):
        self.build_easy_mode_options()
        self.refresh_left_panel()
        if hasattr(self, '_saved_splitter_sizes') and sum(self._saved_splitter_sizes) > 0:
            self.splitter.setSizes(self._saved_splitter_sizes)
            
        self._restore_table_selection()

    def get_cached_icon(self, img_name):
        icon_path = os.path.join(CACHE_DIR, img_name)
        img = QImage()
        if os.path.exists(icon_path):
            img.load(icon_path)
            
        if img.isNull():
            dummy_path = os.path.join(CACHE_DIR, "Dummy.png")
            if os.path.exists(dummy_path):
                img.load(dummy_path)
                
        if not img.isNull():
            scaled = img.scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            square = QImage(24, 24, QImage.Format.Format_ARGB32_Premultiplied)
            square.fill(Qt.GlobalColor.transparent)
            painter = QPainter(square)
            painter.drawImage((24 - scaled.width()) // 2, (24 - scaled.height()) // 2, scaled)
            painter.end()
            return QIcon(QPixmap.fromImage(square))
        return QIcon()

    def update_combo_icon(self, index, icon, is_sub=True):
        if is_sub:
            self.combo_sub.setItemIcon(index, icon)
        else:
            self.combo_special.setItemIcon(index, icon)

    def build_easy_mode_options(self):
        self.sub_options = [
            ("", t("opt_default"), "", False)
        ]
        self.special_options = [
            ("", t("opt_default"), "", False)
        ]
        self.combo_workers = []
        
        if self.weapon_sub_file and self.weapon_sub_file in self.rsdb_data:
            for row in self.rsdb_data[self.weapon_sub_file]:
                row_id = row.get('__RowId', '')
                _, img_name, _, _ = self.data_manager.guess_image_and_name(row_id)
                
                is_filtered = self._is_row_filtered(row_id, img_name)
                label = self.get_weapon_display_name(row_id)
                path = f"Work/Gyml/{row_id}.spl__WeaponInfoSub.gyml"
                self.sub_options.append((path, label, img_name, is_filtered))
                
        if self.weapon_special_file and self.weapon_special_file in self.rsdb_data:
            for row in self.rsdb_data[self.weapon_special_file]:
                row_id = row.get('__RowId', '')
                _, img_name, _, _ = self.data_manager.guess_image_and_name(row_id)
                
                is_filtered = self._is_row_filtered(row_id, img_name)
                label = self.get_weapon_display_name(row_id)
                path = f"Work/Gyml/{row_id}.spl__WeaponInfoSpecial.gyml"
                self.special_options.append((path, label, img_name, is_filtered))
                
        self.combo_sub.blockSignals(True)
        self.combo_special.blockSignals(True)
        
        self.combo_sub.clear()
        for idx, (path, label, img_name, is_filtered) in enumerate(self.sub_options):
            icon = self.get_cached_icon(img_name) if img_name else QIcon()
            self.combo_sub.addItem(icon, label, path)
            if is_filtered:
                self.combo_sub.setItemData(idx, QSize(0, 0), Qt.ItemDataRole.SizeHintRole)
            if img_name and icon.isNull():
                local_p = os.path.join(CACHE_DIR, img_name)
                urls = self.get_image_urls(img_name)
                worker = ComboIconWorker(idx, urls, local_p)
                worker.finished.connect(lambda i, ic: self.update_combo_icon(i, ic, is_sub=True))
                self.combo_workers.append(worker)
                worker.start()
            
        self.combo_special.clear()
        for idx, (path, label, img_name, is_filtered) in enumerate(self.special_options):
            icon = self.get_cached_icon(img_name) if img_name else QIcon()
            self.combo_special.addItem(icon, label, path)
            if is_filtered:
                self.combo_special.setItemData(idx, QSize(0, 0), Qt.ItemDataRole.SizeHintRole)
            if img_name and icon.isNull():
                local_p = os.path.join(CACHE_DIR, img_name)
                urls = self.get_image_urls(img_name)
                worker = ComboIconWorker(idx, urls, local_p)
                worker.finished.connect(lambda i, ic: self.update_combo_icon(i, ic, is_sub=False))
                self.combo_workers.append(worker)
                worker.start()
            
        self.combo_sub.blockSignals(False)
        self.combo_special.blockSignals(False)

    def get_current_visible_row_number(self):
        item = self.table_w.currentItem()
        if not item or self.table_w.isRowHidden(item.row()):
            return 0
        visible_count = 0
        for r in range(item.row() + 1):
            if not self.table_w.isRowHidden(r):
                visible_count += 1
        return visible_count

    def filter_tables(self, text):
        displayed_count = 0
        for row in range(self.table_w.rowCount()):
            item = self.table_w.item(row, 0)
            if item:
                is_hidden = text.lower() not in item.text().lower()
                self.table_w.setRowHidden(row, is_hidden)
                if not is_hidden:
                    displayed_count += 1
                    
        self._last_displayed = displayed_count
        current_row = self.get_current_visible_row_number()
        self.count_lbl.setText(t("count_info", getattr(self, '_last_total', 0), self._last_displayed, current_row, self._last_displayed))

    def on_table_current_changed(self, current, previous):
        if current:
            current_row = self.get_current_visible_row_number()
            self.count_lbl.setText(t("count_info", getattr(self, '_last_total', 0), getattr(self, '_last_displayed', 0), current_row, getattr(self, '_last_displayed', 0)))

        if not current: return
        
        self._pending_current_data = current.data(Qt.ItemDataRole.UserRole)
        self._pending_previous_data = previous.data(Qt.ItemDataRole.UserRole) if previous else None
        
        self.selection_timer.start(150) 

    def _process_delayed_selection(self):
        if getattr(self, '_is_loading_tree', False):
            self.selection_timer.start(150)
            return

        current_data = getattr(self, '_pending_current_data', None)
        previous_data = getattr(self, '_pending_previous_data', None)
        
        if current_data is None: return
        
        if self.is_easy_mode:
            if not isinstance(current_data, int): return
            self.load_easy_mode_weapon(current_data)
        else:
            self._is_loading_tree = True
            self.table_w.setEnabled(False) 
            self.btn_mode.setEnabled(False)
            self.btn_open.setEnabled(False)
            self.btn_save.setEnabled(False)
            self.cancel_operation = False
            try:
                file_name = current_data

                if previous_data is not None and self.current_table_name and isinstance(self.current_table_name, str) and self.current_table_name in self.rsdb_data:
                    try: 
                        self.rsdb_data[self.current_table_name] = TreeHandler.build_dict(self.tree_w.invisibleRootItem())
                        self.modified_files.add(self.current_table_name)
                        
                        items = []
                        while self.tree_w.topLevelItemCount() > 0:
                            items.append(self.tree_w.takeTopLevelItem(0))
                        self.tree_item_cache[self.current_table_name] = items
                    except: pass
                
                self.load_expert_mode_file(file_name)
            finally:
                self.table_w.setEnabled(True) 
                self.btn_mode.setEnabled(True)
                self.btn_open.setEnabled(True)
                self.btn_save.setEnabled(True)
                self._is_loading_tree = False
                self.cancel_operation = False

    def load_expert_mode_file(self, file_name):
        if self.current_table_name == file_name: return
        
        data = self.rsdb_data.get(file_name)
        if data is None: return
        
        self.current_table_name = file_name
        self.tree_w.clear()
        
        if file_name in self.tree_item_cache:
            self.tree_w.addTopLevelItems(self.tree_item_cache[file_name])
            if self.chk_expand_all.isChecked():
                self._attempt_expand(is_auto=True)
            elif self.chk_collapse_all.isChecked():
                self.tree_w.collapseAll()
        else:
            self.expert_chk_container.setVisible(False)
            self.expert_progress_container.setVisible(True)
            self.btn_preload.setEnabled(False)
            
            self.spinner_idx = 0
            self.spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
            
            def prog_cb(c, t_val):
                self.expert_progress.setMaximum(t_val)
                self.expert_progress.setValue(c)
                if c % 50 == 0:
                    self.spinner_idx = (self.spinner_idx + 1) % len(self.spinner_chars)
                    self.expert_spinner.setText(self.spinner_chars[self.spinner_idx])
            
            TreeHandler.populate_tree(self.tree_w, data, auto_expand=False, progress_cb=prog_cb, is_cancelled_cb=lambda: self.cancel_operation)
            
            self.expert_progress_container.setVisible(False)
            self.btn_preload.setEnabled(True)
            if not self.is_easy_mode:
                self.expert_chk_container.setVisible(True)

            if self.cancel_operation:
                return

            if self.chk_expand_all.isChecked():
                self._attempt_expand(is_auto=True)
            elif self.chk_collapse_all.isChecked():
                self.tree_w.collapseAll()

    def load_easy_mode_weapon(self, index):
        if not isinstance(index, int):
            return
            
        self.current_table_name = index
        weapon = self.rsdb_data[self.weapon_main_file][index]
        
        row_id = weapon.get("__RowId", "Unknown")
        display_title = self.get_weapon_display_name(row_id)
        self.lbl_weapon_title.setText(display_title)
        
        _, img_name, _, _ = self.data_manager.guess_image_and_name(row_id)
        icon_path = os.path.join(CACHE_DIR, img_name)
        img = QImage()
        if os.path.exists(icon_path):
            img.load(icon_path)
            
        if img.isNull():
            dummy_path = os.path.join(CACHE_DIR, "Dummy.png")
            if os.path.exists(dummy_path):
                img.load(dummy_path)

        if not img.isNull():
            scaled = img.scaled(128, 128, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            square = QImage(128, 128, QImage.Format.Format_ARGB32_Premultiplied)
            square.fill(Qt.GlobalColor.transparent)
            painter = QPainter(square)
            painter.drawImage((128 - scaled.width()) // 2, (128 - scaled.height()) // 2, scaled)
            painter.end()
            self.img_lbl.setPixmap(QPixmap.fromImage(square))
        else:
            self.img_lbl.clear()
            self.img_lbl.setText(t("img_unavail"))
            urls = self.get_image_urls(img_name)
            self.img_worker = ImageDownloadWorker(urls)
            self.img_worker.finished.connect(lambda img: self.cache_and_show_image(img, icon_path))
            self.img_worker.start()
        
        self.combo_sub.blockSignals(True)
        self.combo_special.blockSignals(True)
        self.spin_special_points.blockSignals(True)
        
        sub_path = weapon.get("SubWeapon") or ""
        sub_idx = self.combo_sub.findData(sub_path)
        self.combo_sub.setCurrentIndex(sub_idx if sub_idx >= 0 else 0)
            
        sp_path = weapon.get("SpecialWeapon") or ""
        sp_idx = self.combo_special.findData(sp_path)
        self.combo_special.setCurrentIndex(sp_idx if sp_idx >= 0 else 0)
            
        sp_points = weapon.get("SpecialPoint", 0)
        try: self.spin_special_points.setText(str(int(sp_points)))
        except: self.spin_special_points.setText("0")
        
        self.combo_sub.blockSignals(False)
        self.combo_special.blockSignals(False)
        self.spin_special_points.blockSignals(False)

    def cache_and_show_image(self, image, local_path):
        is_dummy_fallback = False
        if image.isNull():
            dummy_path = os.path.join(CACHE_DIR, "Dummy.png")
            if os.path.exists(dummy_path):
                image = QImage(dummy_path)
                is_dummy_fallback = True

        if not image.isNull():
            if not is_dummy_fallback and local_path:
                image.save(local_path)
            
            scaled = image.scaled(128, 128, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            square = QImage(128, 128, QImage.Format.Format_ARGB32_Premultiplied)
            square.fill(Qt.GlobalColor.transparent)
            painter = QPainter(square)
            painter.drawImage((128 - scaled.width()) // 2, (128 - scaled.height()) // 2, scaled)
            painter.end()
            self.img_lbl.setPixmap(QPixmap.fromImage(square))
        else:
            self.img_lbl.clear()
            self.img_lbl.setText(t("img_unavail"))

    def on_easy_form_changed(self):
        if not self.is_easy_mode or self.current_table_name is None: return
        weapon = self.rsdb_data[self.weapon_main_file][self.current_table_name]
        
        sub_val = self.combo_sub.currentData()
        weapon["SubWeapon"] = sub_val if sub_val else None
            
        sp_val = self.combo_special.currentData()
        weapon["SpecialWeapon"] = sp_val if sp_val else None
            
        try: new_sp_point = int(self.spin_special_points.text())
        except ValueError: new_sp_point = 0
        orig = weapon.get("SpecialPoint", 0)
        
        type_name = type(orig).__name__
        if type_name in ['UInt', 'Int', 'Int64', 'UInt64'] and hasattr(byml, type_name):
            weapon["SpecialPoint"] = getattr(byml, type_name)(new_sp_point)
        else:
            weapon["SpecialPoint"] = new_sp_point
            
        self.modified_files.add(self.weapon_main_file)

    def zero_all_special_points(self):
        if not self.weapon_main_file or self.weapon_main_file not in self.rsdb_data: return
        for weapon in self.rsdb_data[self.weapon_main_file]:
            if "SpecialPoint" in weapon:
                orig = weapon.get("SpecialPoint", 0)
                type_name = type(orig).__name__
                if type_name in ['UInt', 'Int', 'Int64', 'UInt64'] and hasattr(byml, type_name):
                    weapon["SpecialPoint"] = getattr(byml, type_name)(0)
                else:
                    weapon["SpecialPoint"] = 0
                    
        self.modified_files.add(self.weapon_main_file)
        
        QMessageBox.information(self, t("success_title"), t("msg_zero_special_done"))
        if self.current_table_name is not None and isinstance(self.current_table_name, int):
            self.load_easy_mode_weapon(self.current_table_name)

    def reset_config_and_restart(self):
        if self.ask_yes_no(t("menu_reset"), t("msg_reset_confirm"), default_no=True):
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(current_dir, "splatoon_RSDBeditor_config.json")
            if os.path.exists(config_path):
                try: os.remove(config_path)
                except Exception as e:
                    QMessageBox.critical(self, t("err_title"), f"{e}")
                    return
            subprocess.Popen([sys.executable] + sys.argv)
            sys.exit(0)

    def check_system_theme(self):
        current_dark = darkdetect.isDark()
        if current_dark != self.last_is_dark:
            self.last_is_dark = current_dark
            new_icon = get_app_icon()
            self.setWindowIcon(new_icon)
            QApplication.instance().setWindowIcon(new_icon)
            QApplication.instance().setStyleSheet(get_stylesheet(current_dark))
            pal = QApplication.instance().palette()
            pal.setColor(QApplication.instance().palette().ColorRole.Window, Qt.GlobalColor.darkGray if current_dark else QColor("#F0F0F5"))
            QApplication.instance().setPalette(pal)