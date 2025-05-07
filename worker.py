from PyQt5.QtWidgets import QApplication, QWidget, QProgressBar, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt, QProcess
from PyQt5.QtGui import QIcon
from PyQt5 import QtCore

import os
import sys
import requests
import subprocess
import ctypes
import config



class UpdateWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(config.patcher_title)
        self.setGeometry(500, 500, 400, 150)
        self.setWindowIcon(QIcon(self.resource_path(config.icon_path)))
        self.layout = QVBoxLayout()
        self.message_label = QLabel("Starting update...", self)
        self.message_label.setStyleSheet(
            """
            font-size: 18px;
            color: #444;
            font-weight: bold;
            text-align: center;
        """
        )
        self.layout.addWidget(self.message_label)
        self.progress_bar = QProgressBar(self)
        self.layout.addWidget(self.progress_bar)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.percent_label = QLabel("0%", self)
        self.percent_label.setStyleSheet(
            """
            font-size: 18px;
            color: #444;
            font-weight: bold;
            text-align: center;
        """
        )
        self.percent_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.percent_label)
        self.setLayout(self.layout)
        self.show()

    def resource_path(self, relative_path):
        """Handle resource paths flexibly"""
        relative_path = relative_path.replace("/", "\\")
        if hasattr(sys, "_MEIPASS"):
            full_path = os.path.join(sys._MEIPASS, relative_path)
        else:
            full_path = os.path.join(os.path.abspath("."), relative_path)
        return full_path

    def update_progress(self, message, progress_value):
        """Update the message, progress bar, and percentage."""
        self.message_label.setText(message)
        self.progress_bar.setValue(progress_value)
        self.percent_label.setText(f"{progress_value}%")
        QApplication.processEvents()

    def close_window(self):
        """Close the window."""
        self.close()


def download_file(url, dest_path, window):
    """Download the file from the URL and save it to the destination path."""
    try:
        window.update_progress(f"Downloading...", 0)
        response = requests.get(url, stream=True)
        total_length = int(response.headers.get("content-length", 0))

        if total_length == 0:
            window.update_progress("Download error.", 0)
            return

        with open(dest_path, "wb") as f:
            downloaded = 0
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                percent = int(downloaded * 100 / total_length)
                window.update_progress(config.downloading_text, percent)

        window.update_progress(config.update_complete, 100)
    except Exception as e:
        window.update_progress(f"Error: {e}", 0)


def run_new_patcher(window, updated_patcher_path, patcher_path):
    """
    Run the new patcher in a separate process without blocking the GUI.
    """
    try:
        if os.path.exists(patcher_path):
            window.update_progress("Running the new patcher", 100)
            new_patcher_path = os.path.join(updated_patcher_path, patcher_path)
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", new_patcher_path, None, None, 1
            )
            sys.exit()
        else:
            window.update_progress("New patcher not found.", 0)

    except Exception as e:
        window.update_progress(f"Error during patcher execution: {e}", 0)


def replace_and_run_exe():
    current_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    old_file = os.path.join(current_dir, config.patcher_name)
    temp_file = os.path.join(current_dir, config.patcher_name + "_temp")

    try:
        if os.path.exists(old_file):
            os.remove(old_file)
        if os.path.exists(temp_file):
            os.rename(temp_file, old_file)
        if os.path.exists(old_file):
            subprocess.Popen([old_file], shell=True)
    except PermissionError as e:
        print(f"Permission Error: {e}")
    except Exception as e:
        print(f"Error: {e}")

    sys.exit()


def main():
    app = QApplication(sys.argv)
    window = UpdateWindow()
    file_url = config.patcher_folder + config.patcher_name
    updated_patcher_path = os.path.join(os.getcwd(), config.patcher_name + "_temp")
    patcher_path = os.path.join(os.getcwd(), config.patcher_name)
    download_file(file_url, updated_patcher_path, window)
    replace_and_run_exe()
    run_new_patcher(window, updated_patcher_path, patcher_path)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
