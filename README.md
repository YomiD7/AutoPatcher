# Open Source Python AutoPatcher v1.28

## Description

The **AutoPatcher** is a tool designed to facilitate the management and updating of private game clients like Metin2. This system allows for automatic downloading of patches and necessary files to keep the game client up-to-date, without requiring manual updates from the user. The AutoPatcher connects to a server, checks if there are new file versions, and if needed, downloads them to update the client.

![AutoPatcher GIF](https://metin2.download/picture/9mPPIVzfoVrW2tvRO50qeBym7z81qlvA/.gif)

---

## How It Works

### Server Side
- The **Patcher** connects to a server to download a `patchlist.json` file, which contains version information and hashes for the updated files.
- It compares the version and hash of local client files with those in the patchlist. If discrepancies are found, the patcher downloads the required files.
- If the program detects a new version of itself, it will download and restart to apply the update.

### Client Side
- The **Client** uses a `version.pkl` file to track the current version of the client.
- When the user runs the Patcher, it checks the version of the client against the one listed in the `patchlist.json`.
- If updates are available, the Patcher downloads the new .eix/.epk files or other necessary resources.

---

## Project Structure

### Folders

- **images**: Contains the images used in the graphical user interface (GUI).
- **patcher**: Contains the patcher update files, including the `patchlist.json` and the executable file `_TheSeedPatcher.exe`.
- **update**: Folder containing updated files (e.g., .eix/.epk).
- **pack**: Folder on the server that contains the files to be downloaded by the client.

### Key Files

- `main.py`: Contains the main logic of the Patcher.
- `gui.py`: Manages the graphical interface.
- `config.py`: Contains all configurable variables, such as server settings and other customizations.
- `worker.exe`: Handles the automatic update of the Patcher.
- `patchlist.json`: JSON file containing details about the patches to be downloaded.

---

## How to Use

### Server Side

1. **Prepare the Server**:
   - Upload the updated files to the `pack` folder on the server.
   - Upload the `patchlist.json` file that lists the available patches and their version hashes.
   
2. **Run the Server**:
   - Ensure the server is properly configured to serve the necessary files and provide the correct URLs for the clients to download from.
   
### Client Side

1. **Configure the Client**:
   - Edit the `config.py` file to configure the server URL and other settings.
   
2. **Run the Patcher**:
   - Execute the `main.py` file to launch the AutoPatcher. It will connect to the server, check for updates, and download any required files.
   
3. **Automatic Update**:
   - If a new version of the Patcher is detected, the client will automatically download and restart to apply the update.

---

## Video Tutorial

For a step-by-step guide, check out the tutorial video:

[![AutoPatcher Tutorial](https://img.youtube.com/vi/g1YFHWS4hYE/0.jpg)](https://youtu.be/g1YFHWS4hYE)

---

## Requirements

- Python 3.x
- Dependencies: 
   - `requests`
   - `json`
   - `hashlib`
   
   You can install the necessary dependencies using:
   
   ```bash
   pip install -r requirements.txt
