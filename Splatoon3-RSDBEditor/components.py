import os
import re
import json
import requests
import concurrent.futures
import zipfile
import io
import shutil

from PyQt6.QtGui import QImage, QIcon, QTextOption
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QCheckBox

from translations import t
from utils import CACHE_DIR, log

class CacheBuilderWorker(QThread):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal()

    def __init__(self, missing_images, get_urls_callback):
        super().__init__()
        self.missing_images = missing_images
        self.get_urls_callback = get_urls_callback

    def download_image(self, img_filename):
        local_path = os.path.join(CACHE_DIR, img_filename)
        urls_to_try = self.get_urls_callback(img_filename)
            
        for url in urls_to_try:
            try:
                resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
                if resp.status_code == 200:
                    image = QImage()
                    image.loadFromData(resp.content)
                    if not image.isNull():
                        with open(local_path, "wb") as f: f.write(resp.content)
                        return
            except Exception: pass

    def run(self):
        missing_list = list(self.missing_images)
        total, completed = len(missing_list), 0

        if total > 0:
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = {executor.submit(self.download_image, img): img for img in missing_list}
                for future in concurrent.futures.as_completed(futures):
                    completed += 1
                    self.progress.emit(completed, total)

        self.finished.emit()

class ImageDownloadWorker(QThread):
    finished = pyqtSignal(QImage)

    def __init__(self, urls):
        super().__init__()
        self.urls = urls if isinstance(urls, list) else [urls]

    def run(self):
        for url in self.urls:
            try:
                resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
                if resp.status_code == 200:
                    image = QImage()
                    image.loadFromData(resp.content)
                    if not image.isNull():
                        self.finished.emit(image)
                        return
            except Exception:
                continue
                
        dummy_path = os.path.join(CACHE_DIR, "Dummy.png")
        if os.path.exists(dummy_path):
            self.finished.emit(QImage(dummy_path))
        else:
            self.finished.emit(QImage())

class ComboIconWorker(QThread):
    finished = pyqtSignal(int, QIcon)

    def __init__(self, index, urls, cache_path):
        super().__init__()
        self.index = index
        self.urls = urls if isinstance(urls, list) else [urls]
        self.cache_path = cache_path

    def run(self):
        try:
            if os.path.exists(self.cache_path):
                icon = QIcon(self.cache_path)
                if not icon.isNull():
                    self.finished.emit(self.index, icon)
                    return
                
            for url in self.urls:
                try:
                    resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
                    if resp.status_code == 200:
                        image = QImage()
                        image.loadFromData(resp.content)
                        if not image.isNull():
                            image.save(self.cache_path)
                            self.finished.emit(self.index, QIcon(self.cache_path))
                            return
                except Exception:
                    continue
            
            dummy_path = os.path.join(CACHE_DIR, "Dummy.png")
            if os.path.exists(dummy_path):
                self.finished.emit(self.index, QIcon(dummy_path))
            else:
                self.finished.emit(self.index, QIcon())
            
        except Exception:
            self.finished.emit(self.index, QIcon())

class WECheckWorker(QThread):
    finished = pyqtSignal(bool, str, str, str, str)
    
    def __init__(self):
        super().__init__()
        
    def find_weapons_editor(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        paths_to_check = [
            os.path.abspath(os.path.join(current_dir, "..", "main.py")), 
            os.path.abspath(os.path.join(current_dir, "..", "Splatoon3WeaponsEditor", "main.py")),
            os.path.abspath(os.path.join(current_dir, "..", "Splatoon3WeaponsEditor", "Splatoon3-WeaponsEditor", "main.py")),
            os.path.abspath(os.path.join(current_dir, "Splatoon3WeaponsEditor", "main.py")),
            os.path.abspath(os.path.join(current_dir, "Splatoon3WeaponsEditor", "Splatoon3-WeaponsEditor", "main.py")),
            os.path.abspath(os.path.join(current_dir, "..", "Splatoon3-WeaponsEditor", "main.py")),
            os.path.abspath(os.path.join(current_dir, "..", "Splatoon3-WeaponsEditor", "Splatoon3-WeaponsEditor", "main.py"))
        ]
        
        for p in paths_to_check:
            if os.path.exists(p):
                try:
                    with open(p, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if "Splatoon 3 Weapons Editor" in content or "SplatoonPackManager" in content:
                            return p
                except Exception:
                    pass
        return None

    def run(self):
        local_version = "0.0.0"
        we_main_path = self.find_weapons_editor()
        exists = we_main_path is not None
        
        if exists:
            try:
                with open(we_main_path, 'r', encoding='utf-8') as f:
                    match = re.search(r'APP_VERSION\s*=\s*["\']([^"\']+)["\']', f.read())
                    if match:
                        local_version = match.group(1)
            except Exception:
                pass
        else:
            we_main_path = ""
        
        remote_version = "0.0.0"
        download_url = ""
        try:
            resp = requests.get("https://api.github.com/repos/JeremKOYTB/Splatoon3-WeaponsEditor/releases/latest", headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                remote_version = data.get("tag_name", "0.0.0").replace("v", "")
                
                for asset in data.get("assets", []):
                    if asset["name"].endswith(".zip"):
                        download_url = asset["browser_download_url"]
                        break
                if not download_url:
                    download_url = data.get("zipball_url")
        except Exception:
            pass
            
        self.finished.emit(exists, local_version, remote_version, download_url, we_main_path)

class WEDownloadWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str, str)
    
    def __init__(self, url):
        super().__init__()
        self.url = url
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.target_dir = os.path.abspath(os.path.join(self.current_dir, "..", "Splatoon3WeaponsEditor"))
        
    def run(self):
        try:
            self.progress.emit(t("we_downloading"))
            resp = requests.get(self.url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
            resp.raise_for_status()
            zip_data = resp.content
                
            self.progress.emit(t("we_extracting"))
            with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
                root_items = set()
                for item in z.namelist():
                    if not item: continue
                    root_items.add(item.split('/')[0])
                    
                if len(root_items) == 1:
                    root_dir = list(root_items)[0]
                    temp_dir = self.target_dir + "_temp"
                    z.extractall(temp_dir)
                    if os.path.exists(self.target_dir):
                        shutil.rmtree(self.target_dir)
                    shutil.move(os.path.join(temp_dir, root_dir), self.target_dir)
                    shutil.rmtree(temp_dir)
                else:
                    if os.path.exists(self.target_dir):
                        shutil.rmtree(self.target_dir)
                    z.extractall(self.target_dir)

            paths_to_check = [
                os.path.join(self.target_dir, "main.py"),
                os.path.join(self.target_dir, "Splatoon3-WeaponsEditor", "main.py")
            ]

            main_path = ""
            for p in paths_to_check:
                if os.path.exists(p):
                    main_path = p
                    break

            self.finished.emit(True, "", main_path)
        except Exception as e:
            self.finished.emit(False, str(e), "")

class UpdateCheckWorker(QThread):
    finished = pyqtSignal(int, str, str)

    def __init__(self, current_version):
        super().__init__()
        self.current_version = current_version

    def run(self):
        url = "https://api.github.com/repos/JeremKOYTB/Splatoon3-RSDBEditor/releases/latest"
        try:
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            latest_version = data.get("tag_name", "").replace("v", "")
            changelog = data.get("body", "No changelog provided.")
            
            from packaging import version
            v_latest = version.parse(latest_version)
            v_current = version.parse(self.current_version)
            
            if v_latest > v_current: self.finished.emit(1, latest_version, changelog)
            elif v_latest < v_current: self.finished.emit(2, latest_version, changelog)
            else: self.finished.emit(0, latest_version, "")
        except Exception as e:
            log(f"[NET] Update check failed: {e}")
            self.finished.emit(-1, "", str(e))

class UpdatePromptDialog(QDialog):
    def __init__(self, current_version, new_version, changelog, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("update_title"))
        self.resize(600, 450)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        layout = QVBoxLayout(self)
        
        lbl_info = QLabel(t("update_msg", current_version, new_version))
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet("font-size: 11pt;")
        layout.addWidget(lbl_info)
        
        self.browser = QTextEdit()
        self.browser.setReadOnly(True)
        self.browser.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.browser.setMarkdown(re.sub(r'(?<!\n)\n(?!\n)', '\n\n', changelog.replace("\r\n", "\n")))
        self.browser.setStyleSheet("""
            QTextEdit { background-color: #1E1E24; color: #E8E8E8; border: 1px solid #4A4A55; border-radius: 8px; padding: 10px; font-family: "Segoe UI", sans-serif; }
        """)
        layout.addWidget(self.browser)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_no = QPushButton(t("btn_update_later"))
        btn_no.setStyleSheet("QPushButton { background-color: #34495e; color: white; padding: 8px 16px; border-radius: 4px; border: none; } QPushButton:hover { background-color: #2c3e50; }")
        btn_no.clicked.connect(self.reject)
        
        btn_yes = QPushButton(t("btn_update_now"))
        btn_yes.setStyleSheet("QPushButton { background-color: #27ae60; color: white; font-weight: bold; padding: 8px 16px; border-radius: 4px; border: none; } QPushButton:hover { background-color: #2ecc71; }")
        btn_yes.clicked.connect(self.accept)
        
        btn_layout.addWidget(btn_no)
        btn_layout.addWidget(btn_yes)
        layout.addLayout(btn_layout)

class OnlineWarningDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("warn_online_title"))
        self.setFixedWidth(550)
        
        layout = QVBoxLayout(self)
        layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetFixedSize)
        
        self.lbl = QLabel(t("warn_online_msg"))
        self.lbl.setWordWrap(True)
        self.lbl.setStyleSheet("font-size: 11pt;")
        layout.addWidget(self.lbl)
        
        self.chk_confirm = QCheckBox(t("chk_online_confirm"))
        layout.addWidget(self.chk_confirm)
        
        btn_layout = QHBoxLayout()
        self.btn_yes = QPushButton(t("btn_continue"))
        self.btn_yes.clicked.connect(self.accept)
        
        btn_no = QPushButton(t("diff_btn_close"))
        btn_no.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_no)
        btn_layout.addWidget(self.btn_yes)
        layout.addLayout(btn_layout)