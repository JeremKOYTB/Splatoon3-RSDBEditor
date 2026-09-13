import os
import sys
import copy
import math
import darkdetect
import byml
import subprocess

from PyQt6.QtWidgets import (QApplication, QMainWindow, QMessageBox, QTableWidgetItem, QMenu, QDialog, 
                             QTreeWidgetItem, QAbstractItemView, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QProgressBar, QScrollArea, QFrame, 
                             QGridLayout, QCheckBox, QListWidget, QListWidgetItem, QStyledItemDelegate, 
                             QStyleOptionButton, QStyleOptionViewItem, QStyle, QLineEdit, QSizePolicy, 
                             QGraphicsOpacityEffect)
from PyQt6.QtGui import QIcon, QPixmap, QImage, QPainter, QColor, QFont
from PyQt6.QtCore import Qt, QTimer, QEvent, QSize, QRect, QPropertyAnimation, QEasingCurve, QVariantAnimation

import translations
from translations import t
from components import ImageDownloadWorker, ComboIconWorker, UpdateCheckWorker, UpdatePromptDialog, BadgeNoticeDialog
from ui_layout import UILayoutMixin, get_app_icon, get_stylesheet
from splatoon_data import SplatoonDataManager
from tree_handler import TreeHandler
from editor_backend import EditorBackendMixin

from utils import (get_editor_mode, save_editor_mode, get_saved_language, save_language, 
                    save_hide_filenames, save_hide_coop, save_hide_mission, save_hide_notfound, 
                    CACHE_DIR, CONFIG_FILE, log, get_badge_notice_dismissed, save_badge_notice_dismissed)

from badge_handler import BadgeCardDelegate, BadgePageMixin


class AnimatedWeaponImage(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._pixmap = None
        self._scale = 1.0
        self._opacity = 1.0
        self._anim = None

    def setPixmap(self, pixmap, animate=True):
        self._pixmap = pixmap
        if pixmap and not pixmap.isNull():
            self.setText("")
        if self._anim and self._anim.state() == QVariantAnimation.State.Running:
            self._anim.stop()

        if not animate or pixmap is None or pixmap.isNull():
            self._scale = 1.0
            self._opacity = 1.0
            self.update()
            return

        self._scale = 0.65
        self._opacity = 0.0
        self.update()

        self._anim = QVariantAnimation(self)
        self._anim.setDuration(380)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutBack)

        def on_step(val):
            self._scale = 0.65 + 0.35 * val
            self._opacity = min(1.0, max(0.0, val * 1.6))
            self.update()

        def on_end():
            self._scale = 1.0
            self._opacity = 1.0
            self.update()

        self._anim.valueChanged.connect(on_step)
        self._anim.finished.connect(on_end)
        self._anim.start()

    def clear(self):
        self._pixmap = None
        if self._anim and self._anim.state() == QVariantAnimation.State.Running:
            self._anim.stop()
        self._scale = 1.0
        self._opacity = 1.0
        super().clear()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._pixmap and not self._pixmap.isNull():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            painter.setOpacity(self._opacity)

            cx = self.width() / 2.0
            cy = self.height() / 2.0
            painter.translate(cx, cy)
            painter.scale(self._scale, self._scale)

            pw = self._pixmap.width()
            ph = self._pixmap.height()
            painter.drawPixmap(int(-pw / 2.0), int(-ph / 2.0), self._pixmap)
            painter.end()


class AnimatedTitleLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._scale = 1.0
        self._opacity = 1.0
        self._anim = None

    def setText(self, text, animate=True):
        super().setText(text)
        if self._anim and self._anim.state() == QVariantAnimation.State.Running:
            self._anim.stop()

        if not animate or not text:
            self._scale = 1.0
            self._opacity = 1.0
            self.update()
            return

        self._scale = 0.85
        self._opacity = 0.0
        self.update()

        self._anim = QVariantAnimation(self)
        self._anim.setDuration(360)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutBack)

        def on_step(val):
            self._scale = 0.85 + 0.15 * val
            self._opacity = min(1.0, max(0.0, val * 1.5))
            self.update()

        def on_end():
            self._scale = 1.0
            self._opacity = 1.0
            self.update()

        self._anim.valueChanged.connect(on_step)
        self._anim.finished.connect(on_end)
        self._anim.start()

    def paintEvent(self, event):
        if not (self._anim and self._anim.state() == QVariantAnimation.State.Running):
            super().paintEvent(event)
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setOpacity(min(1.0, max(0.0, self._opacity)))

        cx = self.width() / 2.0
        cy = self.height() / 2.0
        painter.translate(cx, cy)
        painter.scale(self._scale, self._scale)
        painter.translate(-cx, -cy)

        painter.setFont(self.font())
        painter.setPen(QColor("#ffffff"))
        painter.drawText(self.rect(), self.alignment() | Qt.TextFlag.TextWordWrap, self.text())
        painter.end()


class WeaponTableDelegate(QStyledItemDelegate):
    def __init__(self, parent_table):
        super().__init__(parent_table)
        self.table = parent_table
        self._anim_rows = {}
        self._max_concurrent = 64

    def trigger_icon_animation(self, row):
        if not self.table or row < 0 or row >= self.table.rowCount():
            return

        item = self.table.item(row, 0)
        if not item:
            return

        rect = self.table.visualItemRect(item)
        viewport_rect = self.table.viewport().rect()
        if not viewport_rect.intersects(rect):
            return

        if len(self._anim_rows) >= self._max_concurrent:
            return

        if row in self._anim_rows:
            self._anim_rows[row][1].stop()

        anim = QVariantAnimation(self)
        anim.setDuration(380)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutBack)

        def on_step(val):
            self._anim_rows[row] = (val, anim)
            if self.table and self.table.viewport():
                self.table.viewport().update(self.table.visualItemRect(item))

        def on_end():
            self._anim_rows.pop(row, None)
            if self.table and self.table.viewport():
                self.table.viewport().update(self.table.visualItemRect(item))

        anim.valueChanged.connect(on_step)
        anim.finished.connect(on_end)
        self._anim_rows[row] = (0.0, anim)
        anim.start()
        if self.table and self.table.viewport():
            self.table.viewport().update(rect)

    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        row = index.row()
        rect = option.rect

        is_selected = bool(option.state & QStyle.StateFlag.State_Selected)
        is_hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)

        if is_selected:
            painter.fillRect(rect, QColor("#0078D7"))
        elif is_hovered:
            painter.fillRect(rect, QColor(255, 255, 255, 20))
        else:
            painter.fillRect(rect, Qt.GlobalColor.transparent)

        icon = index.data(Qt.ItemDataRole.DecorationRole)
        icon_size = 28
        icon_x = rect.left() + 8
        icon_y = rect.top() + (rect.height() - icon_size) // 2

        is_animating = row in self._anim_rows
        prog = self._anim_rows[row][0] if is_animating else 1.0

        if isinstance(icon, QIcon) and not icon.isNull():
            pix = icon.pixmap(QSize(icon_size, icon_size))
            if not pix.isNull():
                if is_animating:
                    painter.save()
                    painter.setOpacity(min(1.0, max(0.0, prog * 1.5)))
                    cx = icon_x + icon_size / 2.0
                    cy = icon_y + icon_size / 2.0
                    painter.translate(cx, cy)
                    scale = 0.60 + (0.40 * prog)
                    painter.scale(scale, scale)
                    painter.drawPixmap(int(-icon_size / 2.0), int(-icon_size / 2.0), pix)
                    painter.restore()
                else:
                    painter.drawPixmap(icon_x, icon_y, pix)
        else:
            placeholder_rect = QRect(icon_x + 2, icon_y + 2, icon_size - 4, icon_size - 4)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, 14))
            painter.drawRoundedRect(placeholder_rect, 4, 4)

        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        text_x = icon_x + icon_size + 10
        text_w = rect.width() - (text_x - rect.left()) - 8
        text_rect = QRect(text_x, rect.top(), max(0, text_w), rect.height())

        text_color = QColor("#FFFFFF") if is_selected else option.palette.text().color()
        painter.setPen(text_color)
        painter.setFont(option.font)

        elided = painter.fontMetrics().elidedText(text, Qt.TextElideMode.ElideRight, text_w)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided)

        painter.restore()


class SplatoonRSDBEditor(QMainWindow, UILayoutMixin, EditorBackendMixin, BadgePageMixin):
    def __init__(self, app_version):
        super().__init__()
        self.APP_VERSION = app_version
        self.detected_version = None
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
        self._unlock_in_cooldown = False
        self._all_unlocked_popup_shown = False

        self._last_weapon_sub = None
        self._last_weapon_sp = None
        self._last_weapon_pts = None

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
        self.easy_mode_page = 0
        self.weapon_main_file = None
        self.weapon_sub_file = None
        self.weapon_special_file = None
        self.badge_file = None

        self.sub_options = []
        self.special_options = []
        self.img_worker = None
        self.combo_workers = []
        self._populating_badges = False
        self._page_switch_busy = False

        self._weapon_icon_cache = {}
        self._combo_icon_cache = {}
        self._badge_pix_cache = {}
        self._badge_icon_cache = {}
        self._badge_items_by_image = {}

        self.setup_ui()
        self.weapon_delegate = WeaponTableDelegate(self.table_w)
        self.table_w.setItemDelegate(self.weapon_delegate)
        self.setup_badge_page_ui()
        self.setup_easy_weapon_page_ui()
        self.setup_status_progress()

        if hasattr(self, 'btn_unlock_shop'):
            try:
                self.btn_unlock_shop.clicked.disconnect()
            except Exception:
                pass
            self.btn_unlock_shop.clicked.connect(self.unlock_all_shop_weapons)

        self.table_w.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_w.customContextMenuRequested.connect(self.on_table_context_menu)
        self.table_w.currentItemChanged.connect(self.on_table_current_changed)

        self.tree_w.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_w.customContextMenuRequested.connect(self.on_tree_context_menu)
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

        self.update_loaded_state_ui()
        QTimer.singleShot(1000, self.check_for_updates)

    def get_placeholder_pixmap(self, width=32, height=32):
        if not hasattr(self, '_placeholder_pixmaps'):
            self._placeholder_pixmaps = {}
        key = (width, height)
        if key not in self._placeholder_pixmaps:
            pix = QPixmap(width, height)
            pix.fill(Qt.GlobalColor.transparent)
            self._placeholder_pixmaps[key] = pix
        return self._placeholder_pixmaps[key]

    def get_placeholder_icon(self, width=32, height=32):
        return QIcon(self.get_placeholder_pixmap(width, height))

    def is_data_loaded(self):
        return bool(self.rsdb_data)

    def update_loaded_state_ui(self):
        loaded = self.is_data_loaded()
        if hasattr(self, 'nav_container'):
            self.nav_container.setEnabled(loaded)
        if hasattr(self, 'btn_page_prev'):
            self.btn_page_prev.setEnabled(loaded and self.easy_mode_page > 0)
        if hasattr(self, 'btn_page_title'):
            self.btn_page_title.setEnabled(loaded)
        if hasattr(self, 'btn_page_next'):
            self.btn_page_next.setEnabled(loaded and self.easy_mode_page < 1)
        if hasattr(self, 'btn_mode'):
            self.btn_mode.setEnabled(loaded)
        if hasattr(self, 'btn_save'):
            self.btn_save.setEnabled(loaded)
        if hasattr(self, 'btn_zero_all'):
            has_data = loaded
            if self.is_easy_mode:
                if self.easy_mode_page == 0:
                    has_data = loaded and bool(self.weapon_main_file and self.weapon_main_file in self.rsdb_data)
                else:
                    has_data = loaded and bool(self.badge_file and self.badge_file in self.rsdb_data)
            self.btn_zero_all.setEnabled(has_data and not getattr(self, '_unlock_in_cooldown', False))
        if hasattr(self, 'btn_unlock_shop'):
            has_weapons = bool(self.weapon_main_file and self.weapon_main_file in self.rsdb_data)
            self.btn_unlock_shop.setEnabled(loaded and has_weapons)
        if hasattr(self, 'btn_preload'):
            self.btn_preload.setEnabled(loaded)
        for chk in [getattr(self, 'chk_hide_filenames', None), getattr(self, 'chk_hide_notfound', None), getattr(self, 'chk_hide_coop', None), getattr(self, 'chk_hide_mission', None), getattr(self, 'chk_expand_all', None), getattr(self, 'chk_collapse_all', None)]:
            if chk:
                chk.setEnabled(loaded)

    def setup_status_progress(self):
        self.cache_status_container = QWidget()
        cs_layout = QHBoxLayout(self.cache_status_container)
        cs_layout.setContentsMargins(15, 0, 15, 5)
        cs_layout.setSpacing(10)
        cs_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_cache_status = QLabel("")
        self.lbl_cache_status.setStyleSheet("font-size: 11px; font-weight: 500; color: #dcdde1; padding-bottom: 2px;")
        self.lbl_cache_status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.cache_progress_bar = QProgressBar()
        self.cache_progress_bar.setRange(0, 100)
        self.cache_progress_bar.setFixedWidth(170)
        self.cache_progress_bar.setFixedHeight(14)
        self.cache_progress_bar.setTextVisible(True)
        self.cache_progress_bar.setStyleSheet(
            "QProgressBar { border: 1px solid #555; border-radius: 4px; text-align: center; font-size: 10px; margin-bottom: 2px; } "
            "QProgressBar::chunk { background-color: #27ae60; border-radius: 3px; }"
        )

        cs_layout.addStretch(1)
        cs_layout.addWidget(self.lbl_cache_status)
        cs_layout.addWidget(self.cache_progress_bar)
        cs_layout.addStretch(1)

        self.cache_status_container.setVisible(False)
        self.statusBar().addWidget(self.cache_status_container, 1)

    def update_cache_progress(self, current, total, current_name=""):
        if total > 0 and current < total:
            self.cache_status_container.setVisible(True)
            self.cache_progress_bar.setMaximum(total)
            self.cache_progress_bar.setValue(current)
            
            if current_name:
                txt = t("cache_downloading_file", current, total, current_name)
            else:
                txt = t("cache_downloading_general", current, total)
                
            self.lbl_cache_status.setText(txt)
        else:
            self.cache_status_container.setVisible(False)

    def on_cache_finished(self):
        self.cache_status_container.setVisible(False)

    def setup_easy_weapon_page_ui(self):
        if not hasattr(self, 'right_stack') or self.right_stack.count() < 2:
            return
        if getattr(self, '_weapon_page_reorganized', False):
            return
        self._weapon_page_reorganized = True

        weapon_page = self.right_stack.widget(1)
        if not weapon_page:
            return

        lbl_sub = getattr(self, 'lbl_sub', None) or getattr(self, 'lbl_sub_weapon', None)
        lbl_special = getattr(self, 'lbl_special', None) or getattr(self, 'lbl_special_weapon', None)
        lbl_points = getattr(self, 'lbl_points', None) or getattr(self, 'lbl_special_points', None)

        for lbl in weapon_page.findChildren(QLabel):
            if lbl in (getattr(self, 'lbl_weapon_title', None), getattr(self, 'img_lbl', None)):
                continue
            txt = lbl.text().lower()
            if not lbl_sub and ("sub" in txt or "secondaire" in txt):
                lbl_sub = lbl
            elif not lbl_points and ("point" in txt):
                lbl_points = lbl
            elif not lbl_special and ("special" in txt or "spécial" in txt):
                lbl_special = lbl

        old_layout = weapon_page.layout()
        if old_layout is not None:
            def clear_layout(l):
                while l.count():
                    item = l.takeAt(0)
                    if item.layout():
                        clear_layout(item.layout())
            clear_layout(old_layout)
            QWidget().setLayout(old_layout)

        self.weapon_card = QFrame()
        self.weapon_card.setObjectName("weapon_card")
        self.weapon_card.setFixedWidth(680)
        self.weapon_card.setStyleSheet(
            "#weapon_card { "
            "  background-color: rgba(255, 255, 255, 0.04); "
            "  border: 1px solid rgba(255, 255, 255, 0.14); "
            "  border-radius: 12px; "
            "} "
            "QLabel { background: transparent; } "
            "QComboBox, QLineEdit { "
            "  background-color: #4a4a50; "
            "  border: 1px solid #5a5a62; "
            "  border-radius: 8px; "
            "  color: #ffffff; "
            "  font-size: 14px; "
            "  padding: 0 12px; "
            "  min-height: 42px; "
            "} "
            "QComboBox:hover, QLineEdit:hover { "
            "  border-color: #707078; "
            "  background-color: #525258; "
            "} "
            "QComboBox:focus, QLineEdit:focus { "
            "  border-color: #27ae60; "
            "} "
            "QComboBox QAbstractItemView { "
            "  background-color: #38383e; "
            "  border: 1px solid #55555a; "
            "  selection-background-color: #27ae60; "
            "  color: #ffffff; "
            "  font-size: 13px; "
            "  padding: 4px; "
            "}"
        )

        card_l = QVBoxLayout(self.weapon_card)
        card_l.setContentsMargins(36, 28, 36, 28)
        card_l.setSpacing(16)
        card_l.setAlignment(Qt.AlignmentFlag.AlignCenter)

        old_img = getattr(self, 'img_lbl', None)
        self.img_lbl = AnimatedWeaponImage()
        self.img_lbl.setFixedSize(160, 160)
        self.img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_lbl.setStyleSheet(
            "QLabel { "
            "  background-color: rgba(0, 0, 0, 0.22); "
            "  border: 1px solid rgba(255, 255, 255, 0.08); "
            "  border-radius: 10px; "
            "}"
        )
        card_l.addWidget(self.img_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
        if old_img:
            old_img.deleteLater()

        old_title = getattr(self, 'lbl_weapon_title', None)
        self.lbl_weapon_title = AnimatedTitleLabel(t("lbl_weapon_name"))
        self.lbl_weapon_title.setMinimumSize(0, 0)
        self.lbl_weapon_title.setMaximumSize(16777215, 16777215)
        self.lbl_weapon_title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        self.lbl_weapon_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_weapon_title.setWordWrap(True)
        self.lbl_weapon_title.setStyleSheet(
            "QLabel { "
            "  color: #ffffff; "
            "  font-size: 16px; "
            "  font-weight: bold; "
            "  padding: 8px 14px; "
            "}"
        )
        self.lbl_weapon_title.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.lbl_weapon_title.customContextMenuRequested.connect(self.on_title_context_menu)
        card_l.addWidget(self.lbl_weapon_title)
        if old_title:
            old_title.deleteLater()

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); max-height: 1px; margin: 6px 0;")
        card_l.addWidget(sep)

        form_widget = QWidget()
        form_grid = QGridLayout(form_widget)
        form_grid.setContentsMargins(0, 6, 0, 0)
        form_grid.setHorizontalSpacing(18)
        form_grid.setVerticalSpacing(14)
        form_grid.setColumnStretch(1, 1)

        label_style = "QLabel { font-size: 14px; font-weight: bold; color: #dcdde1; }"

        row = 0
        if lbl_sub and hasattr(self, 'combo_sub'):
            lbl_sub.setStyleSheet(label_style)
            lbl_sub.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.combo_sub.setIconSize(QSize(32, 32))
            self.combo_sub.setFixedHeight(44)
            self.combo_sub.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.combo_sub.customContextMenuRequested.connect(self.on_combo_sub_context_menu)
            self.combo_sub.installEventFilter(self)
            self.combo_sub.currentIndexChanged.connect(self.on_easy_form_changed)
            form_grid.addWidget(lbl_sub, row, 0)
            form_grid.addWidget(self.combo_sub, row, 1)
            row += 1

        if lbl_special and hasattr(self, 'combo_special'):
            lbl_special.setStyleSheet(label_style)
            lbl_special.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.combo_special.setIconSize(QSize(32, 32))
            self.combo_special.setFixedHeight(44)
            self.combo_special.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.combo_special.customContextMenuRequested.connect(self.on_combo_special_context_menu)
            self.combo_special.installEventFilter(self)
            self.combo_special.currentIndexChanged.connect(self.on_easy_form_changed)
            form_grid.addWidget(lbl_special, row, 0)
            form_grid.addWidget(self.combo_special, row, 1)
            row += 1

        if lbl_points and hasattr(self, 'spin_special_points'):
            lbl_points.setStyleSheet(label_style)
            lbl_points.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.spin_special_points.setFixedHeight(44)
            self.spin_special_points.installEventFilter(self)
            self.spin_special_points.textChanged.connect(self.on_easy_form_changed)
            form_grid.addWidget(lbl_points, row, 0)
            form_grid.addWidget(self.spin_special_points, row, 1)
            row += 1

        card_l.addWidget(form_widget)

        scroll_area = QScrollArea(weapon_page)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("background: transparent; border: none;")

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self.weapon_card)
        scroll_area.setWidget(scroll_content)

        main_page_layout = QVBoxLayout(weapon_page)
        main_page_layout.setContentsMargins(0, 0, 0, 0)
        main_page_layout.addWidget(scroll_area)

    def get_combo_cached_icon(self, img_name):
        if not hasattr(self, '_combo_icon_cache'):
            self._combo_icon_cache = {}
        if not img_name:
            return QIcon()
        if img_name in self._combo_icon_cache:
            return self._combo_icon_cache[img_name]

        icon_path = os.path.join(CACHE_DIR, img_name) if img_name else ""
        img = QImage()
        if icon_path and os.path.exists(icon_path):
            img.load(icon_path)

        if img.isNull():
            dummy_path = os.path.join(CACHE_DIR, "Dummy.png")
            if os.path.exists(dummy_path):
                img.load(dummy_path)

        if not img.isNull():
            scaled = img.scaled(28, 28, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            square = QImage(32, 32, QImage.Format.Format_ARGB32_Premultiplied)
            square.fill(Qt.GlobalColor.transparent)
            painter = QPainter(square)
            painter.drawImage((32 - scaled.width()) // 2, (32 - scaled.height()) // 2, scaled)
            painter.end()
            icon = QIcon(QPixmap.fromImage(square))
            self._combo_icon_cache[img_name] = icon
            return icon
        return self.get_placeholder_icon(32, 32)

    def animate_combo_icon(self, combo):
        if not combo or not combo.isVisible():
            return

        idx = combo.currentIndex()
        if idx < 0:
            return

        data = combo.itemData(idx)
        if not data or str(data).strip() == "":
            return

        base_icon = combo.itemIcon(idx)
        if not base_icon or base_icon.isNull():
            return

        icon_sz = QSize(32, 32)
        base_pix = base_icon.pixmap(icon_sz)
        if base_pix.isNull():
            return

        if hasattr(combo, "_icon_anim_info") and combo._icon_anim_info:
            prev_idx, prev_base_icon, prev_anim = combo._icon_anim_info
            if prev_anim and prev_anim.state() == QVariantAnimation.State.Running:
                prev_anim.stop()
            if prev_base_icon and not prev_base_icon.isNull():
                combo.setItemIcon(prev_idx, prev_base_icon)
            combo._icon_anim_info = None

        anim = QVariantAnimation(combo)
        anim.setDuration(380)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutBack)

        def on_step(val):
            if combo.currentIndex() != idx:
                anim.stop()
                return

            scale = 0.55 + 0.45 * val
            canvas = QPixmap(icon_sz)
            canvas.fill(Qt.GlobalColor.transparent)

            painter = QPainter(canvas)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            painter.setOpacity(min(1.0, max(0.0, val * 1.6)))

            painter.translate(16.0, 16.0)
            painter.scale(scale, scale)
            painter.drawPixmap(-16, -16, base_pix)
            painter.end()

            combo.setItemIcon(idx, QIcon(canvas))
            combo.update()

        def on_end():
            combo.setItemIcon(idx, base_icon)
            combo._icon_anim_info = None
            combo.update()

        anim.valueChanged.connect(on_step)
        anim.finished.connect(on_end)
        combo._icon_anim_info = (idx, base_icon, anim)
        on_step(0.0)
        anim.start()

    def animate_number_font(self, widget):
        if not widget or not widget.isVisible():
            return

        if hasattr(widget, "_font_anim") and widget._font_anim and widget._font_anim.state() == QVariantAnimation.State.Running:
            widget._font_anim.stop()

        anim = QVariantAnimation(widget)
        anim.setDuration(360)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutBack)

        def on_step(val):
            scale = 0.70 + 0.30 * val
            sz = max(8, int(14 * scale))
            widget.setStyleSheet(f"font-size: {sz}px;")
            widget.update()

        def on_end():
            widget.setStyleSheet("")
            widget.update()

        anim.valueChanged.connect(on_step)
        anim.finished.connect(on_end)
        widget._font_anim = anim
        anim.start()

    def manage_checkboxes_for_mode(self):
        super().manage_checkboxes_for_mode()
        if hasattr(self, 'chk_grid_w'):
            self.chk_grid_w.setVisible(self.is_easy_mode and self.easy_mode_page == 0)
        if hasattr(self, 'expert_chk_container'):
            self.expert_chk_container.setVisible(not self.is_easy_mode)

    def show_prev_page(self):
        if self.easy_mode_page > 0:
            self.switch_easy_page(self.easy_mode_page - 1)

    def show_next_page(self):
        if self.easy_mode_page < 1:
            self.switch_easy_page(self.easy_mode_page + 1)

    def toggle_easy_page(self):
        target = 1 if self.easy_mode_page == 0 else 0
        self.switch_easy_page(target)

    def switch_easy_page(self, page_index):
        if getattr(self, '_page_switch_busy', False):
            return
        if page_index == self.easy_mode_page:
            return

        self._page_switch_busy = True
        QTimer.singleShot(220, lambda: setattr(self, '_page_switch_busy', False))

        if page_index == 1 and not get_badge_notice_dismissed():
            b_count = len(self.rsdb_data[self.badge_file]) if (self.badge_file and self.badge_file in self.rsdb_data) else 0
            dlg = BadgeNoticeDialog(b_count, self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                if dlg.chk_dont_show.isChecked():
                    save_badge_notice_dismissed(True)
            else:
                self.easy_mode_page = 0
                self.update_page_nav_state()
                return

        self.easy_mode_page = page_index
        self.update_page_nav_state()
        if not self.is_easy_mode:
            return

        if self.easy_mode_page == 0:
            if hasattr(self, 'left_frame'):
                self.left_frame.setVisible(True)
                self.left_frame.setMinimumWidth(280)
            self.right_stack.setCurrentIndex(1)
            self.splitter.setSizes([340, max(500, self.splitter.width() - 340)])
            self.refresh_left_panel()
            self._restore_table_selection()
        else:
            if hasattr(self, 'left_frame'):
                self.left_frame.setMinimumWidth(0)
                self.left_frame.setVisible(False)
            self.right_stack.setCurrentIndex(2)
            self.populate_badge_grid()
            QTimer.singleShot(0, lambda: self.adjust_badge_grid_spacing(animate=False))
            if hasattr(self, 'badge_fade_anim'):
                self.badge_fade_anim.stop()
                self.badge_opacity_effect.setOpacity(0.2)
                self.badge_fade_anim.setStartValue(0.2)
                self.badge_fade_anim.setEndValue(1.0)
                self.badge_fade_anim.start()

        self.update_action_buttons()

    def update_page_nav_state(self):
        if not hasattr(self, 'nav_container'):
            return

        self.nav_container.setVisible(self.is_easy_mode)
        self.btn_page_prev.setVisible(self.is_easy_mode)
        self.btn_page_title.setVisible(self.is_easy_mode)
        self.btn_page_next.setVisible(self.is_easy_mode)

        if hasattr(self, 'top_header_widget'):
            self.top_header_widget.setVisible(True)
            if self.top_header_widget.layout():
                if self.is_easy_mode and self.easy_mode_page == 0:
                    self.top_header_widget.layout().setContentsMargins(0, 0, 0, 8)
                else:
                    self.top_header_widget.layout().setContentsMargins(0, 0, 0, 0)

        if hasattr(self, 'chk_grid_w'):
            self.chk_grid_w.setVisible(self.is_easy_mode and self.easy_mode_page == 0)

        self.btn_page_prev.setEnabled(self.is_data_loaded() and self.easy_mode_page > 0)
        self.btn_page_next.setEnabled(self.is_data_loaded() and self.easy_mode_page < 1)

        if not self.is_easy_mode:
            self.lbl_header_title.setText(t("page_expert_title"))
            self.lbl_header_desc.setText(t("page_expert_desc"))
        elif self.easy_mode_page == 1:
            self.btn_page_title.setText(t("page_badges"))
            self.lbl_header_title.setText(t("page_badges_title"))
            self.lbl_header_desc.setText(t("page_badges_desc"))
        else:
            self.btn_page_title.setText(t("page_weapons"))
            self.lbl_header_title.setText(t("page_weapons_title"))
            self.lbl_header_desc.setText(t("page_weapons_desc"))

    def closeEvent(self, event):
        if getattr(self, '_is_loading_tree', False):
            log("[INFO] Operation cancelled by user via Window Close.")
            self.cancel_operation = True
            event.ignore()
        else:
            if hasattr(self, 'cache_worker') and self.cache_worker and self.cache_worker.isRunning():
                self.cache_worker.cancel()
                self.cache_worker.wait()
            event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if getattr(self, 'is_easy_mode', False) and getattr(self, 'easy_mode_page', 0) == 1:
            self.adjust_badge_grid_spacing(animate=False)

    def preload_ram(self):
        if not self.rsdb_data:
            return

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

    def on_red_button_clicked(self):
        if self.easy_mode_page == 1:
            self.unlock_all_badges()
        else:
            self.zero_all_special_points()

    def update_action_buttons(self):
        if not self.is_easy_mode:
            self.btn_preload.setVisible(True)
            self.btn_zero_all.setVisible(False)
            if hasattr(self, 'btn_unlock_shop'):
                self.btn_unlock_shop.setVisible(False)
        else:
            self.btn_preload.setVisible(False)
            self.btn_zero_all.setVisible(True)
            if hasattr(self, 'btn_unlock_shop'):
                self.btn_unlock_shop.setVisible(self.easy_mode_page == 0)
                has_weapons = bool(self.weapon_main_file and self.weapon_main_file in self.rsdb_data)
                self.btn_unlock_shop.setEnabled(self.is_data_loaded() and has_weapons)

            if self.easy_mode_page == 0:
                self.btn_zero_all.setText(t("btn_zero_special"))
                has_weapons = bool(self.weapon_main_file and self.weapon_main_file in self.rsdb_data)
                self.btn_zero_all.setEnabled(self.is_data_loaded() and has_weapons and not getattr(self, '_unlock_in_cooldown', False))
            else:
                self.btn_zero_all.setText(t("btn_unlock_all_badges"))
                has_badges = bool(self.badge_file and self.badge_file in self.rsdb_data)
                self.btn_zero_all.setEnabled(self.is_data_loaded() and has_badges and not getattr(self, '_unlock_in_cooldown', False))

    def eventFilter(self, obj, event):
        if hasattr(self, 'badge_list_w') and (obj == self.badge_list_w or (hasattr(self.badge_list_w, 'viewport') and obj == self.badge_list_w.viewport())):
            if event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
                if getattr(self, 'is_easy_mode', False) and getattr(self, 'easy_mode_page', 0) == 1:
                    self.adjust_badge_grid_spacing(animate=False)

            if event.type() == QEvent.Type.KeyPress:
                if event.key() == Qt.Key.Key_Space:
                    if not event.isAutoRepeat():
                        self._space_held = True
                        curr = self.badge_list_w.currentItem()
                        if curr:
                            self._toggle_or_set_badge_item(curr, set_target=True)
                    return True

                elif event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
                    res = super().eventFilter(obj, event)
                    if getattr(self, '_space_held', False):
                        curr = self.badge_list_w.currentItem()
                        if curr:
                            self._apply_space_state_to_badge(curr)
                    return res

            elif event.type() == QEvent.Type.KeyRelease:
                if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
                    self._space_held = False
                    self._space_target_state = None
                    return True

            return False

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
            QMessageBox.critical(self, t("err_title"), t("err_updater_missing"))
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
            if self.is_easy_mode and self.easy_mode_page == 1:
                self.populate_badge_grid()
            else:
                self.refresh_left_panel()
                self._restore_table_selection()

    def ui_update_texts(self):
        super().ui_update_texts()
        self.update_page_nav_state()
        self.update_action_buttons()
        self.update_loaded_state_ui()
        if hasattr(self, 'btn_unlock_shop'):
            self.btn_unlock_shop.setText(t("btn_unlock_shop"))

    def on_filter_toggled(self, state):
        if not self.is_easy_mode:
            return

        save_hide_filenames(self.chk_hide_filenames.isChecked())
        save_hide_coop(self.chk_hide_coop.isChecked())
        save_hide_mission(self.chk_hide_mission.isChecked())
        save_hide_notfound(self.chk_hide_notfound.isChecked())

        if self.easy_mode_page == 1:
            return
        else:
            current_item = self.table_w.currentItem()
            saved_user_data = current_item.data(Qt.ItemDataRole.UserRole) if current_item else None
            self.refresh_left_panel()
            self.build_easy_mode_options()
            self._restore_table_selection(preferred_data=saved_user_data)

            if hasattr(self, 'table_fade_anim'):
                self.table_fade_anim.stop()
                self.table_opacity.setOpacity(0.35)
                self.table_fade_anim.setStartValue(0.35)
                self.table_fade_anim.setEndValue(1.0)
                self.table_fade_anim.start()

    def toggle_mode(self):
        if not self.is_easy_mode and self.current_table_name and isinstance(self.current_table_name, str) and self.current_table_name in self.rsdb_data:
            try:
                self.rsdb_data[self.current_table_name] = TreeHandler.build_dict(self.tree_w.invisibleRootItem())
                self.modified_files.add(self.current_table_name)
            except:
                pass

        self.is_easy_mode = not self.is_easy_mode
        save_editor_mode(self.is_easy_mode)
        self.apply_mode()

    def apply_mode(self):
        super().apply_mode()
        self.update_page_nav_state()
        if hasattr(self, 'chk_grid_w'):
            self.chk_grid_w.setVisible(self.is_easy_mode and self.easy_mode_page == 0)
        if hasattr(self, 'expert_chk_container'):
            self.expert_chk_container.setVisible(not self.is_easy_mode)

        if self.is_easy_mode:
            if self.easy_mode_page == 1:
                if hasattr(self, 'left_frame'):
                    self.left_frame.setMinimumWidth(0)
                    self.left_frame.setVisible(False)
                self.right_stack.setCurrentIndex(2)
                self.populate_badge_grid()
            else:
                if hasattr(self, 'left_frame'):
                    self.left_frame.setVisible(True)
                    self.left_frame.setMinimumWidth(280)
                self.right_stack.setCurrentIndex(1)
                self.splitter.setSizes([340, max(500, self.splitter.width() - 340)])
                self.refresh_left_panel()
                self._restore_table_selection()
        else:
            if hasattr(self, 'left_frame'):
                self.left_frame.setVisible(True)
                self.left_frame.setMinimumWidth(280)
            self.right_stack.setCurrentIndex(0)
            self.splitter.setSizes([340, max(500, self.splitter.width() - 340)])
            self.refresh_left_panel()
            self._restore_table_selection()
        self.update_action_buttons()

    def get_weapon_display_name(self, row_id):
        translated = self.data_manager.get_exact_translation(row_id, row_id)

        if not self.chk_hide_filenames.isChecked():
            if translated == row_id or (translated.startswith(row_id) and f" ({row_id})" in translated):
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
            if "SpIkuraShoot" in row_id: 
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
        if not item:
            return
        menu = QMenu(self)
        copy_action = menu.addAction(t("ctx_copy_name"))
        action = menu.exec(self.table_w.viewport().mapToGlobal(pos))
        if action == copy_action:
            QApplication.clipboard().setText(item.text())

    def on_tree_context_menu(self, pos):
        item = self.tree_w.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        copy_prop = menu.addAction(t("ctx_copy_prop"))
        copy_val = menu.addAction(t("ctx_copy_val"))
        action = menu.exec(self.tree_w.viewport().mapToGlobal(pos))
        if action == copy_prop:
            QApplication.clipboard().setText(item.text(0))
        elif action == copy_val:
            QApplication.clipboard().setText(item.text(1))

    def on_title_context_menu(self, pos):
        if not self.lbl_weapon_title.text():
            return
        menu = QMenu(self)
        copy_action = menu.addAction(t("ctx_copy_name"))
        action = menu.exec(self.lbl_weapon_title.mapToGlobal(pos))
        if action == copy_action:
            QApplication.clipboard().setText(self.lbl_weapon_title.text())

    def on_combo_sub_context_menu(self, pos):
        if self.combo_sub.count() == 0:
            return
        menu = QMenu(self)
        copy_action = menu.addAction(t("ctx_copy_name"))
        action = menu.exec(self.combo_sub.mapToGlobal(pos))
        if action == copy_action:
            QApplication.clipboard().setText(self.combo_sub.currentText())

    def on_combo_special_context_menu(self, pos):
        if self.combo_special.count() == 0:
            return
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
                item.setData(Qt.ItemDataRole.UserRole + 1, img_name)

                icon = self.get_cached_icon(img_name)
                if not icon.isNull():
                    item.setIcon(icon)

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

    def _update_icons_for_image(self, img_name):
        if hasattr(self, '_weapon_icon_cache') and img_name in self._weapon_icon_cache:
            del self._weapon_icon_cache[img_name]
        if hasattr(self, '_combo_icon_cache') and img_name in self._combo_icon_cache:
            del self._combo_icon_cache[img_name]
        if hasattr(self, '_badge_pix_cache') and img_name in self._badge_pix_cache:
            del self._badge_pix_cache[img_name]
        if hasattr(self, '_badge_icon_cache') and img_name in self._badge_icon_cache:
            del self._badge_icon_cache[img_name]

        icon = self.get_cached_icon(img_name)
        if not icon.isNull():
            for row in range(self.table_w.rowCount()):
                it = self.table_w.item(row, 0)
                if it and it.data(Qt.ItemDataRole.UserRole + 1) == img_name:
                    it.setIcon(icon)
                    if hasattr(self, 'weapon_delegate'):
                        self.weapon_delegate.trigger_icon_animation(row)

        if hasattr(self, '_badge_items_by_image'):
            items = self._badge_items_by_image.get(img_name, [])
            if items:
                b_icon = self.get_badge_icon(img_name)
                b_pix = self.get_badge_pixmap(img_name)
                for b_it in items:
                    b_it.setIcon(b_icon)
                    if b_pix:
                        b_it.setData(Qt.ItemDataRole.UserRole + 2, b_pix)
                    if hasattr(self, 'badge_delegate'):
                        u_idx = b_it.data(Qt.ItemDataRole.UserRole)
                        self.badge_delegate.trigger_icon_animation(u_idx, b_it)

        combo_icon = self.get_combo_cached_icon(img_name)
        if hasattr(self, 'combo_sub') and hasattr(self, 'sub_options'):
            for s_idx, opt in enumerate(self.sub_options):
                if opt[2] == img_name:
                    self.combo_sub.setItemIcon(s_idx, combo_icon)

        if hasattr(self, 'combo_special') and hasattr(self, 'special_options'):
            for sp_idx, opt in enumerate(self.special_options):
                if opt[2] == img_name:
                    self.combo_special.setItemIcon(sp_idx, combo_icon)

    def on_single_image_cached(self, img_name):
        self._update_icons_for_image(img_name)

        if self.is_easy_mode and self.easy_mode_page == 0:
            if getattr(self, '_current_weapon_img', None) == img_name:
                local_p = os.path.join(CACHE_DIR, img_name)
                if os.path.exists(local_p):
                    img = QImage(local_p)
                    if not img.isNull() and hasattr(self, 'img_lbl'):
                        scaled = img.scaled(136, 136, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        square = QImage(160, 160, QImage.Format.Format_ARGB32_Premultiplied)
                        square.fill(Qt.GlobalColor.transparent)
                        painter = QPainter(square)
                        painter.drawImage((160 - scaled.width()) // 2, (160 - scaled.height()) // 2, scaled)
                        painter.end()
                        self.img_lbl.setPixmap(QPixmap.fromImage(square), animate=True)

    def finalize_rsdb_load(self):
        self._all_unlocked_popup_shown = False
        self.build_easy_mode_options()
        if self.is_easy_mode and self.easy_mode_page == 1:
            self.populate_badge_grid()
        else:
            self.refresh_left_panel()
            self._restore_table_selection()

        if hasattr(self, '_saved_splitter_sizes') and sum(self._saved_splitter_sizes) > 0:
            self.splitter.setSizes(self._saved_splitter_sizes)
        self.update_loaded_state_ui()

    def get_cached_icon(self, img_name):
        if not hasattr(self, '_weapon_icon_cache'):
            self._weapon_icon_cache = {}
        if img_name in self._weapon_icon_cache:
            return self._weapon_icon_cache[img_name]

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
            icon = QIcon(QPixmap.fromImage(square))
            self._weapon_icon_cache[img_name] = icon
            return icon
        return QIcon()

    def update_combo_icon(self, index, icon, is_sub=True, img_name=None):
        target_combo = self.combo_sub if is_sub else self.combo_special
        if not img_name:
            options = self.sub_options if is_sub else self.special_options
            if 0 <= index < len(options):
                img_name = options[index][2]
        proper_icon = self.get_combo_cached_icon(img_name) if img_name else icon
        target_combo.setItemIcon(index, proper_icon)

    def build_easy_mode_options(self):
        placeholder = self.get_placeholder_icon(32, 32)

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
            icon = self.get_combo_cached_icon(img_name) if img_name else QIcon()
            if img_name and icon.isNull():
                icon = placeholder

            self.combo_sub.addItem(icon, label, path)
            if is_filtered:
                self.combo_sub.setItemData(idx, QSize(0, 0), Qt.ItemDataRole.SizeHintRole)
            if img_name and self.get_cached_icon(img_name).isNull():
                local_p = os.path.join(CACHE_DIR, img_name)
                urls = self.get_image_urls(img_name)
                worker = ComboIconWorker(idx, urls, local_p)
                worker.finished.connect(lambda i, ic, im=img_name: self.update_combo_icon(i, ic, is_sub=True, img_name=im))
                self.combo_workers.append(worker)
                worker.start()

        self.combo_special.clear()
        for idx, (path, label, img_name, is_filtered) in enumerate(self.special_options):
            icon = self.get_combo_cached_icon(img_name) if img_name else QIcon()
            if img_name and icon.isNull():
                icon = placeholder

            self.combo_special.addItem(icon, label, path)
            if is_filtered:
                self.combo_special.setItemData(idx, QSize(0, 0), Qt.ItemDataRole.SizeHintRole)
            if img_name and self.get_cached_icon(img_name).isNull():
                local_p = os.path.join(CACHE_DIR, img_name)
                urls = self.get_image_urls(img_name)
                worker = ComboIconWorker(idx, urls, local_p)
                worker.finished.connect(lambda i, ic, im=img_name: self.update_combo_icon(i, ic, is_sub=False, img_name=im))
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
        filter_text = text.lower()

        if self.is_easy_mode and self.easy_mode_page == 1 and hasattr(self, 'badge_list_w'):
            for idx in range(self.badge_list_w.count()):
                it = self.badge_list_w.item(idx)
                if it:
                    hide = filter_text not in it.text().lower()
                    it.setHidden(hide)
                    if not hide:
                        displayed_count += 1
            self.update_badge_count()
            return

        for row in range(self.table_w.rowCount()):
            item = self.table_w.item(row, 0)
            if item:
                is_hidden = filter_text not in item.text().lower()
                self.table_w.setRowHidden(row, is_hidden)
                if not is_hidden:
                    displayed_count += 1

        self._last_displayed = displayed_count
        current_row = self.get_current_visible_row_number()
        self.count_lbl.setText(t("count_info", getattr(self, '_last_total', 0), self._last_displayed, current_row, self._last_displayed))

    def on_table_current_changed(self, current, previous):
        if current:
            current_row = self.get_current_visible_row_number()
            self.count_lbl.setText(t("count_info", getattr(self, '_last_total', 0), self._last_displayed, current_row, self._last_displayed))

        if not current:
            return

        self._pending_current_data = current.data(Qt.ItemDataRole.UserRole)
        self._pending_previous_data = previous.data(Qt.ItemDataRole.UserRole) if previous else None

        self.selection_timer.start(150)

    def _process_delayed_selection(self):
        if getattr(self, '_is_loading_tree', False):
            self.selection_timer.start(150)
            return

        current_data = getattr(self, '_pending_current_data', None)
        previous_data = getattr(self, '_pending_previous_data', None)

        if current_data is None:
            return

        if self.is_easy_mode:
            if not isinstance(current_data, int):
                return
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
                    except:
                        pass

                self.load_expert_mode_file(file_name)
            finally:
                self.table_w.setEnabled(True) 
                self.btn_mode.setEnabled(True)
                self.btn_open.setEnabled(True)
                self.btn_save.setEnabled(True)
                self._is_loading_tree = False
                self.cancel_operation = False

    def load_expert_mode_file(self, file_name):
        if self.current_table_name == file_name:
            return

        data = self.rsdb_data.get(file_name)
        if data is None:
            return

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
        self.lbl_weapon_title.setText(display_title, animate=True)
        self.lbl_weapon_title.updateGeometry()

        _, img_name, _, _ = self.data_manager.guess_image_and_name(row_id)
        self._current_weapon_img = img_name
        icon_path = os.path.join(CACHE_DIR, img_name)
        img = QImage()
        if os.path.exists(icon_path):
            img.load(icon_path)

        dummy_path = os.path.join(CACHE_DIR, "Dummy.png")
        if img.isNull() and os.path.exists(dummy_path):
            img.load(dummy_path)

        if hasattr(self, 'img_worker') and self.img_worker and self.img_worker.isRunning():
            try:
                self.img_worker.finished.disconnect()
            except Exception:
                pass

        if not img.isNull():
            scaled = img.scaled(136, 136, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            square = QImage(160, 160, QImage.Format.Format_ARGB32_Premultiplied)
            square.fill(Qt.GlobalColor.transparent)
            painter = QPainter(square)
            painter.drawImage((160 - scaled.width()) // 2, (160 - scaled.height()) // 2, scaled)
            painter.end()
            self.img_lbl.setPixmap(QPixmap.fromImage(square), animate=True)
        else:
            self.img_lbl.clear()
            self.img_lbl.setText(t("img_unavail"))

        if img_name != "Dummy.png" and (not os.path.exists(icon_path) or os.path.getsize(icon_path) == 0):
            urls = self.get_image_urls(img_name)
            self.img_worker = ImageDownloadWorker(urls)
            curr_target = img_name
            curr_path = icon_path

            def on_loaded(loaded_img, target=curr_target, p=curr_path):
                if getattr(self, '_current_weapon_img', None) == target:
                    self.cache_and_show_image(loaded_img, p)
                elif not loaded_img.isNull() and p:
                    loaded_img.save(p)
                    self._update_icons_for_image(os.path.basename(p))

            self.img_worker.finished.connect(on_loaded)
            self.img_worker.start()

            if hasattr(self, 'cache_worker') and self.cache_worker and self.cache_worker.isRunning():
                self.cache_worker.prioritize(img_name)
        elif img_name == "Dummy.png" and (not os.path.exists(dummy_path) or os.path.getsize(dummy_path) == 0):
            urls = self.get_image_urls("Dummy.png")
            self.img_worker = ImageDownloadWorker(urls)
            def on_dummy_loaded(loaded_img):
                if not loaded_img.isNull() and dummy_path:
                    loaded_img.save(dummy_path)
                    if getattr(self, '_current_weapon_img', None) == "Dummy.png":
                        self.cache_and_show_image(loaded_img, dummy_path)
                    self._update_icons_for_image("Dummy.png")
            self.img_worker.finished.connect(on_dummy_loaded)
            self.img_worker.start()

        old_sub = self._last_weapon_sub
        old_sp = self._last_weapon_sp

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
        try:
            pts_str = str(int(sp_points))
        except:
            pts_str = "0"
        self.spin_special_points.setText(pts_str)

        self.combo_sub.blockSignals(False)
        self.combo_special.blockSignals(False)
        self.spin_special_points.blockSignals(False)

        if old_sub is not None and old_sub != sub_path and sub_path:
            sub_img = None
            for p, _, im, _ in self.sub_options:
                if p == sub_path:
                    sub_img = im
                    break
            if sub_img and os.path.exists(os.path.join(CACHE_DIR, sub_img)):
                self.animate_combo_icon(self.combo_sub)

        if old_sp is not None and old_sp != sp_path and sp_path:
            sp_img = None
            for p, _, im, _ in self.special_options:
                if p == sp_path:
                    sp_img = im
                    break
            if sp_img and os.path.exists(os.path.join(CACHE_DIR, sp_img)):
                self.animate_combo_icon(self.combo_special)

        self._last_weapon_sub = sub_path
        self._last_weapon_sp = sp_path

    def cache_and_show_image(self, image, local_path):
        if getattr(self, '_current_weapon_img', None) != os.path.basename(local_path):
            if not image.isNull() and local_path:
                image.save(local_path)
                self._update_icons_for_image(os.path.basename(local_path))
            return

        if image.isNull():
            dummy_path = os.path.join(CACHE_DIR, "Dummy.png")
            if os.path.exists(dummy_path):
                image = QImage(dummy_path)

        if not image.isNull():
            if local_path and os.path.basename(local_path) != "Dummy.png":
                image.save(local_path)

            scaled = image.scaled(136, 136, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            square = QImage(160, 160, QImage.Format.Format_ARGB32_Premultiplied)
            square.fill(Qt.GlobalColor.transparent)
            painter = QPainter(square)
            painter.drawImage((160 - scaled.width()) // 2, (160 - scaled.height()) // 2, scaled)
            painter.end()
            self.img_lbl.setPixmap(QPixmap.fromImage(square), animate=True)

            if local_path:
                self._update_icons_for_image(os.path.basename(local_path))
        else:
            self.img_lbl.clear()
            self.img_lbl.setText(t("img_unavail"))

    def on_easy_form_changed(self):
        if not self.is_easy_mode or self.current_table_name is None:
            return
        weapon = self.rsdb_data[self.weapon_main_file][self.current_table_name]

        sub_val = self.combo_sub.currentData()
        weapon["SubWeapon"] = sub_val if sub_val else None

        sp_val = self.combo_special.currentData()
        weapon["SpecialWeapon"] = sp_val if sp_val else None

        try:
            new_sp_point = int(self.spin_special_points.text())
        except ValueError:
            new_sp_point = 0
        orig = weapon.get("SpecialPoint", 0)

        type_name = type(orig).__name__
        if type_name in ['UInt', 'Int', 'Int64', 'UInt64'] and hasattr(byml, type_name):
            weapon["SpecialPoint"] = getattr(byml, type_name)(new_sp_point)
        else:
            weapon["SpecialPoint"] = new_sp_point

        self.modified_files.add(self.weapon_main_file)

    def unlock_all_shop_weapons(self):
        if not self.weapon_main_file or self.weapon_main_file not in self.rsdb_data:
            return

        if not self.ask_yes_no(t("warn_title"), t("msg_unlock_shop_warn"), default_no=True):
            return

        keys_to_zero = ["Season", "ShopUnlockRank", "ShopPrice"]

        for weapon in self.rsdb_data[self.weapon_main_file]:
            for key in keys_to_zero:
                if key in weapon:
                    orig = weapon[key]
                    t_name = type(orig).__name__
                    if t_name in ['UInt', 'Int', 'Int64', 'UInt64'] and hasattr(byml, t_name):
                        weapon[key] = getattr(byml, t_name)(0)
                    else:
                        weapon[key] = 0
                else:
                    weapon[key] = getattr(byml, 'Int')(0) if hasattr(byml, 'Int') else 0

        self.modified_files.add(self.weapon_main_file)

        QMessageBox.information(
            self,
            t("success_title"),
            t("msg_unlock_shop_done")
        )

        if self.current_table_name is not None and isinstance(self.current_table_name, int):
            self.load_easy_mode_weapon(self.current_table_name)

    def zero_all_special_points(self):
        if not self.weapon_main_file or self.weapon_main_file not in self.rsdb_data:
            return
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
            if os.path.exists(CONFIG_FILE):
                try:
                    os.remove(CONFIG_FILE)
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