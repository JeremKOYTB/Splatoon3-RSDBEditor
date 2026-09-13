import os
import copy
import math
import re
import byml

from PyQt6.QtWidgets import (
    QStyledItemDelegate, QStyleOptionButton, QStyle, QApplication,
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGridLayout,
    QLineEdit, QSizePolicy, QListWidget, QListWidgetItem, QAbstractItemView,
    QGraphicsOpacityEffect, QDialog, QMessageBox
)
from PyQt6.QtGui import QFont, QColor, QPixmap, QIcon, QPainter, QImage
from PyQt6.QtCore import Qt, QSize, QRect, QVariantAnimation, QEasingCurve, QTimer, QEvent, QPropertyAnimation

import translations
from translations import t
from components import BadgeNoticeDialog
from utils import CACHE_DIR, save_badge_notice_dismissed, get_badge_notice_dismissed


class BadgeCardDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_list = parent

        self._card_font = QFont()
        self._card_font.setPointSize(9)
        self._card_font.setBold(True)

        self.c_checked_bg = QColor(39, 174, 96, 115)
        self.c_checked_border = QColor(46, 204, 113, 230)

        self.c_checked_hover_bg = QColor(39, 174, 96, 145)
        self.c_checked_hover_border = QColor(46, 204, 113, 255)

        self.c_checked_sel_bg = QColor(46, 204, 113, 160)
        self.c_checked_sel_border = QColor(255, 255, 255, 240)

        self.c_normal_bg = QColor(255, 255, 255, 12)
        self.c_normal_border = QColor(255, 255, 255, 30)

        self.c_hover_bg = QColor(255, 255, 255, 12)
        self.c_hover_border = QColor(255, 255, 255, 60)

        self.c_sel_bg = QColor(255, 255, 255, 20)
        self.c_sel_border = QColor(255, 255, 255, 100)

        self.c_white_text = QColor("#ffffff")
        self._anim_cards = {}
        self._anim_icon_cards = {}
        self._max_concurrent_icons = 8

    def sizeHint(self, option, index):
        w = 155
        if hasattr(self, 'parent_list') and self.parent_list and self.parent_list.gridSize().isValid():
            gw = self.parent_list.gridSize().width()
            if gw > 50:
                w = gw
        return QSize(w, 148)

    def trigger_check_animation(self, idx):
        if idx in self._anim_cards:
            self._anim_cards[idx][1].stop()

        anim = QVariantAnimation(self)
        anim.setDuration(220)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutBack)

        def on_step(val):
            self._anim_cards[idx] = (val, anim)
            if self.parent_list and self.parent_list.viewport():
                self.parent_list.viewport().update()

        def on_end():
            self._anim_cards.pop(idx, None)
            if self.parent_list and self.parent_list.viewport():
                self.parent_list.viewport().update()

        anim.valueChanged.connect(on_step)
        anim.finished.connect(on_end)
        self._anim_cards[idx] = (0.0, anim)
        anim.start()

    def trigger_icon_animation(self, idx, item):
        if not self.parent_list or not item:
            return

        rect = self.parent_list.visualItemRect(item)
        if not self.parent_list.viewport().rect().intersects(rect):
            return

        if len(self._anim_icon_cards) >= self._max_concurrent_icons:
            return

        if idx in self._anim_icon_cards:
            self._anim_icon_cards[idx][1].stop()

        anim = QVariantAnimation(self)
        anim.setDuration(200)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        def on_step(val):
            self._anim_cards_icon = getattr(self, '_anim_icon_cards', {})
            self._anim_cards_icon[idx] = (val, anim)
            if self.parent_list and self.parent_list.viewport():
                self.parent_list.viewport().update(self.parent_list.visualItemRect(item))

        def on_end():
            self._anim_icon_cards.pop(idx, None)
            if self.parent_list and self.parent_list.viewport():
                self.parent_list.viewport().update(self.parent_list.visualItemRect(item))

        anim.valueChanged.connect(on_step)
        anim.finished.connect(on_end)
        self._anim_icon_cards[idx] = (0.0, anim)
        anim.start()

    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        idx = index.data(Qt.ItemDataRole.UserRole)
        orig_card_rect = option.rect.adjusted(3, 3, -3, -3)
        card_rect = QRect(orig_card_rect)

        check_val = index.data(Qt.ItemDataRole.CheckStateRole)
        is_checked = (check_val in (Qt.CheckState.Checked, 2, Qt.CheckState.Checked.value))
        is_hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        is_selected = bool(option.state & QStyle.StateFlag.State_Selected)

        if idx in self._anim_cards:
            prog = self._anim_cards[idx][0]
            offset = int(math.sin(prog * math.pi) * 3.5)
            card_rect = card_rect.adjusted(-offset, -offset, offset, offset)

        if is_checked:
            if is_selected:
                bg_color = self.c_checked_sel_bg
                border_color = self.c_checked_sel_border
            elif is_hovered:
                bg_color = self.c_checked_hover_bg
                border_color = self.c_checked_hover_border
            else:
                bg_color = self.c_checked_bg
                border_color = self.c_checked_border

            if idx in self._anim_cards:
                flash_alpha = int(115 + (1.0 - self._anim_cards[idx][0]) * 110)
                bg_color = QColor(46, 204, 113, min(255, flash_alpha))
        else:
            if is_selected:
                bg_color = self.c_sel_bg
                border_color = self.c_sel_border
            elif is_hovered:
                bg_color = self.c_hover_bg
                border_color = self.c_hover_border
            else:
                bg_color = self.c_normal_bg
                border_color = self.c_normal_border

        painter.setBrush(bg_color)
        painter.setPen(border_color)
        painter.drawRoundedRect(card_rect, 6, 6)

        chk_opt = QStyleOptionButton()
        chk_opt.rect = QRect(card_rect.left() + 7, card_rect.top() + 7, 18, 18)
        chk_opt.state = QStyle.StateFlag.State_Enabled
        if is_checked:
            chk_opt.state |= QStyle.StateFlag.State_On
        else:
            chk_opt.state |= QStyle.StateFlag.State_Off
        QApplication.style().drawPrimitive(QStyle.PrimitiveElement.PE_IndicatorCheckBox, chk_opt, painter)

        pix = index.data(Qt.ItemDataRole.UserRole + 2)
        if not isinstance(pix, QPixmap) or pix.isNull():
            icon = index.data(Qt.ItemDataRole.DecorationRole)
            if isinstance(icon, QIcon) and not icon.isNull():
                pix = icon.pixmap(QSize(76, 76))
            else:
                pix = None

        prog_icon = self._anim_icon_cards[idx][0] if idx in self._anim_icon_cards else 1.0

        if not pix or pix.isNull() or prog_icon < 1.0:
            placeholder_rect = QRect(orig_card_rect.center().x() - 38, orig_card_rect.top() + 6, 76, 76)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, 14))
            painter.drawRoundedRect(placeholder_rect, 8, 8)

        if pix and not pix.isNull():
            if prog_icon < 1.0:
                painter.save()
                painter.setOpacity(prog_icon)
                cx = orig_card_rect.center().x()
                cy = orig_card_rect.top() + 6 + pix.height() / 2.0
                painter.translate(cx, cy)
                scale = 0.70 + (0.30 * prog_icon)
                painter.scale(scale, scale)
                painter.drawPixmap(int(-pix.width() / 2.0), int(-pix.height() / 2.0), pix)
                painter.restore()
            else:
                icon_x = orig_card_rect.center().x() - pix.width() // 2
                icon_y = orig_card_rect.top() + 6
                painter.drawPixmap(icon_x, icon_y, pix)

        title = index.data(Qt.ItemDataRole.DisplayRole) or ""
        text_rect = QRect(orig_card_rect.left() + 4, orig_card_rect.top() + 84, orig_card_rect.width() - 8, orig_card_rect.height() - 86)

        painter.setFont(self._card_font)
        painter.setPen(self.c_white_text)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap, title)
        painter.restore()

    def editorEvent(self, event, model, option, index):
        if event.type() in (QEvent.Type.MouseButtonRelease, QEvent.Type.KeyPress):
            if event.type() == QEvent.Type.MouseButtonRelease and event.button() != Qt.MouseButton.LeftButton:
                return super().editorEvent(event, model, option, index)
            if event.type() == QEvent.Type.KeyPress and event.key() != Qt.Key.Key_Space:
                return super().editorEvent(event, model, option, index)

            card_rect = option.rect.adjusted(3, 3, -3, -3)
            if event.type() == QEvent.Type.KeyPress or card_rect.contains(event.pos()):
                is_orig_unlocked = bool(index.data(Qt.ItemDataRole.UserRole + 3))
                if is_orig_unlocked:
                    parent_win = self.parent_list.window() if (self.parent_list and hasattr(self.parent_list, 'window')) else None
                    QMessageBox.information(
                        parent_win,
                        t("badge_already_unlocked_title"),
                        t("msg_badge_already_unlocked")
                    )
                    return True

                check_val = index.data(Qt.ItemDataRole.CheckStateRole)
                is_checked = (check_val in (Qt.CheckState.Checked, 2, Qt.CheckState.Checked.value))
                new_state = Qt.CheckState.Unchecked if is_checked else Qt.CheckState.Checked
                model.setData(index, new_state, Qt.ItemDataRole.CheckStateRole)
                idx = index.data(Qt.ItemDataRole.UserRole)
                if isinstance(idx, int):
                    self.trigger_check_animation(idx)
                return True
        return super().editorEvent(event, model, option, index)


class BadgePageMixin:
    def is_badge_unlocked(self, badge):
        if not badge:
            return False
        cat = str(badge.get("Category", ""))
        sub1_str = str(badge.get("Sub1_Str", ""))
        try:
            sub1_int = int(badge.get("Sub1_Int", -1))
        except (ValueError, TypeError):
            sub1_int = -1
        try:
            sub2_int = int(badge.get("Sub2_Int", -1))
        except (ValueError, TypeError):
            sub2_int = -1
        return (cat == "SpendShop" and sub1_str == "Goods" and sub1_int == 0 and sub2_int == 0)

    def is_badge_file_saved(self):
        if not hasattr(self, 'modified_files') or not hasattr(self, 'badge_file'):
            return True
        return self.badge_file not in self.modified_files

    def check_badges_status(self):
        if not hasattr(self, 'badge_file') or not self.badge_file or not hasattr(self, 'rsdb_data') or self.badge_file not in self.rsdb_data:
            return {"all_unlocked_ram": False, "saved_on_disk": True}

        badges = self.rsdb_data[self.badge_file]
        all_unlocked_ram = (len(badges) > 0 and all(self.is_badge_unlocked(b) for b in badges))
        saved = self.is_badge_file_saved()

        return {
            "all_unlocked_ram": all_unlocked_ram,
            "saved_on_disk": saved
        }

    def get_estimated_version(self):
        for attr in ['detected_version', 'estimated_version', 'game_version', 'version']:
            val = getattr(self, attr, None)
            if val and str(val).strip() not in ["", "???", "None"]:
                return str(val)
        if hasattr(self, 'version_lbl') and self.version_lbl and hasattr(self.version_lbl, 'text') and self.version_lbl.text():
            txt = self.version_lbl.text()
            match = re.search(r'[\d\.]+', txt)
            if match:
                return match.group(0)
        return "???"

    def _toggle_or_set_badge_item(self, item, set_target=False):
        is_orig_unlocked = bool(item.data(Qt.ItemDataRole.UserRole + 3))
        if is_orig_unlocked:
            return

        check_val = item.checkState()
        is_checked = (check_val in (Qt.CheckState.Checked, 2, Qt.CheckState.Checked.value))
        
        new_state = Qt.CheckState.Unchecked if is_checked else Qt.CheckState.Checked
        if set_target:
            self._space_target_state = new_state
        
        item.setCheckState(new_state)
        idx = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(idx, int) and hasattr(self, 'badge_delegate'):
            self.badge_delegate.trigger_check_animation(idx)

    def _apply_space_state_to_badge(self, item):
        is_orig_unlocked = bool(item.data(Qt.ItemDataRole.UserRole + 3))
        if is_orig_unlocked:
            return

        target_state = getattr(self, '_space_target_state', Qt.CheckState.Checked)
        if target_state is None:
            target_state = Qt.CheckState.Checked

        if item.checkState() != target_state:
            item.setCheckState(target_state)
            idx = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(idx, int) and hasattr(self, 'badge_delegate'):
                self.badge_delegate.trigger_check_animation(idx)

    def on_badge_selection_changed(self, current, previous):
        if not current:
            return
        img_name = current.data(Qt.ItemDataRole.UserRole + 1)
        if not img_name:
            return
        local_path = os.path.join(CACHE_DIR, img_name)
        if not os.path.exists(local_path) or os.path.getsize(local_path) == 0:
            if hasattr(self, 'cache_worker') and self.cache_worker and self.cache_worker.isRunning():
                self.cache_worker.prioritize(img_name)

    def update_page_nav_state(self):
        is_badge_page = False
        if hasattr(self, 'right_stack') and hasattr(self, 'badge_container_widget'):
            is_badge_page = (self.right_stack.currentWidget() == self.badge_container_widget)

        if hasattr(self, 'btn_unlock_shop'):
            self.btn_unlock_shop.setVisible(not is_badge_page)
            self.btn_unlock_shop.setEnabled(not is_badge_page and (self.is_data_loaded() if hasattr(self, 'is_data_loaded') else True))

        if hasattr(self, 'btn_mode'):
            self.btn_mode.setVisible(not is_badge_page)

        if hasattr(self, 'center_filter_box') and self.center_filter_box.layout():
            if self.is_easy_mode and self.easy_mode_page == 0:
                self.center_filter_box.layout().setContentsMargins(0, 0, 15, 14)
            else:
                self.center_filter_box.layout().setContentsMargins(0, 0, 15, 0)

    def setup_badge_page_ui(self):
        self._space_held = False
        self._space_target_state = None

        BUTTON_WIDTH = 205
        TOTAL_RIGHT_W = BUTTON_WIDTH * 2 + 8

        self.nav_container = QWidget()
        self.nav_container.setFixedHeight(30)
        self.nav_container.setFixedWidth(TOTAL_RIGHT_W)
        nav_l = QHBoxLayout(self.nav_container)
        nav_l.setContentsMargins(0, 0, 0, 0)
        nav_l.setSpacing(0)

        btn_style_left = (
            "QPushButton { background-color: #68686e; color: #ffffff; font-size: 13px; font-weight: bold; "
            "border: 1px solid #55555a; border-right: none; border-top-left-radius: 4px; border-bottom-left-radius: 4px; "
            "border-top-right-radius: 0px; border-bottom-right-radius: 0px; } "
            "QPushButton:hover { background-color: #76767c; } "
            "QPushButton:pressed { background-color: #55555a; } "
            "QPushButton:disabled { background-color: #505055; color: #888888; border-color: #44444a; }"
        )
        btn_style_mid = (
            "QPushButton { background-color: #5e5e64; color: #ffffff; font-size: 12px; font-weight: bold; "
            "border-top: 1px solid #55555a; border-bottom: 1px solid #55555a; border-left: none; border-right: none; "
            "border-radius: 0px; padding: 0 12px; } "
            "QPushButton:hover { background-color: #6b6b72; } "
            "QPushButton:pressed { background-color: #4e4e54; }"
        )
        btn_style_right = (
            "QPushButton { background-color: #68686e; color: #ffffff; font-size: 13px; font-weight: bold; "
            "border: 1px solid #55555a; border-left: none; border-top-right-radius: 4px; border-bottom-right-radius: 4px; "
            "border-top-left-radius: 0px; border-bottom-left-radius: 0px; } "
            "QPushButton:hover { background-color: #76767c; } "
            "QPushButton:pressed { background-color: #55555a; } "
            "QPushButton:disabled { background-color: #505055; color: #888888; border-color: #44444a; }"
        )

        self.btn_page_prev = QPushButton("◀")
        self.btn_page_prev.setStyleSheet(btn_style_left)
        self.btn_page_prev.setFixedSize(38, 30)
        self.btn_page_prev.clicked.connect(self.show_prev_page)

        self.btn_page_title = QPushButton(t("page_weapons"))
        self.btn_page_title.setStyleSheet(btn_style_mid)
        self.btn_page_title.setFixedHeight(30)
        self.btn_page_title.clicked.connect(self.toggle_easy_page)

        self.btn_page_next = QPushButton("▶")
        self.btn_page_next.setStyleSheet(btn_style_right)
        self.btn_page_next.setFixedSize(38, 30)
        self.btn_page_next.clicked.connect(self.show_next_page)

        nav_l.addWidget(self.btn_page_prev)
        nav_l.addWidget(self.btn_page_title, 1)
        nav_l.addWidget(self.btn_page_next)

        self.top_header_widget = QWidget()
        self.top_header_widget.setFixedHeight(36)
        top_hdr_layout = QVBoxLayout(self.top_header_widget)
        top_hdr_layout.setContentsMargins(0, 0, 0, 0)
        top_hdr_layout.setSpacing(2)
        top_hdr_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_header_title = QLabel(t("page_weapons_title"))
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        self.lbl_header_title.setFont(title_font)
        self.lbl_header_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_header_desc = QLabel(t("page_weapons_desc"))
        self.lbl_header_desc.setStyleSheet("color: #b0b0b5; font-size: 11px;")
        self.lbl_header_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)

        top_hdr_layout.addWidget(self.lbl_header_title)
        top_hdr_layout.addWidget(self.lbl_header_desc)

        search_input = getattr(self, 'search_input', None) or getattr(self, 'search_edit', None)
        if not search_input:
            for le in self.findChildren(QLineEdit):
                if "Search" in le.placeholderText() or "Recherch" in le.placeholderText():
                    search_input = le
                    break

        lang_label = getattr(self, 'lbl_lang', None) or getattr(self, 'lang_lbl', None)
        if not lang_label:
            for lbl in self.findChildren(QLabel):
                if "Language" in lbl.text() or "Langue" in lbl.text():
                    lang_label = lbl
                    break

        cw = self.centralWidget()
        cw_l = cw.layout() if cw else None

        if cw_l and not getattr(self, '_top_layout_built', False):
            self._top_layout_built = True

            old_top = cw_l.takeAt(0)
            if old_top:
                sub_l = old_top.layout()
                if sub_l:
                    for i in range(sub_l.count() - 1, -1, -1):
                        it = sub_l.takeAt(i)
                        w = it.widget()
                        if w:
                            w.setParent(None)

            top_bar = QWidget()
            top_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            top_bar_l = QHBoxLayout(top_bar)
            top_bar_l.setContentsMargins(0, 2, 0, 4)
            top_bar_l.setSpacing(15)

            self.left_search_lang_box = QWidget()
            self.left_search_lang_box.setFixedWidth(260)
            left_box_l = QVBoxLayout(self.left_search_lang_box)
            left_box_l.setContentsMargins(15, 0, 0, 0)
            left_box_l.setSpacing(6)
            left_box_l.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            if search_input:
                search_input.setFixedWidth(245)
                search_input.setFixedHeight(32)
                left_box_l.addWidget(search_input)

            lang_row_w = QWidget()
            lang_row_w.setFixedWidth(245)
            lang_row_l = QHBoxLayout(lang_row_w)
            lang_row_l.setContentsMargins(0, 0, 0, 0)
            lang_row_l.setSpacing(6)
            if lang_label:
                lang_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
                lang_row_l.addWidget(lang_label)
            if hasattr(self, 'lang_combo'):
                self.lang_combo.setFixedHeight(32)
                self.lang_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                lang_row_l.addWidget(self.lang_combo, 1)
            left_box_l.addWidget(lang_row_w)

            self.center_filter_box = QWidget()
            self.center_filter_box.setFixedWidth(460)
            center_box_l = QVBoxLayout(self.center_filter_box)
            center_box_l.setContentsMargins(0, 0, 15, 0)
            center_box_l.setSpacing(4)
            center_box_l.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

            center_box_l.addWidget(self.top_header_widget, alignment=Qt.AlignmentFlag.AlignCenter)

            self.chk_grid_w = QWidget()
            self.chk_grid_w.setFixedHeight(50)
            chk_grid_l = QGridLayout(self.chk_grid_w)
            chk_grid_l.setContentsMargins(0, 0, 0, 0)
            chk_grid_l.setHorizontalSpacing(16)
            chk_grid_l.setVerticalSpacing(4)

            for chk in [self.chk_hide_filenames, self.chk_hide_notfound, self.chk_hide_coop, self.chk_hide_mission]:
                chk.setMinimumHeight(22)
                chk.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

            chk_grid_l.addWidget(self.chk_hide_filenames, 0, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            chk_grid_l.addWidget(self.chk_hide_notfound, 0, 1, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            chk_grid_l.addWidget(self.chk_hide_coop, 1, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            chk_grid_l.addWidget(self.chk_hide_mission, 1, 1, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            center_box_l.addWidget(self.chk_grid_w, alignment=Qt.AlignmentFlag.AlignCenter)

            if hasattr(self, 'expert_chk_container'):
                self.expert_chk_container.setFixedHeight(60)
                center_box_l.addWidget(self.expert_chk_container, alignment=Qt.AlignmentFlag.AlignCenter)
            if hasattr(self, 'expert_progress_container'):
                center_box_l.addWidget(self.expert_progress_container, alignment=Qt.AlignmentFlag.AlignCenter)

            self.right_controls_box = QWidget()
            self.right_controls_box.setFixedWidth(TOTAL_RIGHT_W)
            right_box_l = QVBoxLayout(self.right_controls_box)
            right_box_l.setContentsMargins(0, 0, 0, 0)
            right_box_l.setSpacing(4)
            right_box_l.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            right_box_l.addWidget(self.nav_container)

            right_btn_w = QWidget()
            right_btn_w.setFixedWidth(TOTAL_RIGHT_W)
            right_btn_grid = QGridLayout(right_btn_w)
            right_btn_grid.setContentsMargins(0, 0, 0, 0)
            right_btn_grid.setHorizontalSpacing(8)
            right_btn_grid.setVerticalSpacing(4)

            self.btn_zero_all.setFixedSize(BUTTON_WIDTH, 34)
            right_btn_grid.addWidget(self.btn_zero_all, 0, 0)

            if hasattr(self, 'btn_preload'):
                self.btn_preload.setFixedSize(BUTTON_WIDTH, 34)
                right_btn_grid.addWidget(self.btn_preload, 0, 0)

            self.btn_mode.setFixedSize(BUTTON_WIDTH, 34)
            right_btn_grid.addWidget(self.btn_mode, 0, 1)

            self.btn_open.setFixedSize(BUTTON_WIDTH, 34)
            right_btn_grid.addWidget(self.btn_open, 1, 0)

            self.btn_save.setFixedSize(BUTTON_WIDTH, 34)
            right_btn_grid.addWidget(self.btn_save, 1, 1)

            if hasattr(self, 'btn_unlock_shop'):
                self.btn_unlock_shop.setFixedSize(BUTTON_WIDTH, 34)
                right_btn_grid.addWidget(self.btn_unlock_shop, 2, 0)

            if hasattr(self, 'version_lbl'):
                if hasattr(self.version_lbl, 'setAlignment'):
                    self.version_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if hasattr(self.version_lbl, 'setStyleSheet'):
                    self.version_lbl.setStyleSheet("color: #dcdde1; font-style: italic; font-size: 11px; padding: 2px 0px;")
                right_btn_grid.addWidget(self.version_lbl, 2, 1)

            right_box_l.addWidget(right_btn_w)

            top_bar_l.addWidget(self.left_search_lang_box, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            top_bar_l.addWidget(self.center_filter_box, 1, Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            top_bar_l.addWidget(self.right_controls_box, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            cw_l.insertWidget(0, top_bar)

        if hasattr(self, 'btn_zero_all'):
            try:
                self.btn_zero_all.clicked.disconnect()
            except Exception:
                pass
            self.btn_zero_all.clicked.connect(self.on_red_button_clicked)

        if cw and cw_l:
            cw_l.setContentsMargins(15, 6, 15, 4)
            cw_l.setSpacing(6)
            for i in range(cw_l.count() - 1, -1, -1):
                it = cw_l.itemAt(i)
                if it and it.spacerItem():
                    taken = cw_l.takeAt(i)
                    del taken

            if hasattr(self, 'splitter'):
                self.splitter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                cw_l.setStretchFactor(self.splitter, 1)

        if hasattr(self, 'splitter'):
            self.splitter.setCollapsible(0, False)
            self.splitter.setCollapsible(1, False)
            self.splitter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.splitter.setMaximumHeight(16777215)
            self.splitter.setMinimumHeight(0)
            for i in range(self.splitter.count()):
                w = self.splitter.widget(i)
                if w:
                    w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                    w.setMaximumHeight(16777215)
                    if w.layout():
                        w.layout().setContentsMargins(0, 0, 0, 0)
                        for j in range(w.layout().count() - 1, -1, -1):
                            it = w.layout().itemAt(j)
                            if it and it.spacerItem():
                                taken = w.layout().takeAt(j)
                                del taken

        if hasattr(self, 'left_frame'):
            self.left_frame.setMinimumWidth(280)

        if hasattr(self, 'count_lbl') and self.count_lbl:
            self.count_lbl.setStyleSheet(
                "QLabel { padding-top: 10px; padding-bottom: 8px; font-size: 11px; color: #dcdde1; }"
            )
            self.count_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if hasattr(self, 'table_w'):
            self.table_w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.table_w.setMaximumHeight(16777215)
            self.table_w.setStyleSheet("QTableWidget::item { padding-left: 6px; }")
            if self.table_w.parentWidget() and self.table_w.parentWidget().layout():
                pl = self.table_w.parentWidget().layout()
                pl.setContentsMargins(0, 0, 0, 0)
                pl.setStretchFactor(self.table_w, 1)
                for i in range(pl.count() - 1, -1, -1):
                    it = pl.itemAt(i)
                    if it and it.spacerItem():
                        taken = pl.takeAt(i)
                        del taken

            self.table_opacity = QGraphicsOpacityEffect(self.table_w)
            self.table_w.setGraphicsEffect(self.table_opacity)
            self.table_fade_anim = QPropertyAnimation(self.table_opacity, b"opacity")
            self.table_fade_anim.setDuration(150)
            self.table_fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        if hasattr(self, 'right_stack'):
            self.right_stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.right_stack.setMaximumHeight(16777215)
            if self.right_stack.parentWidget() and self.right_stack.parentWidget().layout():
                rl = self.right_stack.parentWidget().layout()
                rl.setContentsMargins(0, 0, 0, 0)
                rl.setStretchFactor(self.right_stack, 1)
            for idx in range(self.right_stack.count()):
                rw = self.right_stack.widget(idx)
                if rw:
                    rw.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                    rw.setMaximumHeight(16777215)

        self.badge_container_widget = QWidget()
        self.badge_container_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.badge_container_widget.setMaximumHeight(16777215)
        b_cnt_layout = QVBoxLayout(self.badge_container_widget)
        b_cnt_layout.setContentsMargins(0, 0, 0, 0)
        b_cnt_layout.setSpacing(4)

        self.lbl_badge_count = QLabel("")
        self.lbl_badge_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_badge_count.setStyleSheet(
            "QLabel { color: #dcdde1; font-size: 12px; font-weight: bold; padding: 6px 0px 4px 0px; }"
        )

        self.badge_list_w = QListWidget()
        self.badge_list_w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.badge_list_w.setMaximumHeight(16777215)
        self.badge_list_w.setViewMode(QListWidget.ViewMode.IconMode)
        self.badge_list_w.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.badge_list_w.setMovement(QListWidget.Movement.Static)
        self.badge_list_w.setSpacing(0)
        self.badge_list_w.setUniformItemSizes(True)
        self.badge_list_w.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.badge_list_w.setStyleSheet(
            "QListWidget { background-color: transparent; border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 6px; padding: 2px; } "
            "QListWidget::item { border: none; } "
            "QScrollBar:vertical { width: 10px; background: transparent; } "
            "QScrollBar::handle:vertical { background: #55555a; border-radius: 4px; min-height: 20px; } "
        )
        self.badge_delegate = BadgeCardDelegate(self.badge_list_w)
        self.badge_list_w.setItemDelegate(self.badge_delegate)
        self.badge_list_w.itemChanged.connect(self.on_badge_item_changed)
        self.badge_list_w.currentItemChanged.connect(self.on_badge_selection_changed)
        self.badge_list_w.installEventFilter(self)
        if hasattr(self.badge_list_w, 'viewport') and self.badge_list_w.viewport():
            self.badge_list_w.viewport().installEventFilter(self)

        self.badge_opacity_effect = QGraphicsOpacityEffect(self.badge_list_w)
        self.badge_list_w.setGraphicsEffect(self.badge_opacity_effect)
        self.badge_fade_anim = QPropertyAnimation(self.badge_opacity_effect, b"opacity")
        self.badge_fade_anim.setDuration(160)
        self.badge_fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        b_cnt_layout.addWidget(self.lbl_badge_count)
        b_cnt_layout.addWidget(self.badge_list_w, 1)
        self.right_stack.addWidget(self.badge_container_widget)

        if hasattr(self, 'right_stack'):
            self.right_stack.currentChanged.connect(lambda _: self.update_page_nav_state())
        self.update_page_nav_state()

    def get_badge_icon(self, img_name):
        if not hasattr(self, '_badge_icon_cache'):
            self._badge_icon_cache = {}
            self._badge_pix_cache = {}

        if img_name in self._badge_icon_cache:
            return self._badge_icon_cache[img_name]

        icon_path = os.path.join(CACHE_DIR, img_name)
        img = QImage()
        if os.path.exists(icon_path):
            img.load(icon_path)
        if not img.isNull():
            scaled = img.scaled(76, 76, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            square = QImage(76, 76, QImage.Format.Format_ARGB32_Premultiplied)
            square.fill(Qt.GlobalColor.transparent)
            painter = QPainter(square)
            painter.drawImage((76 - scaled.width()) // 2, (76 - scaled.height()) // 2, scaled)
            painter.end()
            pix = QPixmap.fromImage(square)
            self._badge_pix_cache[img_name] = pix
            icon = QIcon(pix)
            self._badge_icon_cache[img_name] = icon
            return icon
        return QIcon()

    def get_badge_pixmap(self, img_name):
        if not hasattr(self, '_badge_pix_cache'):
            self._badge_pix_cache = {}
        if img_name in self._badge_pix_cache:
            return self._badge_pix_cache[img_name]
        self.get_badge_icon(img_name)
        return self._badge_pix_cache.get(img_name, None)

    def update_badge_count(self):
        if not self.badge_file or self.badge_file not in self.rsdb_data:
            txt = t("count_info_badges", 0, 0)
        else:
            badges = self.rsdb_data[self.badge_file]
            total = len(badges)
            unlocked = sum(1 for b in badges if self.is_badge_unlocked(b))
            txt = t("count_info_badges", total, unlocked)

        if hasattr(self, 'lbl_badge_count') and self.lbl_badge_count:
            self.lbl_badge_count.setText(txt)
        if hasattr(self, 'count_lbl') and self.count_lbl:
            self.count_lbl.setText(txt)

    def populate_badge_grid(self):
        self._populating_badges = True
        self.badge_list_w.blockSignals(True)
        self.badge_list_w.clear()
        self._badge_items_by_image = {}

        if not self.badge_file or self.badge_file not in self.rsdb_data:
            self.update_badge_count()
            self.badge_list_w.blockSignals(False)
            self._populating_badges = False
            return

        badges = self.rsdb_data[self.badge_file]
        displayed = 0

        all_unlocked_ram = (len(badges) > 0 and all(self.is_badge_unlocked(b) for b in badges))
        is_saved_on_disk = self.is_badge_file_saved()

        filter_text = ""
        if hasattr(self, 'search_input') and self.search_input:
            filter_text = self.search_input.text().lower()
        else:
            for le in self.findChildren(QLineEdit):
                if "Search" in le.placeholderText() or "Recherch" in le.placeholderText():
                    filter_text = le.text().lower()
                    break

        for i, badge in enumerate(badges):
            b_name = badge.get("Name", "")
            if not b_name:
                row_id = badge.get("__RowId", "")
                b_name = row_id.replace("Work/Gyml/BadgeInfo_", "").replace(".spl__BadgeInfo.gyml", "")

            title, img_name = self.data_manager.guess_badge_info(badge)
            display_text = title if title else b_name

            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, i)
            item.setData(Qt.ItemDataRole.UserRole + 1, img_name)

            orig_badge = None
            if hasattr(self, 'original_rsdb_data') and self.badge_file in self.original_rsdb_data:
                if i < len(self.original_rsdb_data[self.badge_file]):
                    orig_badge = self.original_rsdb_data[self.badge_file][i]

            is_orig_unlocked = self.is_badge_unlocked(orig_badge) if orig_badge else self.is_badge_unlocked(badge)
            item.setData(Qt.ItemDataRole.UserRole + 3, is_orig_unlocked)

            is_unlocked = self.is_badge_unlocked(badge)

            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            item.setCheckState(Qt.CheckState.Checked if is_unlocked else Qt.CheckState.Unchecked)

            icon = self.get_badge_icon(img_name)
            pix = self.get_badge_pixmap(img_name)
            if not icon.isNull() and pix:
                item.setIcon(icon)
                item.setData(Qt.ItemDataRole.UserRole + 2, pix)
            else:
                item.setIcon(QIcon())
                item.setData(Qt.ItemDataRole.UserRole + 2, None)

            self._badge_items_by_image.setdefault(img_name, []).append(item)

            if filter_text and filter_text not in display_text.lower():
                item.setHidden(True)
            else:
                displayed += 1

            self.badge_list_w.addItem(item)

        self.badge_list_w.blockSignals(False)
        self._populating_badges = False
        self.update_badge_count()
        self.adjust_badge_grid_spacing(animate=False)

        if all_unlocked_ram and is_saved_on_disk and not getattr(self, '_all_unlocked_popup_shown', False):
            self._all_unlocked_popup_shown = True
            QTimer.singleShot(100, lambda: QMessageBox.information(
                self,
                t("all_badges_already_unlocked_title"),
                t("msg_all_badges_already_unlocked")
            ))

    def on_badge_item_changed(self, item):
        if getattr(self, '_populating_badges', False):
            return
        if not self.badge_file or self.badge_file not in self.rsdb_data:
            return

        idx = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(idx, int) or idx < 0 or idx >= len(self.rsdb_data[self.badge_file]):
            return

        badge = self.rsdb_data[self.badge_file][idx]
        check_val = item.checkState()
        is_checked = (check_val in (Qt.CheckState.Checked, 2, Qt.CheckState.Checked.value))

        if is_checked:
            badge["Category"] = byml.String("SpendShop") if hasattr(byml, 'String') else "SpendShop"
            badge["Sub1_Str"] = byml.String("Goods") if hasattr(byml, 'String') else "Goods"
            orig_s1 = badge.get("Sub1_Int", 0)
            t_s1 = type(orig_s1).__name__
            badge["Sub1_Int"] = getattr(byml, t_s1)(0) if hasattr(byml, t_s1) and t_s1 in ['UInt', 'Int', 'Int64', 'UInt64'] else 0
            orig_s2 = badge.get("Sub2_Int", 0)
            t_s2 = type(orig_s2).__name__
            badge["Sub2_Int"] = getattr(byml, t_s2)(0) if hasattr(byml, t_s2) and t_s2 in ['UInt', 'Int', 'Int64', 'UInt64'] else 0
        else:
            if self.badge_file in self.original_rsdb_data and idx < len(self.original_rsdb_data[self.badge_file]):
                orig_badge = self.original_rsdb_data[self.badge_file][idx]
                self.rsdb_data[self.badge_file][idx] = copy.deepcopy(orig_badge)

        self.modified_files.add(self.badge_file)
        self.update_badge_count()
        if hasattr(self, 'update_action_buttons'):
            self.update_action_buttons()

    def _apply_badge_unlock_anim(self, item, user_idx):
        item.setCheckState(Qt.CheckState.Checked)
        if hasattr(self, 'badge_delegate') and isinstance(user_idx, int):
            self.badge_delegate.trigger_check_animation(user_idx)

    def unlock_all_badges(self):
        if not self.badge_file or self.badge_file not in self.rsdb_data:
            return

        if getattr(self, '_unlock_in_cooldown', False):
            return
        self._unlock_in_cooldown = True
        if hasattr(self, 'btn_zero_all'):
            self.btn_zero_all.setEnabled(False)

        def end_cooldown():
            self._unlock_in_cooldown = False
            if hasattr(self, 'btn_zero_all'):
                self.btn_zero_all.setEnabled(self.is_data_loaded())

        QTimer.singleShot(2000, end_cooldown)

        if hasattr(self, 'badge_list_w') and self.badge_list_w:
            self.badge_list_w.clearSelection()
            self.badge_list_w.setCurrentItem(None)

        for badge in self.rsdb_data[self.badge_file]:
            badge["Category"] = byml.String("SpendShop") if hasattr(byml, 'String') else "SpendShop"
            badge["Sub1_Str"] = byml.String("Goods") if hasattr(byml, 'String') else "Goods"
            orig_s1 = badge.get("Sub1_Int", 0)
            t_s1 = type(orig_s1).__name__
            badge["Sub1_Int"] = getattr(byml, t_s1)(0) if hasattr(byml, t_s1) and t_s1 in ['UInt', 'Int', 'Int64', 'UInt64'] else 0
            orig_s2 = badge.get("Sub2_Int", 0)
            t_s2 = type(orig_s2).__name__
            badge["Sub2_Int"] = getattr(byml, t_s2)(0) if hasattr(byml, t_s2) and t_s2 in ['UInt', 'Int', 'Int64', 'UInt64'] else 0

        self.modified_files.add(self.badge_file)

        self._populating_badges = True
        visible_items = []

        if hasattr(self, 'badge_list_w') and self.badge_list_w:
            viewport_rect = self.badge_list_w.viewport().rect()
            self.badge_list_w.setUpdatesEnabled(False)

            for idx in range(self.badge_list_w.count()):
                it = self.badge_list_w.item(idx)
                if it:
                    it.setCheckState(Qt.CheckState.Checked)
                    user_idx = it.data(Qt.ItemDataRole.UserRole)
                    if not it.isHidden() and viewport_rect.intersects(self.badge_list_w.visualItemRect(it)):
                        visible_items.append((it, user_idx))

            self.badge_list_w.setUpdatesEnabled(True)
            self.badge_list_w.viewport().update()

            if hasattr(self, 'badge_fade_anim'):
                self.badge_fade_anim.stop()
                self.badge_opacity_effect.setOpacity(0.4)
                self.badge_fade_anim.setStartValue(0.4)
                self.badge_fade_anim.setEndValue(1.0)
                self.badge_fade_anim.start()

            for rank, (it, user_idx) in enumerate(visible_items):
                delay = min(rank * 18, 350)
                QTimer.singleShot(delay, lambda item=it, u=user_idx: self._apply_badge_unlock_anim(item, u))

        total_anim_time = min(len(visible_items) * 18 + 250, 600) if visible_items else 300

        est_ver = self.get_estimated_version()

        def finalize_unlock():
            self._populating_badges = False
            self.update_badge_count()
            if hasattr(self, 'update_action_buttons'):
                self.update_action_buttons()
            if hasattr(self, 'badge_list_w') and self.badge_list_w and self.badge_list_w.viewport():
                self.badge_list_w.viewport().update()
            QMessageBox.information(self, t("success_title"), t("msg_unlock_all_badges_done", est_ver))

        QTimer.singleShot(total_anim_time, finalize_unlock)

    def adjust_badge_grid_spacing(self, animate=False):
        if not hasattr(self, 'badge_list_w') or not self.badge_list_w:
            return
        viewport = self.badge_list_w.viewport()
        if not viewport:
            return

        viewport_w = viewport.width() - 4
        if viewport_w <= 100:
            return

        min_card_w = 150
        cols = max(1, viewport_w // min_card_w)
        target_w = max(min_card_w, viewport_w // cols)

        cur_w = self.badge_list_w.gridSize().width()
        if cur_w != target_w:
            self.badge_list_w.setGridSize(QSize(target_w, 148))
            self.badge_list_w.doItemsLayout()