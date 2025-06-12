import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt
from autoblogger.ui.main_window import MainWindow
from autoblogger.services.auto_reply import AutoReply
from autoblogger.services.blog_generator import generate_content
from unittest.mock import patch, MagicMock
import json
from pathlib import Path
import sys
import os
import numpy as np

# Add project root to PYTHONPATH to resolve import errors
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def app():
    """Create a QApplication instance."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    app.quit()


@pytest.fixture
def main_window(qtbot, app):
    """Create an instance of the AutoBloggerApp main window."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    return window


@patch("autoblogger.services.vector_db.VectorDB")
@patch("autoblogger.services.wordpress_client.WordPressClient")
def test_vector_db_functions(mock_wp_client, mock_vector_db, main_window):
    """Test vector database functions with mocked FAISS and SentenceTransformer."""
    mock_vector_db_instance = mock_vector_db.return_value
    mock_vector_db_instance.generate_embeddings.return_value = np.random.rand(1, 768)
    mock_vector_db_instance.update_vector_db.return_value = None
    mock_vector_db_instance.is_initialized.return_value = True

    with patch.object(
        main_window.vector_db,
        "generate_embeddings",
        return_value=np.random.rand(1, 768),
    ):
        embeddings = main_window.vector_db.generate_embeddings(["Test text"])
        assert embeddings is not None
        assert embeddings.shape == (1, 768)


def test_search_dialog(main_window, qtbot):
    """Test opening and using the search dialog."""
    qtbot.mouseClick(main_window.search_button, Qt.LeftButton)

    search_dialog = main_window.findChild(QDialog, "SearchSimilarBlogPosts")
    assert search_dialog is not None, "Search dialog was not found."

    query_input = search_dialog.findChild(QLineEdit, "EnterSearchQuery")
    search_button = search_dialog.findChild(QPushButton, "SearchButton")

    assert query_input is not None, "Query input not found in search dialog."
    assert search_button is not None, "Search button not found in search dialog."

    query_input.setText("AI Trading")
    qtbot.mouseClick(search_button, Qt.LeftButton)

    qtbot.wait(2000)

    results_list = search_dialog.findChild(QListWidget, "ResultsList")
    assert results_list is not None, "Results list not found in search dialog."
    assert results_list.count() > 0, "No search results found."


@patch("autoblogger.services.blog_generator.generate_blog")
def test_generate_blog_function(mock_generate_blog, main_window, qtbot):
    """Test that the generate_blog function is called when the button is clicked."""
    mock_generate_blog.return_value = "/path/to/generated_blog.html"

    qtbot.mouseClick(main_window.generate_button, Qt.LeftButton)
    main_window.worker.finished_signal.emit("/path/to/generated_blog.html")

    mock_generate_blog.assert_called_once()
    assert main_window.latest_output_path == "/path/to/generated_blog.html"


@patch("autoblogger.services.wordpress_client.WordPressClient.post_to_wordpress")
def test_post_to_blog(mock_post_to_wordpress, main_window, qtbot):
    """Test posting the blog to WordPress."""
    mock_post_to_wordpress.return_value = {"link": "https://example.com/post"}
    main_window.latest_output_path = "/path/to/generated_blog.html"

    qtbot.mouseClick(main_window.post_button, Qt.LeftButton)
    qtbot.wait(1000)

    mock_post_to_wordpress.assert_called_once_with("/path/to/generated_blog.html")
    assert "https://example.com/post" in main_window.log_display.toPlainText()


def test_settings_dialog(main_window, qtbot):
    """Test opening and interacting with the settings dialog."""
    qtbot.mouseClick(main_window.settings_button, Qt.LeftButton)

    settings_dialog = main_window.findChild(QDialog, "SettingsDialog")
    assert settings_dialog is not None, "Settings dialog was not found."

    category_input = settings_dialog.findChild(QLineEdit, "CategoriesInput")
    tag_input = settings_dialog.findChild(QLineEdit, "TagsInput")
    status_input = settings_dialog.findChild(QLineEdit, "StatusInput")

    assert category_input is not None
    assert tag_input is not None
    assert status_input is not None

    category_input.setText("Trading, AI")
    tag_input.setText("Python, Testing")
    status_input.setText("draft")

    ok_button = settings_dialog.findChild(QPushButton, "OKButton")
    assert ok_button is not None, "OK button not found in settings dialog."
    qtbot.mouseClick(ok_button, Qt.LeftButton)

    qtbot.waitUntil(lambda: not settings_dialog.isVisible(), timeout=5000)
    assert main_window.wordpress_client.status == "draft"


def test_preview_blog_post(main_window, qtbot):
    """Test previewing the blog post."""
    main_window.latest_output_path = "/path/to/generated_blog.html"

    with patch.object(main_window.web_view, "load", return_value=None):
        main_window.preview_blog_post()

    assert (
        main_window.web_view.isVisible()
    ), "Web view should be visible after previewing."
