import os
import json
import vdf
import subprocess
import msvcrt
import sys
import ctypes
from pathlib import Path
from colorama import init, Fore, Style

# Initialize colorama for Windows support
init()

def set_console_size(width, height):
    """Set the console window size"""
    try:
        # Get handle to console window
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            # Get current window size
            rect = ctypes.wintypes.RECT()
            ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
            
            # Calculate new size
            new_width = rect.right - rect.left
            new_height = rect.bottom - rect.top
            
            # Set new size
            ctypes.windll.user32.SetWindowPos(hwnd, 0, rect.left, rect.top, 
                                           width, height, 0x0004)
            return True
    except Exception as e:
        print(f"{Fore.RED}Error setting console size: {str(e)}{Style.RESET_ALL}")
    return False

def get_config_path():
    """Get the correct path for the config file whether running as script or executable"""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        base_path = os.path.dirname(sys.executable)
        config_path = os.path.join(base_path, 'steam_config.json')
        print(f"{Fore.CYAN}Running as executable. Config path: {config_path}{Style.RESET_ALL}")
        return config_path
    else:
        # Running as script
        config_path = "steam_config.json"
        print(f"{Fore.CYAN}Running as script. Config path: {config_path}{Style.RESET_ALL}")
        return config_path

class SteamLauncher:
    def __init__(self):
        self.config_file = get_config_path()
        print(f"{Fore.CYAN}Initializing SteamLauncher with config: {self.config_file}{Style.RESET_ALL}")
        self.config = self.load_config()
        self.library_paths = self.config.get('library_paths', [])
        self.current_user = self.config.get('current_user', '')
        
    def load_config(self):
        """Load configuration from file"""
        default_config = {
            "library_paths": [],
            "current_user": ""
        }
        
        try:
        if os.path.exists(self.config_file):
                print(f"{Fore.GREEN}Loading existing config from: {self.config_file}{Style.RESET_ALL}")
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    print(f"{Fore.GREEN}Loaded config successfully{Style.RESET_ALL}")
                    return config
            else:
                print(f"{Fore.YELLOW}Config file not found. Creating new config at: {self.config_file}{Style.RESET_ALL}")
                # Ensure the directory exists
                os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
                # Create the config file with default values
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=4)
                print(f"{Fore.GREEN}Created new config file{Style.RESET_ALL}")
                return default_config
        except Exception as e:
            print(f"{Fore.RED}Error loading config: {str(e)}{Style.RESET_ALL}")
            return default_config

    def save_config(self):
        """Save configuration to file"""
        try:
            print(f"{Fore.CYAN}Saving config to: {self.config_file}{Style.RESET_ALL}")
            # Ensure the directory exists
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4)
            print(f"{Fore.GREEN}Config saved successfully{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error saving config: {str(e)}{Style.RESET_ALL}")

    def find_steam_libraries(self):
        """Try to find Steam libraries in common locations"""
        common_paths = []
        # Add paths for all possible drives
        for drive in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            steam_paths = [
                os.path.normpath(f"{drive}:{os.sep}Steam{os.sep}steamapps"),
                os.path.normpath(f"{drive}:{os.sep}Program Files (x86){os.sep}Steam{os.sep}steamapps"),
                os.path.normpath(f"{drive}:{os.sep}Program Files{os.sep}Steam{os.sep}steamapps")
            ]
            for path in steam_paths:
                normalized_path = os.path.normpath(path)
                print(f"{Fore.CYAN}Checking Steam folder: {normalized_path}{Style.RESET_ALL}")
                if os.path.exists(os.path.dirname(normalized_path)):  # Check if Steam folder exists
                    print(f"{Fore.GREEN}Found Steam folder: {os.path.dirname(normalized_path)}{Style.RESET_ALL}")
                    if os.path.exists(normalized_path):  # Check if steamapps folder exists
                        print(f"{Fore.GREEN}Found Steam library: {normalized_path}{Style.RESET_ALL}")
                        common_paths.append(normalized_path)
                    else:
                        print(f"{Fore.YELLOW}Steam folder exists but no steamapps folder found at: {normalized_path}{Style.RESET_ALL}")
        
        if not common_paths:
            print(f"{Fore.RED}No Steam libraries found in common locations.{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Please check if Steam is installed and note its location.{Style.RESET_ALL}")
            
            # Try to find steam.exe to help locate the installation
            for drive in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                steam_exe_paths = [
                    os.path.normpath(f"{drive}:{os.sep}Steam{os.sep}steam.exe"),
                    os.path.normpath(f"{drive}:{os.sep}Program Files (x86){os.sep}Steam{os.sep}steam.exe"),
                    os.path.normpath(f"{drive}:{os.sep}Program Files{os.sep}Steam{os.sep}steam.exe")
                ]
                for exe_path in steam_exe_paths:
                    if os.path.exists(exe_path):
                        print(f"{Fore.GREEN}Found Steam executable at: {exe_path}{Style.RESET_ALL}")
                        steam_folder = os.path.dirname(exe_path)
                        steamapps_path = os.path.join(steam_folder, "steamapps")
                        print(f"{Fore.YELLOW}Expected steamapps folder should be at: {steamapps_path}{Style.RESET_ALL}")
        
        return common_paths

    def get_steam_users(self):
        """Get list of Steam users from userdata folder"""
        users = []
        for library in self.library_paths:
            # Go up one level from steamapps to get to Steam folder
            steam_folder = os.path.dirname(library)
            userdata_path = os.path.join(steam_folder, "userdata")
            
            if os.path.exists(userdata_path):
                for user_id in os.listdir(userdata_path):
                    if user_id.isdigit():
                        # Try to get username from localconfig.vdf
                        localconfig_path = os.path.join(userdata_path, user_id, "config", "localconfig.vdf")
                        if os.path.exists(localconfig_path):
                            try:
                                with open(localconfig_path, 'r', encoding='utf-8') as f:
                                    config = vdf.load(f)
                                    username = config.get('UserLocalConfigStore', {}).get('friends', {}).get('PersonaName', f'User {user_id}')
                                    users.append({'id': user_id, 'name': username})
                            except:
                                users.append({'id': user_id, 'name': f'User {user_id}'})
        return users

    def get_key(self):
        """Get a single keypress without requiring Enter"""
        key = msvcrt.getch()
        if key == b'\xe0':  # Arrow key prefix
            key = msvcrt.getch()
            if key == b'H':  # Up arrow
                return 'UP'
            elif key == b'P':  # Down arrow
                return 'DOWN'
            elif key == b'K':  # Left arrow
                return 'LEFT'
            elif key == b'M':  # Right arrow
                return 'RIGHT'
        return key.decode('utf-8').upper()

    def get_number_input(self, max_value):
        """Get numeric input without requiring Enter"""
        number = ""
        while True:
            key = msvcrt.getch().decode('utf-8')
            if key == '\r':  # Enter key
                break
            elif key == '\b':  # Backspace
                if number:
                    number = number[:-1]
                    msvcrt.putch(b'\b')
                    msvcrt.putch(b' ')
                    msvcrt.putch(b'\b')
            elif key.isdigit():
                number += key
                msvcrt.putch(key.encode())
        print()  # New line after input
        return number

    def settings_menu(self):
        """Display and handle settings menu"""
        selected_option = 0
        options = [
            "Manage Library Paths",
            "Select Steam User",
            "Back to Main Menu"
        ]
        
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            print(f"{Fore.CYAN}╔{'═' * 118}╗")
            print(f"║{' ' * 118}║")
            print(f"║{' ' * 45}{Fore.WHITE}SETTINGS MENU{Style.RESET_ALL}{' ' * 55}║")
            print(f"║{' ' * 118}║")
            print(f"╠{'═' * 118}╣")
            
            for i, option in enumerate(options):
                if i == selected_option:
                    print(f"║ {Fore.WHITE}>{Style.RESET_ALL} {option}{' ' * (110 - len(option))}║")
                else:
                    print(f"║   {option}{' ' * (110 - len(option))}║")
            
            print(f"╚{'═' * 118}╝")
            print(f"\n{Fore.YELLOW}Use arrow keys to navigate, Enter to select: {Style.RESET_ALL}", end='', flush=True)
            
            key = self.get_key()
            if key == 'UP':
                selected_option = (selected_option - 1) % len(options)
            elif key == 'DOWN':
                selected_option = (selected_option + 1) % len(options)
            elif key == '\r':  # Enter key
                if selected_option == 0:
                self.manage_library_paths()
                elif selected_option == 1:
                self.select_steam_user()
                elif selected_option == 2:
                break

    def manage_library_paths(self):
        """Manage Steam library paths"""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            print(f"{Fore.CYAN}╔{'═' * 78}╗")
            print(f"║{' ' * 78}║")
            print(f"║{' ' * 25}{Fore.WHITE}LIBRARY PATH MANAGEMENT{Style.RESET_ALL}{' ' * 30}║")
            print(f"║{' ' * 78}║")
            print(f"╠{'═' * 78}╣")
            
            # Show current paths with better formatting
            print(f"║ {Fore.YELLOW}Current Library Paths:{Style.RESET_ALL}")
            if self.library_paths:
                for idx, path in enumerate(self.library_paths, 1):
                    normalized_path = os.path.normpath(path)
                    print(f"║ {Fore.WHITE}{idx}. {normalized_path}{Style.RESET_ALL}")
            else:
                print(f"║ {Fore.RED}No paths configured{Style.RESET_ALL}")
            
            print(f"╠{'═' * 78}╣")
            print(f"║ {Fore.WHITE}1{Style.RESET_ALL} - Add new path")
            print(f"║ {Fore.WHITE}2{Style.RESET_ALL} - Remove path")
            print(f"║ {Fore.WHITE}3{Style.RESET_ALL} - Auto-detect paths")
            print(f"║ {Fore.WHITE}4{Style.RESET_ALL} - Back")
            print(f"╚{'═' * 78}╝")
            
            print(f"\n{Fore.YELLOW}Press a key: {Style.RESET_ALL}", end='', flush=True)
            choice = self.get_key()
            
            if choice == '1':
                print(f"\n{Fore.CYAN}Enter new library path (e.g., D:{os.sep}Steam{os.sep}steamapps):{Style.RESET_ALL}")
                path = input().strip().strip('"').strip("'")
                
                # Convert to Path object for better path handling
                path_obj = Path(path)
                normalized_path = str(path_obj.resolve())  # Get absolute path
                
                # Debug information
                print(f"\n{Fore.YELLOW}Path Information:{Style.RESET_ALL}")
                print(f"Original path: {path}")
                print(f"Path object: {path_obj}")
                print(f"Absolute path: {normalized_path}")
                print(f"Path separators: {os.sep}")
                print(f"Drive: {path_obj.drive}")
                print(f"Parent: {path_obj.parent}")
                print(f"Name: {path_obj.name}")
                
                try:
                    # First check if the drive exists
                    drive_exists = os.path.exists(path_obj.drive + os.sep)
                    print(f"Drive exists: {drive_exists}")
                    
                    if not drive_exists:
                        print(f"{Fore.RED}Drive {path_obj.drive} does not exist.{Style.RESET_ALL}")
                        print("\nPress any key to continue...")
                        self.get_key()
                        continue
                    
                    # Check each part of the path
                    current_path = path_obj.drive + os.sep
                    path_parts = path_obj.parts[1:]  # Skip drive
                    
                    for part in path_parts:
                        current_path = os.path.join(current_path, part)
                        exists = os.path.exists(current_path)
                        print(f"Checking {current_path}: {'Exists' if exists else 'Does not exist'}")
                        
                        if not exists:
                            print(f"{Fore.RED}Path does not exist: {current_path}{Style.RESET_ALL}")
                            print(f"{Fore.YELLOW}Please verify the path and try again.{Style.RESET_ALL}")
                            print("\nPress any key to continue...")
                            self.get_key()
                            return
                    
                    # If we get here, the full path exists
                    print(f"{Fore.GREEN}Full path exists: {normalized_path}{Style.RESET_ALL}")
                    
                    # Check if it's a directory
                    if not os.path.isdir(normalized_path):
                        print(f"{Fore.RED}Path exists but is not a directory: {normalized_path}{Style.RESET_ALL}")
                        print("\nPress any key to continue...")
                        self.get_key()
                        return
                    
                    # Check if we can list contents
                    try:
                        contents = os.listdir(normalized_path)
                        print(f"{Fore.GREEN}Directory is accessible{Style.RESET_ALL}")
                        print(f"Contents: {contents}")
                    except PermissionError:
                        print(f"{Fore.RED}Permission denied. Try running as administrator.{Style.RESET_ALL}")
                        print("\nPress any key to continue...")
                        self.get_key()
                        return
                    
                    # Check for .acf files
                    has_acf = any(f.endswith('.acf') for f in contents)
                    print(f"Contains .acf files: {has_acf}")
                    
                    if has_acf:
                        if normalized_path not in self.library_paths:
                            self.library_paths.append(normalized_path)
                        self.config['library_paths'] = self.library_paths
                            try:
                        self.save_config()
                        print(f"{Fore.GREEN}Path added successfully!{Style.RESET_ALL}")
                            except Exception as e:
                                print(f"{Fore.RED}Error saving config: {str(e)}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.RED}Path already exists in the list.{Style.RESET_ALL}")
                else:
                        print(f"{Fore.RED}Directory does not contain Steam game files (.acf files){Style.RESET_ALL}")
                    
                except Exception as e:
                    print(f"{Fore.RED}Error checking path: {str(e)}{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}Please verify the path and try again.{Style.RESET_ALL}")
                
                print("\nPress any key to continue...")
                self.get_key()
            
            elif choice == '2':
                if not self.library_paths:
                    print(f"{Fore.RED}No paths to remove.{Style.RESET_ALL}")
                    continue
                    
                print(f"{Fore.YELLOW}Enter the number of the path to remove: {Style.RESET_ALL}", end='', flush=True)
                number = self.get_number_input(len(self.library_paths))
                try:
                    idx = int(number)
                    if 1 <= idx <= len(self.library_paths):
                        removed = self.library_paths.pop(idx - 1)
                        self.config['library_paths'] = self.library_paths
                        self.save_config()
                        print(f"{Fore.GREEN}Removed: {removed}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.RED}Invalid number.{Style.RESET_ALL}")
                except ValueError:
                    print(f"{Fore.RED}Please enter a valid number.{Style.RESET_ALL}")
            
            elif choice == '3':
                auto_paths = self.find_steam_libraries()
                if auto_paths:
                    print(f"{Fore.GREEN}Found Steam libraries:{Style.RESET_ALL}")
                    for path in auto_paths:
                        if path not in self.library_paths:
                            self.library_paths.append(path)
                            print(f"{Fore.WHITE}Added: {path}{Style.RESET_ALL}")
                    self.config['library_paths'] = self.library_paths
                    self.save_config()
                else:
                    print(f"{Fore.RED}No Steam libraries found.{Style.RESET_ALL}")
                print("\nPress any key to continue...")
                self.get_key()
            
            elif choice == '4':
                break
            else:
                print(f"{Fore.RED}Invalid choice.{Style.RESET_ALL}")

    def select_steam_user(self):
        """Select Steam user"""
        selected_option = 0
        users = self.get_steam_users()
        if not users:
            print(f"{Fore.RED}No Steam users found.{Style.RESET_ALL}")
            return

        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            print(f"{Fore.CYAN}╔{'═' * 118}╗")
            print(f"║{' ' * 118}║")
            print(f"║{' ' * 45}{Fore.WHITE}SELECT STEAM USER{Style.RESET_ALL}{' ' * 55}║")
            print(f"║{' ' * 118}║")
            print(f"╠{'═' * 118}╣")
            
            for idx, user in enumerate(users):
                if idx == selected_option:
                    print(f"║ {Fore.WHITE}>{Style.RESET_ALL} {user['name']}{' ' * (110 - len(user['name']))}║")
                else:
                    print(f"║   {user['name']}{' ' * (110 - len(user['name']))}║")
            
            print(f"╚{'═' * 118}╝")
            print(f"\n{Fore.YELLOW}Use arrow keys to navigate, Enter to select: {Style.RESET_ALL}", end='', flush=True)
            
            key = self.get_key()
            if key == 'UP':
                selected_option = (selected_option - 1) % len(users)
            elif key == 'DOWN':
                selected_option = (selected_option + 1) % len(users)
            elif key == '\r':  # Enter key
                self.current_user = users[selected_option]['id']
                self.config['current_user'] = self.current_user
                self.save_config()
                print(f"\n{Fore.GREEN}Selected user: {users[selected_option]['name']}{Style.RESET_ALL}")
                print("\nPress any key to continue...")
                self.get_key()
                break

    def get_installed_games(self):
        """Get list of installed Steam games"""
        if not self.library_paths:
            print(f"{Fore.RED}No library paths configured. Please add paths in settings.{Style.RESET_ALL}")
            return []

        games = []
        for library in self.library_paths:
            print(f"{Fore.CYAN}Scanning library: {library}{Style.RESET_ALL}")
            # Read appmanifest files
            for file in os.listdir(library):
                if file.startswith("appmanifest_") and file.endswith(".acf"):
                    manifest_path = os.path.join(library, file)
                    try:
                        with open(manifest_path, 'r', encoding='utf-8') as f:
                            manifest = vdf.load(f)
                            app_data = manifest.get('AppState', {})
                            games.append({
                                'name': app_data.get('name', 'Unknown Game'),
                                'appid': app_data.get('appid'),
                                'install_dir': app_data.get('installdir', '')
                            })
                    except Exception as e:
                        print(f"{Fore.RED}Error reading {file}: {str(e)}{Style.RESET_ALL}")

        return sorted(games, key=lambda x: x['name'])

    def launch_game(self, app_id):
        """Launch a Steam game by its AppID"""
        # Try to find steam.exe in common locations
        steam_paths = []
        for drive in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            steam_paths.extend([
                os.path.normpath(f"{drive}:{os.sep}Steam{os.sep}steam.exe"),
                os.path.normpath(f"{drive}:{os.sep}Program Files (x86){os.sep}Steam{os.sep}steam.exe"),
                os.path.normpath(f"{drive}:{os.sep}Program Files{os.sep}Steam{os.sep}steam.exe")
            ])
        
        steam_exe = None
        for path in steam_paths:
            normalized_path = os.path.normpath(path)
            if os.path.exists(normalized_path):
                steam_exe = normalized_path
                print(f"{Fore.GREEN}Found Steam executable at: {normalized_path}{Style.RESET_ALL}")
                break
                
        if not steam_exe:
            print(f"{Fore.RED}Could not find Steam executable. Please make sure Steam is installed.{Style.RESET_ALL}")
            return

        # Add user selection to launch command if a user is selected
        launch_command = [steam_exe, f"steam://rungameid/{app_id}"]
        if self.current_user:
            launch_command.append(f"-login {self.current_user}")

        print(f"{Fore.CYAN}Launching with command: {' '.join(launch_command)}{Style.RESET_ALL}")
        subprocess.Popen(launch_command)
        print(f"{Fore.GREEN}Launching game...{Style.RESET_ALL}")

    def display_menu(self, games):
        """Display the game selection menu"""
        # Set console size to match content
        set_console_size(1200, 600)  # Wider window
        
        selected_action = 0
        quick_actions = ["Settings", "Refresh", "Quit"]
        
        while True:
            # Clear screen and show header
            os.system('cls' if os.name == 'nt' else 'clear')
            
            # Modern header with clean design
            print(f"{Fore.CYAN}╔{'═' * 118}╗")
            print(f"║{' ' * 118}║")
            print(f"║{' ' * 45}{Fore.WHITE}STEAM GAME LAUNCHER{Style.RESET_ALL}{' ' * 55}║")
            print(f"║{' ' * 118}║")
            print(f"╠{'═' * 118}╣")
            
            # Status bar with user and library info
            if self.current_user:
                users = self.get_steam_users()
                current_user_name = next((user['name'] for user in users if user['id'] == self.current_user), 'Unknown User')
                print(f"║ {Fore.YELLOW}User:{Style.RESET_ALL} {current_user_name:<30} {Fore.YELLOW}Libraries:{Style.RESET_ALL} {len(self.library_paths):<5} ║")
            else:
                print(f"║ {Fore.YELLOW}No User Selected{' ' * 20}Libraries:{Style.RESET_ALL} {len(self.library_paths):<5} ║")
            print(f"╠{'═' * 118}╣")
            
            # Games list with modern styling
            if games:
                print(f"║ {Fore.YELLOW}Installed Games{' ' * 100}║")
                print(f"╠{'─' * 118}╣")
                
                # Show games in a 3-column grid format
                for i in range(0, len(games), 3):
                    game1 = games[i]
                    game2 = games[i + 1] if i + 1 < len(games) else None
                    game3 = games[i + 2] if i + 2 < len(games) else None
                    
                    if game2 and game3:
                        print(f"║ {Fore.WHITE}{i+1:2d}. {game1['name'][:35]:<35} {i+2:2d}. {game2['name'][:35]:<35} {i+3:2d}. {game3['name'][:35]:<35} ║")
                    elif game2:
                        print(f"║ {Fore.WHITE}{i+1:2d}. {game1['name'][:35]:<35} {i+2:2d}. {game2['name'][:35]:<35} {' ' * 40} ║")
                    else:
                        print(f"║ {Fore.WHITE}{i+1:2d}. {game1['name'][:35]:<35} {' ' * 75} ║")
                
                # Add padding if needed
                if len(games) % 3 != 0:
                    print(f"║ {' ' * 118} ║")
            else:
                print(f"║ {Fore.RED}No games found. Please check your library paths in settings.{Style.RESET_ALL}{' ' * 20} ║")
                print(f"║ {' ' * 118} ║")
            
            # Modern quick actions bar with arrow navigation
            print(f"╠{'═' * 118}╣")
            print(f"║ {Fore.YELLOW}Quick Actions:{Style.RESET_ALL}{' ' * 100}║")
            
            # Show quick actions with selection indicator
            actions_text = ""
            for i, action in enumerate(quick_actions):
                if i == selected_action:
                    actions_text += f"{Fore.WHITE}>{Style.RESET_ALL} {action}  |  "
                else:
                    actions_text += f"{action}  |  "
            actions_text = actions_text.rstrip("|  ")  # Remove trailing separator
            print(f"║ {actions_text}{' ' * (110 - len(actions_text))}║")
            print(f"╚{'═' * 118}╝")
            
            # Get user input with modern prompt
            print(f"\n{Fore.YELLOW}Use arrow keys for quick actions, number for games: {Style.RESET_ALL}", end='', flush=True)
            
            # Handle input
            while True:
                key = self.get_key()
                if key in ['LEFT', 'RIGHT']:
                    if key == 'LEFT' and selected_action > 0:
                        selected_action -= 1
                    elif key == 'RIGHT' and selected_action < len(quick_actions) - 1:
                        selected_action += 1
                break
                elif key == '\r':  # Enter key
                    if selected_action == 0:  # Settings
                self.settings_menu()
                games = self.get_installed_games()
                    elif selected_action == 1:  # Refresh
                games = self.get_installed_games()
                    elif selected_action == 2:  # Quit
                        return
                    break
                elif key.isdigit():
                    # Handle game number input
                    number = key + self.get_number_input(len(games))
                try:
                    game_choice = int(number)
                    if 1 <= game_choice <= len(games):
                        selected_game = games[game_choice - 1]
                        self.launch_game(selected_game['appid'])
                    else:
                        print(f"{Fore.RED}Invalid game number.{Style.RESET_ALL}")
                except ValueError:
                    print(f"{Fore.RED}Invalid input. Please enter a valid game number.{Style.RESET_ALL}")
                    break

def main():
    try:
        # Set initial console size
        set_console_size(800, 400)
        
        print(f"{Fore.YELLOW}Initializing Steam Launcher...{Style.RESET_ALL}")
    launcher = SteamLauncher()
        print(f"{Fore.GREEN}Steam Launcher initialized successfully.{Style.RESET_ALL}")
        
        print(f"{Fore.YELLOW}Scanning for installed games...{Style.RESET_ALL}")
    games = launcher.get_installed_games()
        print(f"{Fore.GREEN}Found {len(games)} games.{Style.RESET_ALL}")
        
        print(f"{Fore.YELLOW}Starting main menu...{Style.RESET_ALL}")
    launcher.display_menu(games)
    except Exception as e:
        print(f"\n{Fore.RED}Error occurred: {str(e)}{Style.RESET_ALL}")
        print(f"{Fore.RED}Please check if you have the required permissions and Steam is installed.{Style.RESET_ALL}")
        print("\nPress any key to exit...")
        msvcrt.getch()

if __name__ == "__main__":
    main() 