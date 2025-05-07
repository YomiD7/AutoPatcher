from PyQt5.QtCore import pyqtSignal, Qt, QTimer, QPoint, QEvent, QSize
from PyQt5.QtGui import QPalette, QBrush, QPixmap, QIcon, QMovie, QPainter
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QProgressBar,
    QLabel,
    QStackedWidget,
    QMessageBox,
    QDesktopWidget,
)
from PyQt5 import QtCore

import os
import sys
import webbrowser
import subprocess
import config
import ctypes
import hashlib
import requests


def hash_file(filename):
    """Calculate the sha256 hash of a file incrementally."""
    h = hashlib.sha256()
    with open(filename, "rb") as file:
        while chunk := file.read(4096):
            h.update(chunk)
    return h.hexdigest().upper()


def get_patchlist_json():
    """Download the patchlist.json file from the remote server."""
    url = config.patchlist_url
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error downloading patchlist.json: {e}")
        return None


def get_stored_patcher_hash(patchlist_json):
    """Extracts patcher hash from downloaded JSON."""
    return patchlist_json.get("patcher", {}).get("hash")


class UpdateWindow(QWidget):
    start_update_signal = pyqtSignal()
    file_downloading = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        self.setWindowTitle(str(config.patcher_title))
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.drag_position = QPoint()

        # Ottieni le dimensioni dello schermo
        screen_geometry = QDesktopWidget().screenGeometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()

        # Calcola il 25% delle dimensioni dello schermo
        window_width = int(screen_width * 0.50)
        window_height = int(screen_height * 0.50)

        # Centra la finestra sullo schermo
        x = int((screen_width - window_width) / 2)
        y = int((screen_height - window_height) / 2)

        # Imposta la geometria della finestra
        self.setGeometry(x, y, window_width, window_height)

        # Imposta la dimensione fissa
        self.setFixedSize(window_width, window_height)

        # Carica e avvia l'immagine di sfondo
        #self.movie = QMovie(self.resource_path(str(config.background_image_path)))
        #self.movie.setScaledSize(self.size())
        #self.movie.start()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)  # <-- Aggiunto
        self.movie = QMovie(self.resource_path(str(config.background_image_path)))
        self.movie.setScaledSize(self.size())
        self.movie.start()

        # Imposta l'icona della finestra
        self.setWindowIcon(QIcon(self.resource_path(str(config.icon_path))))

        self.current_file = None

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(50)
        self.close_button = QPushButton("X", self)
        self.close_button.setFixedSize(30, 30)
        self.close_button.move(self.width() - 40, 10)
        self.close_button.clicked.connect(self.close)

        self.close_button.setStyleSheet(
            """
            QPushButton {
                background-color: red;
                color: white;
                border: none;
                padding: 5px 10px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: darkred;
            }
        """
        )

        logo_layout = QHBoxLayout()
        logo_layout.setAlignment(Qt.AlignCenter)
        self.logo_label = QLabel(self)
        self.set_image(self.logo_label, str(config.logo_path), (400, 150))
        logo_layout.addWidget(self.logo_label)
        main_layout.addLayout(logo_layout)

        banner_layout = QHBoxLayout()

        self.image_slide = QStackedWidget(self)

        self.slide1_button = self.create_image_button(config.slide1, config.slide1url)
        self.slide2_button = self.create_image_button(config.slide2, config.slide2url)
        self.slide3_button = self.create_image_button(config.slide3, config.slide3url)
        self.slide4_button = self.create_image_button(config.slide4, config.slide4url)

        banner_layout.addWidget(self.image_slide)
        main_layout.addLayout(banner_layout)
        main_layout.addSpacing(400)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.change_slide)
        self.timer.start(5000)
        self.text_block = QWidget(self)
        self.text_block.setStyleSheet(
            """
            QWidget {
                background-color: rgba(255, 255, 255, 0.5);
                padding: 15px;
                border-radius: 15px;
                width: 60%;
                margin: 0 auto;
            }
        """
        )
        text_block_layout = QVBoxLayout(self.text_block)

        self.text_label = QLabel(self)
        self.text_label.setText(config.walltext)

        self.text_label.setStyleSheet(
            "font-size: 16px; color: black; text-align: center;"
        )

        self.text_label.setAlignment(Qt.AlignCenter)
        self.text_label.setOpenExternalLinks(True)

        text_block_layout.addWidget(self.text_label)
        text_block_layout.addWidget(self.text_label)

        self.text_block.adjustSize()
        self.text_block.setFixedHeight(self.text_block.height() + 20)

        right_layout = QHBoxLayout()
        right_layout.addWidget(self.text_block)
        main_layout.addLayout(right_layout)

        main_layout.addSpacing(90)

        button_layout = QHBoxLayout()
        button_layout.setAlignment(Qt.AlignCenter)

        self.register_button = QPushButton(self)
        self.set_image(self.register_button, config.register_button_image, (125, 50))
        self.register_button.setStyleSheet("background: transparent; border: none;")
        self.register_button.setFixedSize(125, 50)
        self.register_button.setIconSize(QtCore.QSize(125, 50))
        self.register_button.clicked.connect(
            lambda: webbrowser.open(config.register_url)
        )
        self.register_button.installEventFilter(self)
        button_layout.addWidget(self.register_button)

        self.config_button = QPushButton(self)
        image_path = self.resource_path(config.config_button_image)
        self.set_image(self.config_button, image_path, (125, 50))
        self.config_button.setStyleSheet("background: transparent; border: none;")
        self.config_button.setFixedSize(125, 50)
        self.config_button.setIconSize(QtCore.QSize(125, 50))
        self.config_button.clicked.connect(self.open_config)
        self.config_button.installEventFilter(self)
        button_layout.addWidget(self.config_button)

        main_layout.addLayout(button_layout)

        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                border: 2px solid #5A5A5A;
                border-radius: 5px;
                text-align: center;
                font-size: 16px;
                color: black;
            }
            QProgressBar::chunk {
                background-color: #3CB371;
                width: 20px;
            }
        """
        )
        progress_layout.addWidget(self.progress_bar)

        self.update_button = QPushButton(self)
        self.set_image(self.update_button, config.start_button_image, (100, 100))
        self.update_button.setIconSize(QtCore.QSize(100, 100))
        self.update_button.setStyleSheet("background: transparent; border: none;")
        self.update_button.clicked.connect(self.emit_update_signal)
        self.update_button.installEventFilter(self)
        progress_layout.addWidget(self.update_button)

        main_layout.addLayout(progress_layout)

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(5, 5, 5, 5)

        self.update_self_button = QPushButton(self)
        self.set_image(self.update_self_button, config.update_image_button, (50, 50))
        self.update_self_button.setStyleSheet("background: transparent; border: none;")
        self.update_self_button.setFixedSize(50, 50)
        self.update_self_button.setIconSize(QtCore.QSize(50, 50))
        self.update_self_button.installEventFilter(self)
        self.update_self_button.clicked.connect(self.run_self_updater)

        button_layout.addWidget(self.update_self_button, alignment=Qt.AlignLeft)
        center_layout = QHBoxLayout()
        center_layout.setAlignment(Qt.AlignCenter)
        center_layout.addWidget(self.config_button)
        center_layout.addWidget(self.register_button)
        button_layout.addLayout(center_layout)

        main_layout.addLayout(button_layout)
        self.current_index = 0
        self.image_paths = []
        self.file_downloading.connect(self.on_file_downloading)

        self.button_images = {
            self.register_button: config.register_button_image,
            self.config_button: config.config_button_image,
            self.update_button: config.start_button_image,
            self.update_self_button: config.update_image_button,
            self.slide1_button: config.slide1,
            self.slide2_button: config.slide2,
            self.slide3_button: config.slide3,
            self.slide4_button: config.slide4,
        }
        self.text_block.hide()

    def set_file_checking_text(self, file_name):
        # Aggiorna il testo della label per indicare quale file sta venendo verificato
        self.label.setText(f"Checking: {file_name}")

#    def paintEvent(self, event):
#        """Draw GIF as background."""
#        painter = QPainter(self)
#        painter.setRenderHint(QPainter.Antialiasing)
#        current_frame = self.movie.currentPixmap()
#        painter.drawPixmap(self.rect(), current_frame)

    def paintEvent(self, event):
        painter = QPainter(self)
        current_frame = self.movie.currentPixmap()
        if not current_frame.isNull():
            painter.drawPixmap(0, 0, self.width(), self.height(), current_frame)


    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def close_window(self):
        """Close the window without terminating the process."""
        self.close()

    def eventFilter(self, source, event):
        if source in self.button_images:
            image_path = self.button_images[source]

            if event.type() == QEvent.Enter:
                hover_image_path = image_path.replace(".png", "_down.png")
                hover_image_path = self.resource_path(hover_image_path)
                self.set_image(source, hover_image_path, (1300, 300))

            elif event.type() == QEvent.Leave:
                regular_image_path = self.resource_path(image_path)
                self.set_image(source, regular_image_path, (1300, 300))

        return super().eventFilter(source, event)

    def get_hover_image(self, button):
        """Returns the image name for hover (appends '_down' to the image name)."""
        image_name = self.get_original_image(button)
        return image_name.replace(".png", "_down.png")

    def get_original_image(self, button):
        """Returns the name of the original image associated with the button."""
        if button == self.register_button:
            return config.register_button_image
        return ""

    def run_self_updater(self):
        filename = config.patcher_name
        """Run the self-update executable in a completely separate process."""
        current_hash = hash_file(filename).lower()
        patchlist_json = get_patchlist_json()
        remote_hash = get_stored_patcher_hash(patchlist_json)
        if current_hash == remote_hash:
            QMessageBox.information(self, "Up to Date", "The patcher is up to date!")
        else:
            if not ctypes.windll.shell32.IsUserAnAdmin():
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", config.updater_patch, None, None, 1
                )
            else:
                subprocess.Popen([config.updater_patch])
            sys.exit(0)

    def create_image_button(self, image_path, link):
        """Add a button that fits the image and displays the image full size, centered in the GUI"""

        image_button = QPushButton(self)

        # image_button.setStyleSheet("""
        #    QPushButton {
        #        border-radius: 15px;
        #        border: 2px solid #000;
        #        padding: 0px;
        #    }
        #    QPushButton:hover {
        #        background-color: rgba(0, 0, 0, 0.1);
        #    }
        # """)

        image_label = QLabel(self)

        if image_path.lower().endswith(".gif"):
            movie = QMovie(self.resource_path(image_path))
            image_label.setMovie(movie)
            movie.start()
        else:
            pixmap = QPixmap(image_path)
            image_label.setPixmap(pixmap)

        image_label.setAlignment(Qt.AlignCenter)

        image_button_layout = QVBoxLayout(image_button)
        image_button_layout.setContentsMargins(0, 0, 0, 0)
        image_button_layout.addWidget(image_label)

        image_button.clicked.connect(lambda: webbrowser.open(link))

        image_button.setFixedSize(image_label.sizeHint())

        stacked_layout = QVBoxLayout()
        stacked_layout.setAlignment(Qt.AlignCenter)
        stacked_layout.addWidget(image_button)

        stacked_widget = QWidget(self)
        stacked_widget.setLayout(stacked_layout)
        self.image_slide.addWidget(stacked_widget)

        image_height = image_label.sizeHint().height()
        self.image_slide.setMinimumHeight(image_height)

        return image_button

    def change_slide(self):
        """Manages the display of slides in sequence"""
        if self.image_slide.count() == 0:
            return

        self.current_index = (self.current_index + 1) % self.image_slide.count()

        self.image_slide.setCurrentIndex(self.current_index)

    def run_the_seed(self):
        """Run the .exe program and close the app"""
        try:
            if not ctypes.windll.shell32.IsUserAnAdmin():
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", config.exe_name, config.arguments, None, 1
                )
            else:
                subprocess.Popen([config.exe_name, config.arguments])

            #QApplication.quit()
        except Exception as e:
            print(f"Error running .exe: {e}")

    def on_frame_changed(self, frame_number):
        """Stop the movie when the final frame is reached"""
        current_widget = self.image_slide.currentWidget()
        if isinstance(current_widget, QLabel):
            movie = current_widget.movie()
            if movie and movie.frameCount() - 1 == frame_number:
                movie.stop()
                movie.jumpToFrame(0)

    def open_config(self):
        """Open config.exe using subprocess"""
        subprocess.run([config.config_exe_name])

    def set_label_text(self, text):
        """Set the text for the progress bar or status message"""
        self.progress_bar.setFormat(text)
        if config.update_complete in text:
            self.update_button.clicked.disconnect()
            self.update_button.clicked.connect(self.run_the_seed)

    def set_progress(self, value, file_name):
        """Update the progress bar value and set the text."""
        self.progress_bar.setValue(value)

        self.progress_bar.setFormat(f"{file_name} - {value}%")

    def resource_path(self, relative_path):
        """Manage resource path"""
        relative_path = relative_path.replace("/", "\\")
        if hasattr(sys, "_MEIPASS"):
            full_path = os.path.join(sys._MEIPASS, relative_path)
        else:
            full_path = os.path.join(os.path.abspath("."), relative_path)
        return full_path

    def set_background_image(self, image_path):
        full_path = self.resource_path(image_path)
        pixmap = QPixmap(full_path)
        if pixmap.isNull():
            print(f"Error: Unable to load image '{full_path}'")

        palette = QPalette()
        brush = QBrush(pixmap)
        palette.setBrush(QPalette.Window, brush)
        self.setPalette(palette)
        self.setAutoFillBackground(True)

    def set_image(self, widget, image_path, size):
        """Set an image for the widget"""
        full_path = self.resource_path(image_path)
        pixmap = QPixmap(full_path)
        if pixmap.isNull():
            print(f"Errore: impossibile caricare l'immagine '{full_path}'")
        else:
            if isinstance(widget, QLabel):
                widget.setPixmap(pixmap.scaled(size[0], size[1], Qt.KeepAspectRatio))
            elif isinstance(widget, QPushButton):
                widget.setIcon(
                    QIcon(pixmap.scaled(size[0], size[1], Qt.KeepAspectRatio))
                )

    def emit_update_signal(self):
        """Emit the signal to start the update process"""
        self.start_update_signal.emit()

    def on_file_downloading(self, file_name):
        """Listen to the downloading package name and update the progress bar"""
        self.current_file = file_name
        self.set_progress(0)
        self.set_label_text(f"{config.downloading_text}: {file_name}...")
