# autoblogger/main.py

import sys
from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow
from utils.logging_setup import setup_logging


def main():
    # Setup logging
    setup_logging()

    # Initialize QApplication
    app = QApplication(sys.argv)

    # Initialize and show the main window
    window = MainWindow()
    window.show()

    # Execute the application
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
