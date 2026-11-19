"""python -m cloudfolder.desktop [--server http://127.0.0.1:8000]"""
import argparse
import sys

from PySide6.QtWidgets import QApplication, QDialog

from .login_dialog import LoginDialog
from .main_window import MainWindow
from .theme import apply_theme


def main() -> int:
    parser = argparse.ArgumentParser(description="Десктоп-клієнт «Хмарне сховище»")
    parser.add_argument("--server", default="http://127.0.0.1:8000")
    args, qt_args = parser.parse_known_args()

    app = QApplication([sys.argv[0], *qt_args])
    app.setApplicationName("Хмарне сховище")
    apply_theme(app)
    server = args.server
    while True:
        dlg = LoginDialog(server)
        if dlg.exec() != QDialog.Accepted or dlg.client is None:
            return 0
        server = dlg.client.base_url
        win = MainWindow(dlg.client)
        win.logged_out = False
        win.show()
        app.exec()
        if not win.logged_out:
            return 0


if __name__ == "__main__":
    sys.exit(main())
