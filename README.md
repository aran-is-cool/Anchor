# Anchor — Find Your Calm
A personalized grounding experience built with Python and Pygame.

**Anchor** is an immersive grounding and relaxation application designed to help users manage stress, regain focus, and find moments of calm.

Built with **Python and Pygame**, Anchor combines interactive exercises, calming animations, ambient soundscapes, and personalized experiences.

## Features

- **Breathe:** Guided breathing with synchronized cloud animations and audio cues.
- **Release:** Interactive stress-release exercises.
- **Watch:** Calming visual experiences.
- **Stay:** A peaceful environment for mindfulness.
- **Check-in:** Reflect on your emotional well-being.
- **Progress:** Track your activity and progress.
- **Settings:** Personalize your experience.

## Installation and Setup

Anchor is a desktop application intended for Windows, macOS, and Linux. It requires Python and its supporting libraries.

### 1. Install Python

Download Python 3 from:

https://www.python.org/downloads/

**Windows**
- Download the Windows installer.
- During installation, enable the option to add Python to PATH if offered.

**macOS**
- Download and install the macOS version of Python.

**Linux (Ubuntu/Debian)**
- Python may already be installed.
- If necessary, install Python using:

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

Verify installation:

Windows:
```bash
py --version
```

macOS/Linux:
```bash
python3 --version
```

### 2. Download Anchor

1. Open this GitHub repository.
2. Click the green **Code** button.
3. Select **Download ZIP**.
4. Extract the ZIP file.
5. Locate the `anchor_project` folder inside the extracted repository.

Keep the project's Python files, images, audio, and other assets in their original folder structure.

### 3. Install Dependencies

Open Terminal (macOS/Linux) or PowerShell (Windows).

Navigate to the downloaded `anchor_project` directory.

**Windows:**
```powershell
cd "C:\path\to\anchor_project"
```

**macOS/Linux:**
```bash
cd "/path/to/anchor_project"
```

Replace the example path with the actual location of the folder.

Create a virtual environment:

**Windows:**
```powershell
py -m venv .venv
```

**macOS/Linux:**
```bash
python3 -m venv .venv
```

Install Pygame inside that environment:

**Windows:**
```powershell
.\.venv\Scripts\python.exe -m pip install pygame
```

**macOS/Linux:**
```bash
.venv/bin/python -m pip install pygame
```

If a `requirements.txt` file is provided, install all dependencies listed in it instead:

**Windows:**
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**macOS/Linux:**
```bash
.venv/bin/python -m pip install -r requirements.txt
```

### 4. Run Anchor

From inside the `anchor_project` folder, launch the application.

**Windows:**
```powershell
.\.venv\Scripts\python.exe main.py
```

**macOS:**
```bash
.venv/bin/python main.py
```

**Linux:**
```bash
.venv/bin/python main.py
```

The Anchor application should launch in a new window if all required dependencies and assets are available.

**Note:** These examples assume the main application file is named `main.py`. Replace it with the actual entry-point filename if different.

## Troubleshooting

**ModuleNotFoundError**

A required Python library is missing. Install the dependencies listed in `requirements.txt`, if available.

**Images or sounds are missing**

Make sure the complete `anchor_project` folder was downloaded and that its directory structure remains unchanged.

**Python cannot be found**

Reinstall Python or confirm that it is correctly configured for your operating system.

**Application does not launch**

Check the error message in Terminal or PowerShell. Some operating systems may require additional audio or graphics support.

## Compatibility

| Operating System | Installation Method |
|---|---|
| Windows 10/11 | Python + Pygame |
| macOS | Python + Pygame |
| Linux | Python + Pygame |

**Compatibility note:** The commands above describe how to install and attempt to run Anchor on these systems. Full compatibility has not yet been verified on all three operating systems.

## Technologies Used

- Python
- Pygame
- Custom visual animations
- Audio-based relaxation experiences
- Local offline data storage

## Congressional App Challenge 2026

Anchor was developed as a student project for the **2026 Congressional App Challenge**.

*“I didn't want to build another app that demands your attention. I wanted to build one that helps you regain it. It should show 'Elegance'”*
