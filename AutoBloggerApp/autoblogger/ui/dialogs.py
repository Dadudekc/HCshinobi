# autoblogger/ui/dialogs.py

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QTabWidget,
    QWidget,
    QFormLayout,
    QCheckBox,
    QSpinBox,
    QComboBox,
)
from PyQt5.QtCore import Qt
import configparser
from pathlib import Path


class SetupWizardDialog(QDialog):
    def __init__(self, parent=None):
        super(SetupWizardDialog, self).__init__(parent)
        self.setWindowTitle("AutoBloggerApp Setup Wizard")
        self.setModal(True)
        self.setMinimumWidth(500)

        self.init_ui()

    def init_ui(self):
        """Initialize the setup wizard UI."""
        layout = QVBoxLayout(self)

        # Welcome message
        welcome_label = QLabel("Welcome to AutoBloggerApp Setup")
        welcome_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(welcome_label)

        # WordPress Settings
        wp_group = QWidget()
        wp_layout = QFormLayout(wp_group)

        self.wp_url = QLineEdit()
        self.wp_username = QLineEdit()
        self.wp_password = QLineEdit()
        self.wp_password.setEchoMode(QLineEdit.Password)

        wp_layout.addRow("WordPress URL:", self.wp_url)
        wp_layout.addRow("Username:", self.wp_username)
        wp_layout.addRow("Password:", self.wp_password)

        layout.addWidget(wp_group)

        # Buttons
        button_layout = QHBoxLayout()

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(self.save_config)
        button_layout.addWidget(self.next_button)

        layout.addLayout(button_layout)

    def save_config(self):
        """Save the configuration and close the dialog."""
        if not self.validate_inputs():
            return

        config = configparser.ConfigParser()
        config["wordpress"] = {
            "url": self.wp_url.text(),
            "username": self.wp_username.text(),
            "password": self.wp_password.text(),
        }

        config_path = Path(__file__).resolve().parent.parent / "config" / "config.ini"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, "w") as f:
            config.write(f)

        self.accept()

    def validate_inputs(self):
        """Validate the input fields."""
        if not self.wp_url.text():
            QMessageBox.warning(self, "Validation Error", "WordPress URL is required.")
            return False

        if not self.wp_username.text():
            QMessageBox.warning(self, "Validation Error", "Username is required.")
            return False

        if not self.wp_password.text():
            QMessageBox.warning(self, "Validation Error", "Password is required.")
            return False

        return True


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super(SettingsDialog, self).__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setMinimumWidth(600)

        self.init_ui()

    def init_ui(self):
        """Initialize the settings dialog UI."""
        layout = QVBoxLayout(self)

        # Create tab widget
        tab_widget = QTabWidget()

        # WordPress Settings Tab
        wp_tab = QWidget()
        wp_layout = QFormLayout(wp_tab)

        self.wp_url = QLineEdit()
        self.wp_username = QLineEdit()
        self.wp_password = QLineEdit()
        self.wp_password.setEchoMode(QLineEdit.Password)

        wp_layout.addRow("WordPress URL:", self.wp_url)
        wp_layout.addRow("Username:", self.wp_username)
        wp_layout.addRow("Password:", self.wp_password)

        tab_widget.addTab(wp_tab, "WordPress")

        # Generation Settings Tab
        gen_tab = QWidget()
        gen_layout = QFormLayout(gen_tab)

        self.default_model = QComboBox()
        self.default_model.addItems(["GPT-4", "Mistral", "Custom"])
        gen_layout.addRow("Default Model:", self.default_model)

        self.default_style = QComboBox()
        self.default_style.addItems(["Professional", "Casual", "Technical", "Creative"])
        gen_layout.addRow("Default Style:", self.default_style)

        self.default_length = QSpinBox()
        self.default_length.setRange(500, 5000)
        self.default_length.setSingleStep(100)
        self.default_length.setValue(1000)
        gen_layout.addRow("Default Length:", self.default_length)

        tab_widget.addTab(gen_tab, "Generation")

        # Advanced Settings Tab
        adv_tab = QWidget()
        adv_layout = QFormLayout(adv_tab)

        self.auto_save = QCheckBox("Auto-save drafts")
        adv_layout.addRow(self.auto_save)

        self.auto_publish = QCheckBox("Auto-publish after generation")
        adv_layout.addRow(self.auto_publish)

        self.debug_mode = QCheckBox("Enable debug mode")
        adv_layout.addRow(self.debug_mode)

        tab_widget.addTab(adv_tab, "Advanced")

        layout.addWidget(tab_widget)

        # Buttons
        button_layout = QHBoxLayout()

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.accept)
        button_layout.addWidget(self.save_button)

        layout.addLayout(button_layout)

    def get_settings(self):
        """Get the current settings values."""
        return {
            "wordpress": {
                "url": self.wp_url.text(),
                "username": self.wp_username.text(),
                "password": self.wp_password.text(),
            },
            "generation": {
                "default_model": self.default_model.currentText(),
                "default_style": self.default_style.currentText(),
                "default_length": self.default_length.value(),
            },
            "advanced": {
                "auto_save": self.auto_save.isChecked(),
                "auto_publish": self.auto_publish.isChecked(),
                "debug_mode": self.debug_mode.isChecked(),
            },
        }
