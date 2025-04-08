from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QLabel, QSizePolicy
from PyQt5.QtCore import Qt

class PromptPreviewDialog(QDialog):
    """
    A reusable modal dialog for previewing generated prompts.

    Allows users to inspect the prompt details before potentially launching
    or executing them.
    """
    def __init__(self, prompt_title: str, prompt_text: str, parent=None):
        """
        Initializes the dialog.

        Args:
            prompt_title (str): The title to display for the prompt preview.
            prompt_text (str): The formatted text content of the prompt.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)

        self.setWindowTitle("Prompt Preview")
        self.setModal(True)
        self.setMinimumSize(600, 400) # Set a reasonable minimum size

        # Layout
        layout = QVBoxLayout(self)

        # Title Label
        title_label = QLabel(f"<b>{prompt_title}</b>")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Prompt Text Edit (Read-only)
        self.prompt_display = QTextEdit()
        self.prompt_display.setReadOnly(True)
        self.prompt_display.setText(prompt_text)
        self.prompt_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.prompt_display)

        # Buttons (Example: OK button)
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept) # Close dialog on OK
        layout.addWidget(self.ok_button, alignment=Qt.AlignRight)

        self.setLayout(layout)

    @staticmethod
    def show_preview(prompt_title: str, prompt_text: str, parent=None) -> None:
        """
        Static method to create and show the preview dialog.

        Args:
            prompt_title (str): The title for the preview.
            prompt_text (str): The prompt content to display.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        dialog = PromptPreviewDialog(prompt_title, prompt_text, parent)
        dialog.exec_() # Show modally 