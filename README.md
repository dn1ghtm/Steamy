# Steam Terminal Launcher

A simple terminal-based launcher for Steam games that allows you to quickly launch your installed Steam games from the command line.

## Features

- Automatically detects installed Steam games
- Saves Steam installation path for future use
- Colorful terminal interface
- Simple game selection menu
- Supports multiple Steam library folders

## Requirements

- Python 3.6 or higher
- Steam installed on your system
- Windows operating system

## Installation

1. Clone or download this repository
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Run the script:
   ```
   python steam_launcher.py
   ```

2. On first run, you'll be prompted to enter your Steam installation path
   (typically `C:\Program Files (x86)\Steam`)

3. The launcher will scan for installed games and display them in a numbered list

4. Enter the number of the game you want to launch, or 'q' to quit

## How it Works

The launcher reads Steam's library folders and app manifest files to find all installed games. It then creates a simple terminal interface where you can select and launch games. The Steam installation path is saved in a `steam_config.json` file for future use. 