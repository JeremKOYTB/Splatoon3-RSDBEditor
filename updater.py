import os
import sys
import json
import re
import zipfile
import urllib.request
import urllib.error
import subprocess
import importlib.util
import signal
import colorsys
import shutil
import time
import ssl

ssl._create_default_https_context = ssl._create_unverified_context

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

if "--install-dir" in sys.argv:
    try:
        idx = sys.argv.index("--install-dir")
        install_dir_path = sys.argv[idx + 1]
        sys.path.insert(0, os.path.abspath(install_dir_path))
    except IndexError:
        pass

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QFrame, 
                             QMessageBox, QComboBox, QCheckBox, QSizePolicy,
                             QGraphicsOpacityEffect, QTextEdit)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QByteArray, QPropertyAnimation, QAbstractAnimation, QDir
from PyQt6.QtGui import QIcon, QPixmap, QTextOption

def ensure_dependencies():
    if importlib.util.find_spec("darkdetect") is None:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "darkdetect"], 
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            sys.exit(1)

ensure_dependencies()
import darkdetect

def get_current_app_version():
    base_dirs = [os.getcwd()]
    if "--install-dir" in sys.argv:
        try:
            idx = sys.argv.index("--install-dir")
            base_dirs.insert(0, sys.argv[idx + 1])
        except IndexError:
            pass

    for base_dir in base_dirs:
        for sub_path in ["main.py", os.path.join("Splatoon3-RSDBEditor", "main.py")]:
            main_py_path = os.path.join(base_dir, sub_path)
            if os.path.exists(main_py_path):
                try:
                    with open(main_py_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        match = re.search(r'APP_VERSION\s*=\s*["\']([^"\']+)["\']', content)
                        if match:
                            return match.group(1)
                except Exception:
                    pass
    return "1.0.0"

APP_VERSION = get_current_app_version()

BASE_FONT = "\"Segoe UI Variable\", \"Segoe UI\", \"Roboto\", sans-serif"

S3RE_MAIN_LOGO = b"""<?xml version="1.0" standalone="no"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 20010904//EN"
 "http://www.w3.org/TR/2001/REC-SVG-20010904/DTD/svg10.dtd">
<svg version="1.0" xmlns="http://www.w3.org/2000/svg"
 width="2000.000000pt" height="1889.000000pt" viewBox="0 0 2000.000000 1889.000000"
 preserveAspectRatio="xMidYMid meet">
<g transform="translate(0.000000,1889.000000) scale(0.100000,-0.100000)" fill="#000000" stroke="none">
<path d="M8945 18829 c-902 -60 -2016 -271 -3185 -604 -899 -256 -1735 -648
-2610 -1223 -524 -344 -1129 -810 -1434 -1103 -799 -767 -1344 -1921 -1616
-3419 -64 -354 -74 -470 -75 -850 0 -358 7 -460 55 -800 101 -707 333 -1492
690 -2329 148 -349 261 -561 445 -841 265 -404 572 -768 1006 -1195 455 -446
975 -880 1557 -1298 106 -76 149 -114 211 -189 103 -123 349 -361 486 -471
208 -166 455 -333 688 -463 53 -30 97 -59 97 -64 0 -25 -47 -154 -76 -210 -84
-161 -224 -265 -429 -321 -118 -32 -376 -32 -524 0 -627 137 -1167 611 -1375
1208 -33 97 -77 279 -91 375 -5 36 -22 69 -71 140 -190 270 -374 375 -690 394
-103 6 -115 5 -158 -16 -40 -19 -54 -35 -101 -114 -29 -51 -94 -173 -143 -273
-485 -984 -552 -1923 -197 -2753 148 -346 408 -707 700 -972 533 -484 1218
-790 1922 -859 152 -15 506 -6 633 16 300 51 557 150 772 297 115 78 295 255
373 367 181 260 295 627 295 953 0 66 3 88 13 88 26 0 138 -76 196 -133 180
-175 241 -401 158 -580 -58 -127 -164 -218 -357 -309 -226 -107 -248 -119
-298 -167 -117 -112 -140 -254 -65 -408 35 -73 170 -211 270 -277 308 -202
751 -345 1263 -408 137 -17 613 -17 740 0 654 88 1129 304 1544 702 146 139
320 363 416 534 39 68 28 75 116 -68 111 -180 272 -373 432 -519 379 -347 868
-564 1447 -643 181 -25 635 -25 820 -1 394 53 704 139 994 278 294 141 458
283 520 452 42 114 20 237 -58 327 -55 64 -97 91 -258 164 -238 107 -361 207
-426 343 -29 62 -32 77 -32 163 0 149 54 275 172 401 49 52 184 149 209 149
10 0 14 -14 14 -53 0 -86 20 -264 41 -372 131 -659 609 -1121 1303 -1260 201
-40 310 -48 556 -42 294 7 479 37 775 122 901 262 1654 891 2010 1682 342 759
315 1655 -77 2563 -60 137 -227 468 -271 536 -58 89 -125 107 -317 84 -194
-24 -342 -92 -465 -215 -44 -44 -109 -122 -144 -173 -59 -88 -64 -98 -81 -196
-39 -216 -85 -357 -175 -536 -250 -497 -740 -874 -1288 -992 -146 -31 -386
-31 -509 0 -246 61 -425 226 -492 455 l-14 48 60 37 c75 46 276 190 343 246
28 23 120 94 205 158 202 151 378 305 520 458 187 200 196 209 410 362 554
399 1064 825 1504 1258 438 432 739 788 1001 1185 184 279 301 500 445 840
390 919 621 1731 715 2505 11 95 15 240 15 620 0 536 -2 558 -66 905 -189
1024 -523 1917 -978 2610 -336 511 -672 849 -1376 1381 -1096 830 -2179 1390
-3297 1708 -960 273 -1947 478 -2698 561 -441 49 -420 48 -1490 50 -561 2
-1078 -1 -1150 -6z m2050 -329 c88 -5 192 -12 230 -15 l70 -6 -64 -67 c-121
-127 -210 -286 -247 -438 -25 -100 -23 -277 4 -375 153 -565 868 -959 1741
-959 199 0 336 13 524 51 719 143 1197 545 1243 1047 4 40 8 72 9 72 10 0 340
-121 347 -128 4 -4 4 -46 0 -92 -35 -351 140 -668 453 -825 133 -66 239 -88
395 -82 70 2 152 12 185 21 131 36 282 125 375 220 24 25 48 46 52 46 26 0
606 -381 842 -553 147 -107 396 -297 396 -303 0 -2 -23 -32 -51 -66 -224 -277
-224 -660 2 -935 152 -187 417 -289 654 -253 146 22 292 89 387 178 l47 44 31
-44 c60 -82 180 -276 262 -424 336 -607 600 -1413 747 -2279 110 -648 66
-1357 -135 -2160 -170 -678 -515 -1595 -772 -2050 -401 -712 -1085 -1456
-2044 -2223 -131 -106 -575 -442 -583 -442 -2 0 4 19 14 43 64 148 147 452
180 652 46 284 52 656 16 924 -184 1348 -1189 2421 -2515 2685 -202 40 -374
56 -615 56 -502 0 -926 -95 -1363 -305 -343 -166 -588 -340 -863 -614 -224
-224 -388 -439 -538 -707 -128 -230 -251 -548 -309 -804 -18 -78 -31 -117 -35
-105 -3 11 -17 68 -31 126 -97 410 -281 800 -547 1154 -528 705 -1329 1157
-2208 1245 -133 13 -489 13 -622 0 -881 -87 -1680 -538 -2213 -1247 -347 -462
-550 -977 -617 -1568 -16 -142 -17 -508 -1 -650 36 -317 120 -643 236 -913
l35 -82 -62 42 c-101 69 -581 432 -722 547 -376 306 -578 485 -874 776 -634
624 -1046 1188 -1314 1800 -424 970 -671 1838 -753 2655 -21 204 -24 682 -5
850 37 339 147 882 256 1260 149 520 355 1020 583 1418 104 181 222 357 231
346 258 -295 499 -442 841 -515 148 -32 390 -31 540 0 580 122 1001 547 1117
1127 26 133 24 395 -5 531 -52 239 -145 434 -300 626 -30 37 -53 69 -51 71 35
30 592 346 611 346 4 0 8 -6 8 -14 0 -8 22 -58 50 -113 174 -345 494 -569 880
-614 428 -49 854 166 1083 546 148 247 191 582 111 861 -14 49 -28 98 -31 109
-4 18 9 24 149 58 254 64 641 153 848 196 207 42 642 121 669 121 9 0 -8 -14
-37 -31 -68 -38 -192 -156 -247 -234 -191 -270 -219 -615 -72 -910 117 -237
352 -417 614 -471 96 -20 317 -14 408 11 94 26 236 99 319 165 143 113 259
293 307 475 30 113 30 317 0 430 -56 213 -191 403 -366 519 -65 44 -180 98
-245 117 l-45 13 130 13 c72 7 195 16 275 21 201 13 1800 14 1995 2z m-3600
-10175 c588 -90 1111 -454 1400 -975 492 -887 217 -2005 -630 -2563 -241 -159
-519 -262 -813 -303 -147 -20 -447 -15 -581 10 -422 79 -785 274 -1077 578
-625 653 -711 1661 -205 2414 310 462 823 782 1351 843 52 6 109 13 125 15 58
8 331 -4 430 -19z m6029 0 c574 -88 1084 -434 1380 -937 328 -558 353 -1248
67 -1833 -287 -585 -837 -981 -1489 -1071 -147 -20 -447 -15 -581 10 -328 61
-628 196 -876 394 -911 727 -985 2075 -160 2897 296 295 709 498 1105 544 52
6 109 13 125 15 58 8 331 -4 429 -19z m-3273 -2565 c63 -215 181 -483 300
-686 408 -693 1068 -1210 1831 -1433 316 -92 547 -124 893 -124 475 0 809 69
1292 270 7 3 16 -3 19 -13 109 -314 347 -542 659 -632 145 -42 186 -47 390
-47 235 0 344 18 565 91 572 190 1064 627 1316 1171 62 134 127 333 157 481
25 121 26 125 84 200 73 94 154 152 246 175 126 32 111 44 220 -175 288 -583
410 -1078 394 -1607 -7 -244 -35 -422 -97 -626 -212 -693 -723 -1263 -1445
-1611 -852 -411 -1784 -388 -2291 57 -197 174 -326 402 -384 684 -28 132 -42
329 -34 466 8 136 -1 174 -51 218 -47 41 -104 55 -190 46 -104 -9 -180 -31
-282 -80 -254 -123 -459 -377 -524 -651 -30 -126 -24 -295 15 -409 38 -112 96
-205 188 -301 119 -124 257 -211 480 -304 102 -42 106 -47 66 -99 -118 -150
-495 -325 -885 -410 -608 -131 -1195 -95 -1693 104 -270 108 -472 239 -679
440 -218 212 -380 448 -506 736 -25 57 -58 116 -72 131 -52 54 -138 61 -208
18 -27 -17 -44 -41 -72 -103 -179 -394 -371 -660 -631 -878 -375 -312 -816
-478 -1382 -520 -561 -41 -1250 112 -1626 359 -83 55 -174 139 -174 161 0 16
51 45 158 90 501 211 731 599 607 1025 -81 280 -311 537 -570 637 -181 70
-347 75 -417 12 -45 -41 -49 -62 -52 -311 -3 -259 -14 -344 -66 -514 -183
-591 -742 -924 -1505 -895 -1089 42 -2134 754 -2515 1713 -245 616 -219 1322
77 2079 66 170 240 524 261 532 23 9 128 -14 187 -41 65 -30 133 -91 191 -172
38 -53 46 -74 64 -167 157 -813 803 -1494 1614 -1702 176 -45 306 -59 490 -52
207 8 340 39 501 118 226 111 412 328 484 564 7 22 14 46 17 53 3 9 17 6 54
-13 79 -40 254 -110 375 -149 787 -254 1625 -193 2370 174 486 240 912 610
1214 1055 238 350 373 671 486 1150 6 25 11 14 31 -75 13 -58 38 -152 55 -210z"/>
<path d="M10878 16420 c-206 -33 -370 -114 -506 -251 -184 -185 -273 -419
-259 -677 22 -385 273 -694 654 -804 114 -33 343 -33 458 0 307 89 546 331
626 637 31 115 31 308 1 427 -66 266 -261 498 -504 600 -146 62 -337 89 -470
68z"/>
<path d="M6387 15870 c-956 -151 -1545 -1102 -1246 -2015 169 -515 617 -915
1147 -1026 765 -160 1523 272 1781 1014 61 174 75 270 75 497 0 226 -13 310
-74 493 -150 446 -517 816 -960 967 -163 55 -265 72 -470 75 -107 2 -221 0
-253 -5z"/>
<path d="M14275 15489 c-466 -36 -885 -329 -1089 -760 -167 -352 -167 -776 0
-1128 181 -383 525 -653 944 -742 148 -31 372 -31 520 0 276 58 511 189 703
391 596 626 445 1640 -308 2073 -147 85 -347 149 -501 162 -138 11 -171 12
-269 4z"/>
<path d="M8992 13965 c-104 -23 -207 -80 -288 -160 -132 -131 -191 -284 -181
-470 9 -166 61 -281 182 -401 117 -116 255 -174 417 -174 115 0 176 14 278 62
119 57 221 159 278 278 48 101 62 163 62 273 0 165 -63 312 -184 432 -148 146
-356 205 -564 160z"/>
<path d="M17230 13469 c-282 -32 -556 -190 -727 -417 -282 -374 -296 -862 -37
-1259 49 -76 213 -238 289 -288 380 -248 846 -246 1217 6 80 55 188 158 249
238 63 83 151 262 178 361 102 378 -6 781 -283 1055 -175 173 -393 277 -639
304 -107 12 -139 12 -247 0z"/>
<path d="M3266 13384 c-274 -66 -495 -378 -556 -784 -6 -41 -11 -138 -11 -215
0 -157 11 -248 47 -381 117 -440 427 -695 752 -619 363 86 613 570 572 1110
-45 590 -403 986 -804 889z"/>
<path d="M6916 7255 c-156 -30 -272 -92 -391 -210 -116 -115 -177 -228 -209
-387 -65 -317 91 -642 384 -801 187 -102 429 -115 630 -34 150 61 291 183 369
322 70 122 94 215 95 365 1 152 -10 202 -76 340 -44 92 -61 115 -142 195 -69
69 -110 101 -173 133 -149 77 -332 106 -487 77z"/>
<path d="M13054 7255 c-152 -27 -271 -86 -379 -187 -173 -162 -255 -362 -242
-593 22 -414 369 -723 787 -702 588 29 911 702 566 1180 -116 162 -284 267
-481 302 -103 18 -155 18 -251 0z"/>
</g>
</svg>"""

def get_app_icon():
    svg_data = S3RE_MAIN_LOGO
    if darkdetect.isDark():
        svg_data = svg_data.replace(b'fill="#000000"', b'fill="#FFFFFF"')
    pix = QPixmap()
    pix.loadFromData(QByteArray(svg_data))
    return QIcon(pix)

THEMES = {
    "dark": {
        "bg": "#3C3C44", "bg_input": "#32323A", "text": "#E8E8E8", "text_title": "#FFFFFF", 
        "text_dim": "#B0B0B8", "card": "#4A4A54", "border": "#555560", "border_hover": "#626270",
        "btn_text": "#2B2B30", "warn": "#EF5350"
    },
    "light": {
        "bg": "#F0F0F5", "bg_input": "#F9F9FB", "text": "#1D1D1F", "text_title": "#000000", 
        "text_dim": "#8E8E93", "card": "#FFFFFF", "border": "#D1D1D6", "border_hover": "#E5E5EA",
        "btn_text": "#1D1D1F", "warn": "#EF5350"
    },
    "oled": {
        "bg": "#000000", "bg_input": "#121212", "text": "#E8E8E8", "text_title": "#FFFFFF", 
        "text_dim": "#888888", "card": "#0A0A0A", "border": "#333333", "border_hover": "#555555",
        "btn_text": "#000000", "warn": "#EF5350"
    }
}

def load_editor_config():
    base_dirs = [os.getcwd()]
    if "--install-dir" in sys.argv:
        try:
            idx = sys.argv.index("--install-dir")
            base_dirs.insert(0, sys.argv[idx + 1])
        except IndexError:
            pass

    cfg = {
        "theme": "dark",
        "accent_color": "#E6FF00", 
        "rainbow_mode": False,
        "rainbow_speed": 2
    }
    
    for base_dir in base_dirs:
        for sub_path in ["splatoon_RSDBeditor_config.json", os.path.join("Splatoon3-RSDBEditor", "splatoon_RSDBeditor_config.json")]:
            config_path = os.path.join(base_dir, sub_path)
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        for k in cfg:
                            if k in data:
                                cfg[k] = data[k]
                    return cfg
                except Exception:
                    pass
    return cfg

def get_stylesheet(theme_name, accent_color):
    c = THEMES.get(theme_name, THEMES["dark"])
    return f"""
    QMainWindow, QDialog, QMessageBox {{ background-color: {c['bg']}; color: {c['text']}; }}
    QWidget {{ font-family: {BASE_FONT}; font-size: 10pt; }}
    QLabel {{ color: {c['text']}; }}
    QFrame#Card {{ background-color: {c['card']}; border-radius: 8px; border: 1px solid {c['border']}; }}
    QLabel#CardTitle {{ color: {c['text_title']}; font-size: 13pt; font-weight: 700; }}
    QLabel#CardVersion {{ color: {c['text_dim']}; font-size: 9pt; font-weight: 500; }}
    QComboBox {{ background-color: {c['bg_input']}; border: 1px solid {c['border']}; border-radius: 6px; padding: 6px; color: {c['text']}; min-height: 28px; outline: none; }}
    QCheckBox {{ color: {c['text']}; outline: none; }}
    QPushButton {{ background-color: {c['border']}; color: {c['text']}; border-radius: 6px; padding: 6px 14px; font-weight: 600; border: 1px solid {c['border_hover']}; min-height: 20px; outline: none; }}
    QPushButton:hover {{ background-color: {c['border_hover']}; }}
    QPushButton:pressed {{ background-color: {accent_color}; color: {c['btn_text']}; border: 1px solid {accent_color}; }}
    #btnExecute {{ background-color: {accent_color}; color: {c['btn_text']}; font-size: 11pt; font-weight: bold; padding: 10px 24px; border-radius: 6px; border: none; min-width: 200px; }}
    #btnExecute:hover {{ opacity: 0.8; color: {c['btn_text']}; }}
    """

class ReleasesFetchThread(QThread):
    finished = pyqtSignal(list, str)

    def run(self):
        url = f"https://api.github.com/repos/JeremKOYTB/Splatoon3-RSDBEditor/releases?t={int(time.time())}"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Splatoon3RSDBEditor-Updater'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
            self.finished.emit(data, "")
        except Exception as e:
            self.finished.emit([], str(e))

class DownloadWorkerThread(QThread):
    progress = pyqtSignal(str)
    completed = pyqtSignal(bool, str)

    def __init__(self, download_url, install_dir, target_version):
        super().__init__()
        self.download_url = download_url
        self.install_dir = os.path.abspath(install_dir)
        self.target_version = target_version
        self.is_7z = download_url.lower().endswith(".7z")

    def run(self):
        temp_archive_path = os.path.join(self.install_dir, "S3E_Update_Temp." + ("7z" if self.is_7z else "zip"))
        temp_extract_dir = os.path.join(self.install_dir, "S3E_Extract_Temp")
        
        try:
            if self.is_7z:
                self.progress.emit("Loading 7z extraction modules...")
                if importlib.util.find_spec("py7zr") is None:
                    try:
                        subprocess.check_call([sys.executable, "-m", "pip", "install", "py7zr"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except subprocess.CalledProcessError:
                        raise Exception("Failed to install py7zr required for 7z extraction.")
            
            self.progress.emit("Downloading archive...")
            req = urllib.request.Request(self.download_url, headers={'User-Agent': 'Splatoon3RSDBEditor-Updater'})
            with urllib.request.urlopen(req, timeout=30) as response, open(temp_archive_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)

            self.progress.emit("Extracting files...")
            os.makedirs(temp_extract_dir, exist_ok=True)
            
            if self.is_7z:
                import py7zr
                with py7zr.SevenZipFile(temp_archive_path, mode='r') as z:
                    z.extractall(path=temp_extract_dir)
            else:
                with zipfile.ZipFile(temp_archive_path, 'r') as z:
                    z.extractall(temp_extract_dir)

            self.progress.emit("Analyzing architecture...")
            base_target = temp_extract_dir
            contents = os.listdir(temp_extract_dir)
            if len(contents) == 1:
                possible_dir = os.path.join(temp_extract_dir, contents[0])
                if os.path.isdir(possible_dir):
                    base_target = possible_dir

            main_script_target = os.path.join(base_target, "Splatoon3-RSDBEditor", "main.py")
            if not os.path.exists(main_script_target):
                raise Exception("Security: The vital file 'main.py' is missing from the downloaded archive.")

            self.progress.emit("Cleaning up old files...")
            extracted_files = set()
            for root, dirs, files in os.walk(base_target):
                if self.target_version.lower() == "main":
                    for d in list(dirs):
                        if d.lower() == "cache":
                            dirs.remove(d)

                for f in files:
                    rel_path = os.path.relpath(os.path.join(root, f), base_target)
                    extracted_files.add(os.path.normcase(os.path.abspath(os.path.join(self.install_dir, rel_path))))

            protected_paths = [
                os.path.normcase(os.path.abspath(os.path.join(self.install_dir, "Splatoon3-RSDBEditor", "cache"))),
                os.path.normcase(os.path.abspath(os.path.join(self.install_dir, "Splatoon3-RSDBEditor", "splatoon_RSDBeditor_config.json"))),
                os.path.normcase(os.path.abspath(os.path.join(self.install_dir, "cache"))),
                os.path.normcase(os.path.abspath(os.path.join(self.install_dir, "splatoon_RSDBeditor_config.json")))
            ]

            for root_dir, dirs, files in os.walk(self.install_dir, topdown=False):
                rel_root = os.path.relpath(root_dir, self.install_dir)
                if rel_root == "." or rel_root.startswith("Splatoon3-RSDBEditor"):
                    
                    is_dir_protected = False
                    for p in protected_paths:
                        if os.path.normcase(os.path.abspath(root_dir)).startswith(p):
                            is_dir_protected = True
                            break
                    if is_dir_protected:
                        continue

                    for f in files:
                        file_path = os.path.abspath(os.path.join(root_dir, f))
                        file_norm = os.path.normcase(file_path)
                        
                        is_file_protected = False
                        for p in protected_paths:
                            if file_norm == p or file_norm.startswith(p):
                                is_file_protected = True
                                break
                        if is_file_protected:
                            continue
                            
                        if rel_root == ".":
                            if f.lower() not in ["start.bat", "updater.py"]:
                                continue
                        
                        if file_norm not in extracted_files:
                            try:
                                os.remove(file_path)
                            except Exception:
                                pass
                    try:
                        if not os.listdir(root_dir) and rel_root != ".":
                            os.rmdir(root_dir)
                    except Exception:
                        pass

            self.progress.emit("Installing new files...")
            for root, dirs, files in os.walk(base_target):
                if self.target_version.lower() == "main":
                    for d in list(dirs):
                        if d.lower() == "cache":
                            dirs.remove(d)

                for f in files:
                    src_file = os.path.join(root, f)
                    rel_path = os.path.relpath(src_file, base_target)
                    dst_file = os.path.abspath(os.path.join(self.install_dir, rel_path))
                    dst_norm = os.path.normcase(dst_file)
                    
                    is_protected = False
                    for p in protected_paths:
                        if dst_norm == p or dst_norm.startswith(p):
                            if os.path.exists(dst_file):
                                is_protected = True
                            break
                            
                    if is_protected:
                        continue
                        
                    os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                    shutil.copy2(src_file, dst_file)

            self.completed.emit(True, "Update installed successfully.")
        except Exception as e:
            self.completed.emit(False, str(e))
        finally:
            if os.path.exists(temp_extract_dir):
                shutil.rmtree(temp_extract_dir, ignore_errors=True)
            if os.path.exists(temp_archive_path):
                try:
                    os.remove(temp_archive_path)
                except Exception:
                    pass

class UpdaterWindow(QMainWindow):
    def __init__(self, current_version):
        super().__init__()
        self.current_version = current_version
        self.is_dev_version = False
        self.first_stable_idx = -1
        
        self.install_dir = os.getcwd()
        if "--install-dir" in sys.argv:
            try:
                idx = sys.argv.index("--install-dir")
                self.install_dir = sys.argv[idx + 1]
            except IndexError:
                pass
                
        self.setWindowTitle("Splatoon 3 RSDB Editor (Updater)")
        
        self.last_is_dark = darkdetect.isDark()
        self.setWindowIcon(get_app_icon())
        
        self.releases_data = []
        self.cached_releases = []
        
        self.force_reinstall_mode = "--reinstall" in sys.argv
        self.force_prerelease_mode = "--prerelease" in sys.argv
        self.force_view_all_mode = "--view-all" in sys.argv

        self.app_cfg = load_editor_config()
        self.theme_name = self.app_cfg["theme"].lower()
        if self.theme_name not in THEMES:
            self.theme_name = "dark" if self.last_is_dark else "light"
            
        self.accent_color = self.app_cfg.get("accent_color", "#E6FF00")
        self.rainbow_mode = self.app_cfg.get("rainbow_mode", False)
        self.rainbow_speed = self.app_cfg.get("rainbow_speed", 2)
        self.current_hue = 0.0
        
        self.spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.spinner_idx = 0
        self.spinner_timer = QTimer(self)
        self.spinner_timer.timeout.connect(self.update_spinner_ui)
        
        self.init_ui()
        self.apply_style()
        
        if self.rainbow_mode:
            self.rainbow_timer = QTimer(self)
            self.rainbow_timer.setTimerType(Qt.TimerType.PreciseTimer)
            self.rainbow_timer.timeout.connect(self.update_rainbow_tick)
            self.rainbow_timer.start(33)
            
        self.theme_timer = QTimer(self)
        self.theme_timer.timeout.connect(self.check_system_theme)
        self.theme_timer.start(2000)
        
        self.fetch_all_releases()

    def relaunch_app(self):
        start_bat = os.path.join(self.install_dir, "Start.bat")
        main_script_1 = os.path.join(self.install_dir, "main.py")
        main_script_2 = os.path.join(self.install_dir, "Splatoon3-RSDBEditor", "main.py")
        
        try:
            if os.path.exists(start_bat):
                if os.name == 'nt':
                    subprocess.Popen(
                        f'start "" "{start_bat}"', 
                        cwd=self.install_dir, 
                        shell=True, 
                        creationflags=0x00000010  # CREATE_NEW_CONSOLE
                    )
                else:
                    subprocess.Popen([start_bat], cwd=self.install_dir)
            elif os.path.exists(main_script_1):
                kwargs = {'cwd': self.install_dir}
                if os.name == 'nt':
                    kwargs['creationflags'] = 0x00000008 | 0x00000200
                else:
                    kwargs['stdin'] = subprocess.DEVNULL
                    kwargs['stdout'] = subprocess.DEVNULL
                    kwargs['stderr'] = subprocess.DEVNULL
                subprocess.Popen([sys.executable, main_script_1], **kwargs)
            elif os.path.exists(main_script_2):
                kwargs = {'cwd': os.path.join(self.install_dir, "Splatoon3-RSDBEditor")}
                if os.name == 'nt':
                    kwargs['creationflags'] = 0x00000008 | 0x00000200
                else:
                    kwargs['stdin'] = subprocess.DEVNULL
                    kwargs['stdout'] = subprocess.DEVNULL
                    kwargs['stderr'] = subprocess.DEVNULL
                subprocess.Popen([sys.executable, main_script_2], **kwargs)
        except Exception:
            pass
            
        time.sleep(1.0)
        sys.exit(0)

    def check_system_theme(self):
        current_dark = darkdetect.isDark()
        if current_dark != self.last_is_dark:
            self.last_is_dark = current_dark
            new_icon = get_app_icon()
            self.setWindowIcon(new_icon)
            QApplication.instance().setWindowIcon(new_icon)
            
            if self.app_cfg["theme"].lower() not in THEMES:
                self.theme_name = "dark" if current_dark else "light"
                self.apply_style()

    def _convert_markdown_to_html(self, text):
        if not text:
            return ""
        text_normalized = text.replace("\r\n", "\n")
        return re.sub(r'(?<!\n)\n(?!\n)', '\n\n', text_normalized)

    def init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        card_frame = QFrame(self)
        card_frame.setObjectName("Card")
        card_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        card_layout = QVBoxLayout(card_frame)
        card_layout.setContentsMargins(15, 15, 15, 15)
        card_layout.setSpacing(12)
        
        title_lbl = QLabel("Splatoon 3 RSDB Editor (Updater)", card_frame)
        title_lbl.setObjectName("CardTitle")
        card_layout.addWidget(title_lbl)
        
        self.version_lbl = QLabel(f"Current version installed: {self.current_version}", card_frame)
        self.version_lbl.setObjectName("CardVersion")
        card_layout.addWidget(self.version_lbl)
        
        self.beta_checkbox = QCheckBox("Include main branch [not recommended]", card_frame)
        self.beta_checkbox.stateChanged.connect(self.toggle_beta_mode)
        card_layout.addWidget(self.beta_checkbox)
        
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(0, 0, 0, 0)
        
        self.status_lbl = QLabel("Checking available Editor versions...", card_frame)
        status_layout.addWidget(self.status_lbl)
        
        self.status_icon_lbl = QLabel("", card_frame)
        self.status_icon_lbl.setFixedWidth(20)
        status_layout.addWidget(self.status_icon_lbl)
        
        status_layout.addStretch()
        
        card_layout.addLayout(status_layout)
        
        combo_layout = QHBoxLayout()
        combo_layout.setContentsMargins(0, 0, 0, 0)
        
        self.version_combo = QComboBox(card_frame)
        self.version_combo.setEnabled(False)
        self.version_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        combo_layout.addWidget(self.version_combo)
        
        self.btn_refresh = QPushButton("🔄", card_frame)
        self.btn_refresh.clicked.connect(self.refresh_data)
        combo_layout.addWidget(self.btn_refresh)
        
        card_layout.addLayout(combo_layout)
        
        self.browser = QTextEdit(card_frame)
        self.browser.setReadOnly(True)
        self.browser.setMinimumHeight(150)
        self.browser.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        card_layout.addWidget(self.browser)
        
        self.version_combo.currentIndexChanged.connect(self.on_version_changed_index)
        
        main_layout.addWidget(card_frame)
        
        btn_layout = QHBoxLayout()
        
        btn_text = "Install"
        if self.force_reinstall_mode:
            btn_text = "Reinstall Current Version"
        elif self.force_prerelease_mode:
            btn_text = "Install Beta Build"
        
        self.btn_execute = QPushButton(btn_text, self)
        self.btn_execute.setObjectName("btnExecute")
        self.btn_execute.setEnabled(False)
        self.btn_execute.clicked.connect(self.start_installation)
        
        self.lbl_warning_symbol = QLabel("", self)
        self.lbl_warning_symbol.setMinimumWidth(15)
        self.lbl_warning_symbol.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.opacity_effect = QGraphicsOpacityEffect(self.lbl_warning_symbol)
        self.lbl_warning_symbol.setGraphicsEffect(self.opacity_effect)
        
        self.pulse_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.pulse_anim.setStartValue(1.0)
        self.pulse_anim.setKeyValueAt(0.5, 0.3)
        self.pulse_anim.setEndValue(1.0)
        self.pulse_anim.setLoopCount(-1)
        self.pulse_anim.setDuration(2000)
        
        self.btn_cancel = QPushButton("Cancel", self)
        self.btn_cancel.clicked.connect(self.handle_cancel)
        
        btn_layout.addWidget(self.btn_execute)
        btn_layout.addWidget(self.lbl_warning_symbol)
        btn_layout.addStretch(1)
        btn_layout.addWidget(self.btn_cancel)
        
        main_layout.addLayout(btn_layout)
        
        self.setFixedSize(550, 550)

    def apply_style(self):
        self.setStyleSheet(get_stylesheet(self.theme_name, self.accent_color))
        self.update_scrollbar_stylesheet()

    def update_rainbow_tick(self):
        increment = self.rainbow_speed * 0.8
        self.current_hue = (self.current_hue + increment) % 360.0
        is_dark = self.theme_name in ["dark", "oled"]
        sat_f = 200.0 / 255.0 if is_dark else 240.0 / 255.0
        val_f = 255.0 / 255.0 if is_dark else 180.0 / 255.0
        r, g, b = colorsys.hsv_to_rgb(self.current_hue / 360.0, sat_f, val_f)
        self.accent_color = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
        self.apply_style()

    def update_spinner_ui(self):
        self.status_icon_lbl.setText(self.spinner_chars[self.spinner_idx])
        self.spinner_idx = (self.spinner_idx + 1) % len(self.spinner_chars)

    def update_scrollbar_stylesheet(self):
        tmp_dir = QDir.tempPath() + "/SplatoonEditor_SVGs"
        QDir().mkpath(tmp_dir)
        
        def create_svg_file(name, color, is_up):
            path = tmp_dir + "/" + name
            pts = "18 15 12 9 6 15" if is_up else "6 9 12 15 18 9"
            content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="{pts}"/></svg>"""
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return path

        up_idle = create_svg_file("up_idle.svg", "#8A8A95", True)
        up_hover = create_svg_file("up_hover.svg", "#FFFFFF", True)
        down_idle = create_svg_file("down_idle.svg", "#8A8A95", False)
        down_hover = create_svg_file("down_hover.svg", "#FFFFFF", False)

        self.browser.setStyleSheet(f"""
            QTextEdit {{
                background-color: #1E1E24;
                color: #E8E8E8;
                border: 1px solid #4A4A55;
                border-radius: 8px;
                padding: 8px;
            }}
            QScrollBar:vertical {{
                border: none;
                background: #2D2D36;
                width: 20px;
                margin: 0px 0 0px 0;
                padding-top: 20px;
                padding-bottom: 20px;
            }}
            QScrollBar::handle:vertical {{
                background: {self.accent_color};
                width: 20px;
                min-height: 40px;
                border-radius: 6px;
            }}
            QScrollBar::add-line:vertical {{
                border: none;
                background: #3A3A45;
                width: 20px;
                height: 20px;
                subcontrol-position: bottom;
                subcontrol-origin: margin;
                border-radius: 6px;
            }}
            QScrollBar::sub-line:vertical {{
                border: none;
                background: #3A3A45;
                width: 20px;
                height: 20px;
                subcontrol-position: top;
                subcontrol-origin: margin;
                border-radius: 6px;
            }}
            QScrollBar::add-line:vertical:hover, QScrollBar::sub-line:vertical:hover,
            QScrollBar::add-line:vertical:pressed, QScrollBar::sub-line:vertical:pressed {{
                background: {self.accent_color};
            }}
            QScrollBar::up-arrow:vertical {{
                image: url("{up_idle}");
                width: 14px;
                height: 14px;
            }}
            QScrollBar::down-arrow:vertical {{
                image: url("{down_idle}");
                width: 14px;
                height: 14px;
            }}
            QScrollBar::up-arrow:vertical:hover, QScrollBar::up-arrow:vertical:pressed {{
                image: url("{up_hover}");
            }}
            QScrollBar::down-arrow:vertical:hover, QScrollBar::down-arrow:vertical:pressed {{
                image: url("{down_hover}");
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
                border: none;
            }}
        """)

    def set_warning(self, warn_state):
        if warn_state:
            self.lbl_warning_symbol.setText("⚠️")
            if self.pulse_anim.state() != QAbstractAnimation.State.Running:
                self.pulse_anim.start()
        else:
            self.pulse_anim.stop()
            self.opacity_effect.setOpacity(1.0)
            self.lbl_warning_symbol.setText("")

    def refresh_data(self):
        if hasattr(self, 'btn_refresh'):
            self.btn_refresh.setEnabled(False)
        self.status_icon_lbl.setText("")
        self.status_lbl.setText("Refreshing data from GitHub...")
        self.version_combo.clear()
        self.version_combo.setEnabled(False)
        self.btn_execute.setEnabled(False)
        self.fetch_all_releases()

    def toggle_beta_mode(self, state):
        self.version_combo.clear()
        self.set_warning(False)
        self.browser.clear()
        
        for text, data in self.cached_releases:
            self.version_combo.addItem(text, data)
            
        if state == 2:
            self.btn_execute.setEnabled(False)
            QTimer.singleShot(100, self.fetch_beta_source)
        else:
            self.btn_execute.setEnabled(self.version_combo.count() > 0)
            self.check_version_warnings(self.version_combo.currentIndex())

    def merge_dicts(self, dict1, dict2):
        return {**dict1, **dict2}

    def fetch_all_releases(self):
        self.fetch_thread = ReleasesFetchThread()
        self.fetch_thread.finished.connect(self.process_releases)
        self.fetch_thread.start()

    def process_releases(self, data, error_str):
        if error_str:
            self.status_icon_lbl.setText("❌")
            self.status_lbl.setText(f"API Connection Error: {error_str}")
            if hasattr(self, 'btn_refresh'):
                self.btn_refresh.setEnabled(True)
            return
            
        self.releases_data = data
        self.cached_releases = []
        self.version_combo.clear()
        self.browser.clear()
        self.status_icon_lbl.setText("")
        
        first_stable_idx = -1
        prerelease_idx = -1
        latest_stable_tag = ""
        
        for idx, release in enumerate(data):
            tag = release.get("tag_name", "").strip().lstrip('v')
            if tag:
                if release.get("prerelease", False):
                    display_name = f"{tag} [!Pre-release!]"
                    if prerelease_idx == -1:
                        prerelease_idx = idx
                else:
                    display_name = tag
                    if first_stable_idx == -1:
                        first_stable_idx = idx
                        latest_stable_tag = tag
                        
                self.cached_releases.append((display_name, release))
                self.version_combo.addItem(display_name, release)

        self.first_stable_idx = first_stable_idx
        self.is_dev_version = False
        
        if latest_stable_tag:
            try:
                import packaging.version
                v_curr = packaging.version.parse(self.current_version.lstrip('v'))
                v_stab = packaging.version.parse(latest_stable_tag)
                if v_curr > v_stab:
                    self.is_dev_version = True
            except Exception:
                pass
                
        if self.version_combo.count() > 0:
            self.status_lbl.setText("Select a release:")
            self.version_combo.setEnabled(True)
            self.btn_execute.setEnabled(True)
            
            if self.is_dev_version and not self.force_reinstall_mode and not self.force_prerelease_mode and not self.force_view_all_mode:
                self.version_lbl.setText(f"Current version installed: {self.current_version} ⚠️ [DEV]")
                self.version_lbl.setStyleSheet("color: #e67e22; font-weight: bold;")
                
                if first_stable_idx != -1:
                    self.version_combo.setCurrentIndex(first_stable_idx)
                else:
                    self.version_combo.setCurrentIndex(0)
            else:
                if self.force_reinstall_mode:
                    self.status_lbl.setText("Automatic reinstallation triggered...")
                    QTimer.singleShot(300, self.start_installation)
                elif self.force_prerelease_mode and prerelease_idx != -1:
                    self.version_combo.setCurrentIndex(prerelease_idx)
                    self.status_lbl.setText("Automatic reinstallation (beta) triggered...")
                    QTimer.singleShot(300, self.start_installation)
                elif self.force_view_all_mode:
                    self.version_combo.setCurrentIndex(0)
                else:
                    if data[0].get("prerelease", False) and first_stable_idx != -1:
                        self.version_combo.setCurrentIndex(first_stable_idx)
                    else:
                        self.version_combo.setCurrentIndex(0)
            
            self.check_version_warnings(self.version_combo.currentIndex())
                        
            if self.beta_checkbox.isChecked():
                self.toggle_beta_mode(2)
        else:
            self.status_lbl.setText("No public release distributions found?")
            
        if hasattr(self, 'btn_refresh'):
            self.btn_refresh.setEnabled(True)

    def fetch_beta_source(self):
        url = f"https://raw.githubusercontent.com/JeremKOYTB/Splatoon3-RSDBEditor/refs/heads/main/Splatoon3-RSDBEditor/main.py?t={int(time.time())}"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Splatoon3RSDBEditor-Updater'})
                
            with urllib.request.urlopen(req, timeout=5) as response:
                code = response.read().decode('utf-8', errors='ignore')
            
            match = re.search(r'APP_VERSION\s*=\s*["\']([^"\']+)["\']', code)
            beta_version = match.group(1) if match else "Unknown"
            display_version = beta_version if beta_version.startswith("v") else f"v{beta_version}"
            
            target_zip = "https://api.github.com/repos/JeremKOYTB/Splatoon3-RSDBEditor/zipball/main"
            
            dummy_release = {
                "tag_name": f"main branch ({display_version})", 
                "zipball_url": target_zip, 
                "assets": [],
                "is_main_branch_node": True
            }
            
            self.version_combo.insertItem(0, f"main branch ({display_version})", dummy_release)
            self.version_combo.setCurrentIndex(0)
            self.check_version_warnings(self.version_combo.currentIndex())
            self.btn_execute.setEnabled(True)
        except Exception as e:
            self.browser.setHtml(f"<div style='color: #EF5350;'>Failed to fetch main branch metadata: {e}</div>")
            self.set_warning(False)
            self.btn_execute.setEnabled(False)
            
        if hasattr(self, 'btn_refresh'):
            self.btn_refresh.setEnabled(True)

    def on_version_changed_index(self, index):
        if index < 0:
            return
        current_data = self.version_combo.currentData()
        self.browser.clear()
        
        self.check_version_warnings(index)
        
        if isinstance(current_data, dict) and current_data.get("is_main_branch_node", False):
            self.browser.setHtml("<div style='color: #8A8A95; font-style: italic;'>Fetching latest commit data from GitHub...</div>")
            self.commit_thread = MainBranchCommitFetchThread()
            self.commit_thread.finished.connect(self.on_main_branch_commit_loaded)
            self.commit_thread.start()
        else:
            changelog_text = current_data.get("body", "No changelog provided.") if isinstance(current_data, dict) else ""
            self.browser.setMarkdown(self._convert_markdown_to_html(changelog_text))

    def on_main_branch_commit_loaded(self, commit_text):
        self.browser.setHtml(commit_text)

    def check_version_warnings(self, index):
        if index < 0: return
        current_text = self.version_combo.currentText()
        current_data = self.version_combo.currentData()
        
        is_dangerous = False
        is_stable = False
        
        if "main branch" in current_text:
            is_dangerous = True
        elif isinstance(current_data, dict):
            if current_data.get("prerelease", False):
                is_dangerous = True
            elif not current_data.get("is_main_branch_node", False):
                is_stable = True
                
        self.set_warning(is_dangerous)
        
        if not self.force_reinstall_mode and not self.force_prerelease_mode:
            if is_dangerous:
                self.btn_execute.setText("Install (Not recommended)")
            elif self.is_dev_version and is_stable:
                self.btn_execute.setText("Revert to Stable")
            else:
                self.btn_execute.setText("Install")

    def start_installation(self, *args):
        current_data = self.version_combo.currentData()
        if not current_data: return
        
        current_text = self.version_combo.currentText()
        base_version = current_text.split(" ")[0]
        
        download_url = None
        is_main_branch = current_data.get("is_main_branch_node", False)
        
        if is_main_branch:
            download_url = current_data.get("zipball_url")
        else:
            assets = current_data.get("assets", [])
            for asset in assets:
                name = asset.get("name", "").lower()
                if name.endswith(".zip") or name.endswith(".7z"):
                    download_url = asset.get("browser_download_url")
                    break
                    
        if not download_url:
            self.status_icon_lbl.setText("❌")
            self.status_lbl.setText("Select a release:")
            err_box = QMessageBox(self)
            err_box.setWindowIcon(get_app_icon())
            err_box.setIcon(QMessageBox.Icon.Critical)
            err_box.setWindowTitle("Asset Missing")
            err_box.setText("Security: No valid compiled asset (.zip or .7z) was found in this release. Source code download is explicitly forbidden for official releases.")
            err_box.exec()
            return
            
        self.version_combo.setEnabled(False)
        self.btn_execute.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.beta_checkbox.setEnabled(False)
        if hasattr(self, 'btn_refresh'):
            self.btn_refresh.setEnabled(False)
            
        self.spinner_timer.start(100)
        
        self.worker = DownloadWorkerThread(download_url, self.install_dir, base_version)
        self.worker.progress.connect(self.status_lbl.setText)
        self.worker.completed.connect(self.installation_finished)
        self.worker.start()

    def installation_finished(self, success, message):
        self.spinner_timer.stop()
        if success:
            self.status_icon_lbl.setText("✅")
            self.status_lbl.setText("Complete.")
            success_box = QMessageBox(self)
            success_box.setWindowIcon(get_app_icon())
            success_box.setIcon(QMessageBox.Icon.Information)
            success_box.setWindowTitle("Success:")
            success_box.setText("Splatoon 3 RSDB Editor has been updated successfully.\n\nPress OK to reload the Editor.")
            success_box.exec()
            self.relaunch_app()
        else:
            self.status_icon_lbl.setText("❌")
            self.status_lbl.setText("Select a release:")
            fail_box = QMessageBox(self)
            fail_box.setWindowIcon(get_app_icon())
            fail_box.setIcon(QMessageBox.Icon.Critical)
            fail_box.setWindowTitle("Installation Failed...")
            fail_box.setText(f"Critical execution error:\n{message}")
            fail_box.exec()
            
            self.version_combo.setEnabled(True)
            self.btn_execute.setEnabled(True)
            self.btn_cancel.setEnabled(True)
            self.beta_checkbox.setEnabled(True)
            if hasattr(self, 'btn_refresh'):
                self.btn_refresh.setEnabled(True)

    def handle_cancel(self, *args):
        box = QMessageBox(self)
        box.setWindowIcon(get_app_icon())
        box.setWindowTitle("Cancel Update")
        box.setText(f"Do you want to return to Splatoon 3 RSDB Editor ({self.current_version}) or exit completely?")
        box.setIcon(QMessageBox.Icon.Question)
        
        btn_return = box.addButton("Return to Editor", QMessageBox.ButtonRole.YesRole)
        btn_exit = box.addButton("Exit", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("Stay here", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(btn_return)
        box.exec()
        
        if box.clickedButton() == btn_return:
            self.relaunch_app()
        elif box.clickedButton() == btn_exit:
            sys.exit(0)
        else:
            self.status_icon_lbl.setText("❌")
            self.status_lbl.setText("Select a release:")

class MainBranchCommitFetchThread(QThread):
    finished = pyqtSignal(str)

    def run(self):
        url = f"https://api.github.com/repos/JeremKOYTB/Splatoon3-RSDBEditor/commits/main?t={int(time.time())}"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Splatoon3RSDBEditor-Updater'})
                
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                
            sha = data.get("sha", "")[:7]
            commit_info = data.get("commit", {})
            message = commit_info.get("message", "No description provided.")
            author_info = commit_info.get("author", {})
            date_str = author_info.get("date", "").replace("T", " ").replace("Z", "")
            
            html_output = (
                f"<div style='margin-bottom: 4px;'><b style='color: #C4A1FF;'>Latest Main Commit:</b> <code style='background-color: #2D2D36; padding: 2px 4px; border-radius: 4px; color: #FFFFFF;'>{sha}</code></div>"
                f"<div style='margin-bottom: 4px;'><b style='color: #8A8A95;'>Date:</b> <span style='color: #E8E8E8;'>{date_str}</span></div>"
                f"<hr style='border: none; border-top: 1px solid #4A4A55; margin: 6px 0;'>"
                f"<div><b style='color: #FFFFFF;'>Modification Notes:</b></div>"
                f"<div style='color: #E8E8E8; white-space: pre-wrap; margin-top: 4px;'>{message}</div>"
            )
            self.finished.emit(html_output)
        except Exception as e:
            self.finished.emit(f"<div style='color: #EF5350;'>Failed to reach main branch commit API endpoint: {e}</div>")

def handle_interrupt(window_instance):
    box = QMessageBox(window_instance)
    box.setWindowIcon(window_instance.get_app_icon())
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle("Exit?")
    box.setText("Ctrl+C was detected in the terminal.\n\nDo you want to close the updater?")
    box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    box.setDefaultButton(QMessageBox.StandardButton.No)
    box.setWindowFlags(box.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
    if box.exec() == QMessageBox.StandardButton.Yes:
        QApplication.quit()
        sys.exit(0)

if __name__ == "__main__":
    if os.name == 'nt':
        import ctypes
        myappid = 'jeremkoytb.splatoon3rsdbeditor.updater'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    current_script = os.path.abspath(__file__)
    appdata_dir = os.path.join(os.environ.get("APPDATA", ""), "Splatoon3RSDBEditor")
    temp_updater = os.path.join(appdata_dir, "TempUpdater.py")

    if os.path.normcase(current_script) != os.path.normcase(temp_updater):
        relocated_successfully = False
        try:
            os.makedirs(appdata_dir, exist_ok=True)
            shutil.copy2(current_script, temp_updater)
            
            for _ in range(10):
                if os.path.exists(temp_updater) and os.path.getsize(temp_updater) > 0:
                    break
                time.sleep(0.05)
                
            args = [sys.executable, temp_updater]
            passed_args = sys.argv[1:]
            if "--install-dir" not in passed_args:
                args.extend(["--install-dir", os.path.dirname(current_script)])
            args.extend(passed_args)
            
            log_file_path = os.path.join(appdata_dir, "updater_debug.log")
            debug_log = open(log_file_path, "w", encoding="utf-8")
            kwargs = {
                "stdin": subprocess.DEVNULL,
                "stdout": debug_log,
                "stderr": subprocess.STDOUT
            }
            if os.name == 'nt':
                kwargs['creationflags'] = 0x00000008 | 0x00000200
                
            proc = subprocess.Popen(args, **kwargs)
            time.sleep(0.4)
            if proc.poll() is None:
                relocated_successfully = True
        except Exception:
            pass 
            
        if relocated_successfully:
            sys.exit(0)

    app = QApplication(sys.argv)
    window = UpdaterWindow(APP_VERSION)
    window.show()
    
    timer = QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)
    signal.signal(signal.SIGINT, lambda sig, frame: handle_interrupt(window))
    sys.exit(app.exec())
    