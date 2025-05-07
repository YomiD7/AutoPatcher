from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication
from PyQt5 import QtCore

import sys
import json
import urllib.request
import os
import hashlib
import pickle
import config
import cloudscraper
from gui import UpdateWindow  # Import the GUI


class UpdateThread(QThread):
    progress_changed = QtCore.pyqtSignal(int, str)
    finished = pyqtSignal()
    file_downloading = pyqtSignal(str)

    def __init__(self, client_version, patchlist_url, pack_url, pack_path, exe_folder):
        super().__init__()
        self.client_version = client_version
        self.patchlist_url = patchlist_url
        self.pack_url = pack_url
        self.pack_path = pack_path
        self.exe_folder = exe_folder
        self.running = True

    def run(self):
        try:
            patchlist = self.download_patchlist(self.patchlist_url)
            if patchlist and self.running:
                patch_key = self.get_patch_key(patchlist)
                if not patch_key:
                    print("No valid patch key found in the patchlist.")
                    self.finished.emit()
                    return

                server_version = patch_key
                if self.client_version == server_version:
                    if self.check_files_integrity(patchlist, patch_key):
                        self.finished.emit()
                        return

                total_files, total_size = self.calculate_totals(patchlist, patch_key)
                self.download_files(patchlist, patch_key, total_size)
                if self.running:
                    self.update_version_file(server_version)

            if self.running:
                self.finished.emit()
        except Exception as e:
            print(f"Error during update: {e}")
            self.finished.emit()

    def stop(self):
        self.running = False

    def get_patch_key(self, patchlist):
        """Find the most recent patch key dynamically."""
        patch_keys = [key for key in patchlist.keys() if key.startswith("patch_")]
        if not patch_keys:
            return None

        patch_keys.sort(key=lambda x: float(x.split("_")[1]), reverse=True)
        return patch_keys[0]

    def calculate_totals(self, patchlist, patch_key):
        """Calculate the total number of files and their size."""
        total_files = len(patchlist[patch_key]) + (1 if "exe" in patchlist else 0)
        total_size = sum(
            file_info["size"]
            for patch in patchlist[patch_key]
            for file_info in patch.values()
        )
        return total_files, total_size

    

    def download_patchlist(self, patchlist_url):
        
        """Download the patchlist file bypassing Cloudflare."""
        scraper = cloudscraper.create_scraper()
        try:
            response = scraper.get(patchlist_url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Failed to download patchlist: {e}")
            return None


    def check_files_integrity(self, patchlist, patch_key):
        """Check if the local files match the hashes from the server."""
        try:
            # Inizia il processo di checking dei pacchetti
            for patch in patchlist[patch_key]:
                for file, file_info in patch.items():
                    local_path = os.path.join(self.pack_path, file)
                    
                    # Aggiungi nome del file al messaggio di progresso
                    self.progress_changed.emit(0, f"Checking {file}...")  # Mostra il nome del file nella GUI
                    
                    if not os.path.exists(local_path):
                        print(f"Missing file: {local_path}")
                        return False
                    if not self.verify_file_hash(local_path, file_info["hash"]):
                        print(f"Hash mismatch for {local_path}")
                        return False
            for exe in patchlist.get("exe", []):
                local_path = os.path.join(self.exe_folder, exe)
                self.progress_changed.emit(0, f"Checking {exe}...")  # Nome del file exe in controllo
                
                if not os.path.exists(local_path):
                    print(f"Missing executable: {local_path}")
                    return False
            return True
        except Exception as e:
            print(f"Error during file integrity check: {e}")
            return False

    def verify_file_hash(self, file_path, expected_hash):
        """Verify the hash of a file against the expected value."""
        try:
            hasher = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest() == expected_hash
        except Exception as e:
            print(f"Error calculating hash for {file_path}: {e}")
            return False

    def update_version_file(self, version, version_file=config.version_file_name):
        """Update the version file with the new version."""
        try:
            with open(version_file, "wb") as f:
                pickle.dump(version, f)
        except Exception as e:
            print(f"Error updating version file: {e}")

    def download_files(self, patchlist, patch_key, total_size):
        """Handle downloading all required files."""
        self.download_patch_files(patchlist, patch_key, total_size)
        if self.running:
            self.download_exe(patchlist, total_size)

    def download_patch_files(self, patchlist, patch_key, total_size):
        """Download patch files only if they are missing or mismatched."""
        for patch in patchlist[patch_key]:
            for file, file_info in patch.items():
                local_path = os.path.join(self.pack_path, file)
                if not os.path.exists(local_path) or not self.verify_file_hash(
                    local_path, file_info["hash"]
                ):
                    url = f"{self.pack_url}/{file}"
                    self.download_file(
                        url, local_path, file_info["size"], total_size, file
                    )

    def download_exe(self, patchlist, total_size):
        """Download executable files only if they are missing or mismatched."""
        if "exe" in patchlist:
            for exe_file, file_info in patchlist["exe"].items():
                exe_local_path = os.path.join(self.exe_folder, exe_file)
                if not os.path.exists(exe_local_path) or not self.verify_file_hash(
                    exe_local_path, file_info["hash"]
                ):
                    exe_url = f"{self.pack_url}/{exe_file}"
                    self.download_file(
                        exe_url, exe_local_path, file_info["size"], total_size, exe_file
                    )

    def download_file(self, url, local_path, file_size, total_size, file_name):
        """Download a single file using cloudscraper and report progress."""
        try:
            self.current_file = file_name
            self.file_downloading.emit(file_name)

            scraper = cloudscraper.create_scraper()
            response = scraper.get(url, stream=True)
            response.raise_for_status()

            with open(local_path, "wb") as file:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if not self.running:
                        return  # Interrompi il download se il processo ? fermato
                    if chunk:
                        file.write(chunk)
                        downloaded += len(chunk)
                        progress = int((downloaded / file_size) * 100)
                        self.progress_changed.emit(progress, file_name)
        except Exception as e:
            print(f"Error downloading {url}: {e}")


def start_update(client_version, patchlist_url, pack_url, pack_path, exe_folder):
    app = QApplication(sys.argv)
    window = UpdateWindow()
    window.show()

    thread = UpdateThread(
        client_version, patchlist_url, pack_url, pack_path, exe_folder
    )
    thread.progress_changed.connect(window.set_progress)
    thread.file_downloading.connect(window.set_label_text)
    thread.finished.connect(lambda: window.set_label_text(config.update_complete))

    window.start_update_signal.connect(thread.start)

    app.aboutToQuit.connect(thread.stop)
    app.aboutToQuit.connect(thread.wait)

   # sys.exit(app.exec_())


version_file = config.version_file_name


if __name__ == "__main__":

    if not os.path.exists(config.pack_path):
        os.makedirs(config.pack_path)
    if not os.path.exists(version_file):
        with open(version_file, "wb") as f:
            pickle.dump("1.0", f)
        client_version = "1.0"

    else:
        with open(version_file, "rb") as f:
            client_version = pickle.load(f)
        print(f"Client Version: {client_version}")

    patchlist_url = config.patchlist_url
    pack_url = config.pack_url
    pack_path = config.pack_path
    exe_folder = "."

    app = QApplication(sys.argv)
    window = UpdateWindow()
    window.show()

    thread = UpdateThread(
        client_version, patchlist_url, pack_url, pack_path, exe_folder
    )
    thread.progress_changed.connect(window.set_progress)
    thread.file_downloading.connect(window.set_label_text)
    thread.finished.connect(lambda: window.set_label_text(config.update_complete))
    window.start_update_signal.connect(thread.start)

    if config.auto_updater:
        window.start_update_signal.emit()

    app.aboutToQuit.connect(thread.stop)
    app.aboutToQuit.connect(thread.wait)

    sys.exit(app.exec_())



