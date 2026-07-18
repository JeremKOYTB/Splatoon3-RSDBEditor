import sys
import os
import subprocess
import traceback
import json
import importlib
from datetime import datetime

def exception_hook(exctype, value, tb):
    if issubclass(exctype, KeyboardInterrupt):
        print("\n💬 [INFO] Program cleanly stopped by user (Ctrl+C). Goodbye!")
        sys.exit(0)

    print("\n" + "="*60)
    print("🚨 [FATAL CRITICAL CRASH] The program crashed! 🚨")
    print("="*60)
    traceback.print_exception(exctype, value, tb)
    print("="*60 + "\n")
    
    try:
        with open("crash_report_rsdb.log", "w", encoding="utf-8") as f:
            f.write(f"Crash Time: {datetime.now()}\n\n")
            traceback.print_exception(exctype, value, tb, file=f)
        print("💾 A crash report has been saved to: crash_report_rsdb.log\n")
    except:
        pass

    sys.stderr.flush()
    sys.stdout.flush()
    sys.exit(1)

sys.excepthook = exception_hook

def log(msg):
    time_str = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{time_str}] 💬 {msg}")

log("[INIT] Starting Splatoon 3 RSDB Editor...")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, "cache")
CONFIG_FILE = os.path.join(BASE_DIR, "splatoon_RSDBeditor_config.json")

if not os.path.exists(CACHE_DIR):
    log(f"[SYSTEM] Creating cache directory: {CACHE_DIR}")
    os.makedirs(CACHE_DIR)

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception as e: 
            log(f"[ERROR] Cannot read config file: {e}")
    return {}

def save_config(data):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e: 
        log(f"[ERROR] Cannot save configuration: {e}")

def get_last_rsdb_dir(): return load_config().get("last_rsdb_dir", "")
def set_last_rsdb_dir(dir_path): save_config({**load_config(), "last_rsdb_dir": dir_path})
def get_last_save_dir(): return load_config().get("last_save_dir", get_last_rsdb_dir())
def set_last_save_dir(dir_path): save_config({**load_config(), "last_save_dir": dir_path})
def get_editor_mode(): return load_config().get("easy_mode", True)
def save_editor_mode(is_easy): save_config({**load_config(), "easy_mode": is_easy})
def get_hide_filenames(): return load_config().get("hide_filenames", True)
def save_hide_filenames(state): save_config({**load_config(), "hide_filenames": state})
def get_hide_coop(): return load_config().get("hide_coop", False)
def save_hide_coop(state): save_config({**load_config(), "hide_coop": state})
def get_hide_mission(): return load_config().get("hide_mission", False)
def save_hide_mission(state): save_config({**load_config(), "hide_mission": state})
def get_hide_notfound(): return load_config().get("hide_notfound", False)
def save_hide_notfound(state): save_config({**load_config(), "hide_notfound": state})
def get_favorites(): return set(load_config().get("favorites", []))
def save_favorites(fav_set): save_config({**load_config(), "favorites": list(fav_set)})
def get_saved_language(): return load_config().get("language", "English (US)")
def save_language(lang_name): save_config({**load_config(), "language": lang_name})

def install_requirements():
    log("[SYSTEM] Checking dependencies...")
    required_packages = {
        "requests": "requests",
        "zstandard": "zstandard",
        "byml": "byml",
        "PyQt6": "PyQt6",
        "darkdetect": "darkdetect",
        "packaging": "packaging"
    }
    
    needs_restart = False
    for module_name, package_name in required_packages.items():
        try:
            importlib.import_module(module_name)
        except ImportError:
            log(f"[SYSTEM] -> Missing installation detected: '{package_name}'. Installing via pip...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
                needs_restart = True
            except subprocess.CalledProcessError:
                print("\n" + "="*70)
                print(f"❌ [CRITICAL ERROR] The installation of library '{package_name}' failed.")
                print("="*70 + "\n")
                sys.exit(1)

    if needs_restart:
        log("[SYSTEM] Restarting script to apply dependencies...")
        subprocess.Popen([sys.executable] + sys.argv)
        sys.exit(0)