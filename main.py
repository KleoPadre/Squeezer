#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow


def main():
    """Основная точка входа приложения"""
    app = QApplication(sys.argv)
    app.setApplicationName("Squeezer")
    app.setOrganizationName("Squeezer")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
