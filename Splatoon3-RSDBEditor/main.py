import sys
import os
import signal
import darkdetect
import json

from utils import install_requirements
install_requirements()

from PyQt6.QtWidgets import QApplication, QDialog
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt, QTimer

from ui_layout import get_stylesheet
from main_window import SplatoonRSDBEditor
from components import OnlineWarningDialog
from utils import log

APP_VERSION = "1.0.1"

if __name__ == "__main__":
    if os.name == 'nt':
        import ctypes
        myappid = f'jeremkoytb.splatoon3rsdbeditor.{APP_VERSION}'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    is_dark = darkdetect.isDark()
    pal = app.palette()
    pal.setColor(app.palette().ColorRole.Window, Qt.GlobalColor.darkGray if is_dark else QColor("#F0F0F5"))
    app.setPalette(pal)
    app.setStyleSheet(get_stylesheet(is_dark))
    
    win = SplatoonRSDBEditor(APP_VERSION)
    
    def sigint_handler(sig, frame):
        if getattr(win, '_is_loading_tree', False):
            log("[INFO] Interruption (Ctrl+C) detectee : Annulation de l'operation en cours...")
            win.cancel_operation = True
        else:
            log("[INFO] Arret propre demande par l'utilisateur (Ctrl+C). Au revoir !")
            QApplication.quit()
            sys.exit(0)
            
    signal.signal(signal.SIGINT, sigint_handler)
    
    timer = QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)
    
    def show_online_warning():
        config_path = "splatoon_RSDBeditor_config.json"
        config = {}
        
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except Exception:
                pass
        
        if not config.get("online_warning_accepted", False):
            dialog = OnlineWarningDialog(win)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                if dialog.chk_confirm.isChecked():
                    config["online_warning_accepted"] = True
                    try:
                        with open(config_path, "w", encoding="utf-8") as f:
                            json.dump(config, f, indent=4)
                    except Exception as e:
                        log(f"[WARNING] Impossible de sauvegarder la configuration: {e}")
            else:
                sys.exit(0)

    QTimer.singleShot(200, show_online_warning)
    
    win.show()
    sys.exit(app.exec())