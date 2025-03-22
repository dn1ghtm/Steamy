import os
import json
import vdf
import subprocess
import msvcrt
import sys
import ctypes
import psutil
import time
import winreg
from datetime import datetime, timedelta
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

def set_console_title(title):
    """Set the console window title"""
    try:
        ctypes.windll.kernel32.SetConsoleTitleW(title)
        return True
    except Exception as e:
        print(f"{Fore.RED}Error setting console title: {str(e)}{Style.RESET_ALL}")
    return False

def get_documents_path():
    """Get the path to the user's Documents folder"""
    try:
        import ctypes.wintypes
        CSIDL_PERSONAL = 5  # Documents folder
        SHGFP_TYPE_CURRENT = 0  # Get current path rather than default
        buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
        ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf)
        return buf.value
    except Exception as e:
        print(f"{Fore.RED}Error getting Documents path: {str(e)}{Style.RESET_ALL}")
        return os.path.expanduser("~/Documents")

def get_config_path():
    """Get the correct path for the config file in Documents/Steamy folder"""
    try:
        # Get Documents folder path
        documents_path = get_documents_path()
        # Create Steamy folder path
        steamy_folder = os.path.join(documents_path, "Steamy")
        # Create the folder if it doesn't exist
        os.makedirs(steamy_folder, exist_ok=True)
        # Config file path
        config_path = os.path.join(steamy_folder, "steamy_config.json")
        print(f"{Fore.CYAN}Config path: {config_path}{Style.RESET_ALL}")
        return config_path
    except Exception as e:
        print(f"{Fore.RED}Error setting up config path: {str(e)}{Style.RESET_ALL}")
        # Fallback to local config if Documents folder is not accessible
        return "steamy_config.json"

class SteamyLauncher:
    def __init__(self):
        self.config_file = get_config_path()
        print(f"{Fore.CYAN}Initializing SteamyLauncher with config: {self.config_file}{Style.RESET_ALL}")
        self.config = self.load_config()
        self.library_paths = self.config.get('library_paths', [])
        self.current_user = self.config.get('current_user', '')
        self.steam_usernames = self.config.get('steam_usernames', {})

    def load_config(self):
        """Load configuration from file"""
        default_config = {
            "library_paths": [],
            "current_user": "",
            "steam_usernames": {},
            "playtime": {}  # Store playtime data for each game
        }
        
        try:
            if os.path.exists(self.config_file):
                print(f"{Fore.GREEN}Loading existing config from: {self.config_file}{Style.RESET_ALL}")
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    print(f"{Fore.GREEN}Loaded config successfully{Style.RESET_ALL}")
                    # Ensure required fields exist
                    if 'steam_usernames' not in config:
                        config['steam_usernames'] = {}
                    if 'playtime' not in config:
                        config['playtime'] = {}
                    return config
            else:
                print(f"{Fore.YELLOW}Config file not found. Creating new config at: {self.config_file}{Style.RESET_ALL}")
                os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
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
                os.path.normpath(f"{drive}:{os.sep}Program Files{os.sep}Steam{os.sep}steamapps"),
                os.path.normpath(f"{drive}:{os.sep}SteamLibrary{os.sep}steamapps"),  # Add SteamLibrary path
                os.path.normpath(f"{drive}:{os.sep}Steam Library{os.sep}steamapps")   # Add Steam Library path with space
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
                msvcrt.putch(key.encode())  # Print the digit immediately
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
            print(f"{Fore.BLUE}┌{'─' * 118}")
            print(f"│{' ' * 118}")
            print(f"│{' ' * 45}{Fore.WHITE}SETTINGS MENU{Style.RESET_ALL}{' ' * 55}")
            print(f"│{' ' * 118}")
            print(f"├{'─' * 118}")
            
            # Settings menu options display
            for i, option in enumerate(options):
                if i == selected_option:
                    print(f"│ {Fore.WHITE}> {option}{Style.RESET_ALL}{' ' * (110 - len(option))}")
                else:
                    print(f"│   {option}{' ' * (110 - len(option))}")
            
            print(f"└{'─' * 118}")
            print(f"\n{Fore.BLUE}Use arrow keys to navigate, Enter to select: {Style.RESET_ALL}", end='', flush=True)
            
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
            print(f"{Fore.BLUE}┌{'─' * 118}")
            print(f"│{' ' * 118}")
            print(f"│{' ' * 45}{Fore.WHITE}LIBRARY PATH MANAGEMENT{Style.RESET_ALL}{' ' * 45}")
            print(f"│{' ' * 118}")
            print(f"├{'─' * 118}")
            
            # Show current paths with better formatting
            print(f"│ {Fore.BLUE}Current Library Paths:{Style.RESET_ALL}")
            if self.library_paths:
                for idx, path in enumerate(self.library_paths, 1):
                    normalized_path = os.path.normpath(path)
                    print(f"│ {Fore.WHITE}{idx}. {normalized_path}{Style.RESET_ALL}")
            else:
                print(f"│ {Fore.RED}No paths configured{Style.RESET_ALL}")
            
            print(f"├{'─' * 118}")
            print(f"│ {Fore.WHITE}1{Style.RESET_ALL} - Add new path{' ' * 100}")
            print(f"│ {Fore.WHITE}2{Style.RESET_ALL} - Remove path{' ' * 100}")
            print(f"│ {Fore.WHITE}3{Style.RESET_ALL} - Auto-detect paths{' ' * 95}")
            print(f"│ {Fore.WHITE}4{Style.RESET_ALL} - Back{' ' * 105}")
            print(f"└{'─' * 118}")
            
            print(f"\n{Fore.BLUE}Press a key: {Style.RESET_ALL}", end='', flush=True)
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
            print(f"{Fore.BLUE}┌{'─' * 118}")
            print(f"│{' ' * 118}")
            print(f"│{' ' * 45}{Fore.WHITE}SELECT STEAM USER{Style.RESET_ALL}{' ' * 55}")
            print(f"│{' ' * 118}")
            print(f"├{'─' * 118}")
            
            # Select Steam user menu display
            for idx, user in enumerate(users):
                if idx == selected_option:
                    print(f"│ {Fore.WHITE}> {user['name']}{Style.RESET_ALL}{' ' * (110 - len(user['name']))}")
                else:
                    print(f"│   {user['name']}{' ' * (110 - len(user['name']))}")
            
            print(f"└{'─' * 118}")
            print(f"\n{Fore.BLUE}Use arrow keys to navigate, Enter to select: {Style.RESET_ALL}", end='', flush=True)
            
            key = self.get_key()
            if key == 'UP':
                selected_option = (selected_option - 1) % len(users)
            elif key == 'DOWN':
                selected_option = (selected_option + 1) % len(users)
            elif key == '\r':  # Enter key
                selected_user = users[selected_option]
                self.current_user = selected_user['id']
                
                # Ask for Steam account username
                print(f"\n{Fore.YELLOW}Please enter your Steam account username (NOT display name) for {selected_user['name']}:{Style.RESET_ALL}")
                username = input().strip()
                
                # Save both the user ID and Steam username
                self.config['current_user'] = self.current_user
                self.steam_usernames[self.current_user] = username
                self.config['steam_usernames'] = self.steam_usernames
                self.save_config()
                
                print(f"\n{Fore.GREEN}Selected user: {selected_user['name']}{Style.RESET_ALL}")
                print(f"{Fore.GREEN}Steam username saved: {username}{Style.RESET_ALL}")
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

    def _get_logged_in_user(self):
        """Get the currently logged in Steam user by checking the registry"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam\ActiveProcess")
            active_user = winreg.QueryValueEx(key, "ActiveUser")[0]
            winreg.CloseKey(key)
            return str(active_user) if active_user and active_user != 0 else None
        except:
            return None

    def _get_steam_config_path(self):
        """Get path to Steam's config folder"""
        for library in self.library_paths:
            steam_folder = os.path.dirname(library)  # Go up one level from steamapps
            config_path = os.path.join(steam_folder, "config")
            if os.path.exists(config_path):
                return config_path
        return None

    def _get_login_token(self, user_id):
        """Get Steam login token for the specified user"""
        try:
            config_path = self._get_steam_config_path()
            if not config_path:
                return None

            # Try to get token from config.vdf
            config_file = os.path.join(config_path, "config.vdf")
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = vdf.load(f)
                    accounts = config.get('InstallConfigStore', {}).get('Software', {}).get('Valve', {}).get('Steam', {}).get('Accounts', {})
                    if user_id in accounts:
                        return accounts[user_id].get('RememberPassword', '0')
            return None
        except:
            return None

    def _get_ssfn_file(self, user_id):
        """Get path to SSFN file for the user if it exists"""
        try:
            for library in self.library_paths:
                steam_folder = os.path.dirname(library)
                # SSFN files are in Steam root folder
                for file in os.listdir(steam_folder):
                    if file.startswith("ssfn") and file.endswith(user_id[-8:]):  # SSFN files end with last 8 digits of Steam ID
                        return os.path.join(steam_folder, file)
            return None
        except:
            return None

    def _is_steam_running(self):
        """Check if Steam is running by looking for its processes"""
        try:
            output = subprocess.check_output(['tasklist'], text=True)
            return 'steam.exe' in output.lower()
        except:
            return False

    def _get_process_by_name(self, name):
        """Get process by name, returns None if not found"""
        for proc in psutil.process_iter(['name', 'pid']):
            try:
                if proc.info['name'].lower() == name.lower():
                    return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return None

    def _get_game_process(self, app_id):
        """Get the game process using various detection methods"""
        # Common process name patterns for Steam games
        possible_names = [
            f"steam_{app_id}.exe",
            f"game_{app_id}.exe",
            f"app_{app_id}.exe"
        ]
        
        # Try to find the process
        for name in possible_names:
            proc = self._get_process_by_name(name)
            if proc:
                return proc
        
        # If not found by common names, try to find by checking Steam's active process
        steam_proc = self._get_process_by_name("steam.exe")
        if steam_proc:
            # Check children of Steam process
            try:
                for child in steam_proc.children():
                    if child.name().lower() not in ["steamservice.exe", "steamwebhelper.exe"]:
                        return child
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        return None

    def _format_time(self, seconds):
        """Format seconds into readable time string"""
        if seconds < 3600:
            return f"{int(seconds // 60)}m {int(seconds % 60)}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"

    def _get_total_playtime(self, app_id):
        """Get total playtime for a game"""
        return self.config.get('playtime', {}).get(str(app_id), 0)

    def _save_playtime(self, app_id, session_time):
        """Save playtime for a game"""
        app_id_str = str(app_id)
        current_total = self.config.get('playtime', {}).get(app_id_str, 0)
        self.config.setdefault('playtime', {})[app_id_str] = current_total + session_time
        self.save_config()

    def launch_game(self, app_id):
        """Launch a Steam game by its AppID"""
        print(f"\n{Fore.CYAN}=== Starting Game Launch Process ==={Style.RESET_ALL}")
        
        users = self.get_steam_users()
        current_user = next((user for user in users if user['id'] == self.current_user), None)
        
        if not current_user:
            print(f"{Fore.RED}Could not find user information. Please select a user again.{Style.RESET_ALL}")
            return

        try:
            # Find Steam executable
            steam_exe = None
            for drive in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                steam_paths = [
                    os.path.normpath(f"{drive}:{os.sep}Steam{os.sep}steam.exe"),
                    os.path.normpath(f"{drive}:{os.sep}Program Files (x86){os.sep}Steam{os.sep}steam.exe"),
                    os.path.normpath(f"{drive}:{os.sep}Program Files{os.sep}Steam{os.sep}steam.exe")
                ]
                for path in steam_paths:
                    if os.path.exists(path):
                        steam_exe = path
                        break
                if steam_exe:
                    break

            if not steam_exe:
                print(f"{Fore.RED}Could not find Steam executable. Please make sure Steam is installed.{Style.RESET_ALL}")
                return

            # Handle Steam login if needed
            steam_running = self._is_steam_running()
            logged_in_user = self._get_logged_in_user() if steam_running else None

            if not steam_running or logged_in_user != current_user['id']:
                if steam_running:
                    subprocess.run(['taskkill', '/F', '/IM', 'steam.exe'], shell=True)
                    time.sleep(3)
                
                username = self.steam_usernames.get(self.current_user)
                if not username:
                    print(f"\n{Fore.YELLOW}Please enter your Steam account username (NOT display name):{Style.RESET_ALL}")
                    username = input().strip()
                    self.steam_usernames[self.current_user] = username
                    self.config['steam_usernames'] = self.steam_usernames
                    self.save_config()
                
                subprocess.Popen(f'"{steam_exe}" -login {username}', shell=True)
                time.sleep(5)

            # Launch game
            game_command = f'"{steam_exe}" -applaunch {app_id}'
            subprocess.Popen(game_command, shell=True)
            time.sleep(5)  # Wait for game to start

            # Game monitoring
            start_time = time.time()
            last_save = start_time
            game_name = self._get_game_name(app_id)
            total_playtime = self._get_total_playtime(app_id)
            last_cpu_check = 0
            cpu_history = []
            game_was_running = False
            running_time = 0
            
            while True:
                os.system('cls' if os.name == 'nt' else 'clear')
                current_time = time.time()
                session_time = current_time - start_time
                
                # Get game process and system info
                game_proc = self._get_game_process(app_id)
                
                # Track if game was running and for how long
                if game_proc:
                    game_was_running = True
                    running_time = session_time
                elif game_was_running and running_time >= 15:
                    # Show closing message if game ran for at least 15 seconds
                    os.system('cls' if os.name == 'nt' else 'clear')
                    print(f"\n{Fore.BLUE}╔{'═' * 50}╗")
                    print(f"║{' ' * 15}{Fore.CYAN}Game Session Ended{Fore.BLUE}{' ' * 17}║")
                    print(f"╠{'═' * 50}╣")
                    print(f"║ {Fore.WHITE}Game:{' ' * 4}{Fore.YELLOW}{game_name[:35]}{' ' * (41 - len(game_name[:35]))}{Fore.BLUE}║")
                    print(f"║ {Fore.WHITE}Played for:{' ' * 1}{Fore.GREEN}{self._format_time(running_time)}{' ' * (41 - len(self._format_time(running_time)))}{Fore.BLUE}║")
                    print(f"║{' ' * 50}║")
                    print(f"║ {Fore.CYAN}Hope you enjoyed playing!{' ' * 27}{Fore.BLUE}║")
                    print(f"╚{'═' * 50}╝{Style.RESET_ALL}")
                    print("\nPress any key to continue...")
                    self.get_key()
                    break
                
                # Calculate CPU and memory usage
                cpu_percent = 0
                memory_mb = 0
                if game_proc:
                    try:
                        # Only update CPU every second to get more accurate readings
                        if current_time - last_cpu_check >= 1:
                            cpu_percent = game_proc.cpu_percent(interval=0.1)
                            cpu_history.append(cpu_percent)
                            # Keep only last 10 readings for average
                            if len(cpu_history) > 10:
                                cpu_history.pop(0)
                            last_cpu_check = current_time
                        
                        memory_info = game_proc.memory_info()
                        memory_mb = memory_info.rss / (1024 * 1024)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

                # Calculate average CPU usage
                avg_cpu = sum(cpu_history) / len(cpu_history) if cpu_history else 0

                # Save playtime every 5 minutes
                if current_time - last_save >= 300:
                    self._save_playtime(app_id, current_time - last_save)
                    last_save = current_time

                # Display monitoring interface with box drawing characters
                print(f"\n{Fore.BLUE}╔{'═' * 50}╗")
                print(f"║{' ' * 15}{Fore.CYAN}Game Session Monitor{Fore.BLUE}{' ' * 16}║")
                print(f"╠{'═' * 50}╣")
                
                # Game info section
                print(f"║ {Fore.WHITE}Game:{' ' * 4}{Fore.YELLOW}{game_name[:35]}{' ' * (41 - len(game_name[:35]))}{Fore.BLUE}║")
                print(f"║ {Fore.WHITE}Status:{' ' * 3}{Fore.GREEN if game_proc else Fore.RED}{'Running' if game_proc else 'Starting/Not detected'}{' ' * (41 - len('Running' if game_proc else 'Starting/Not detected'))}{Fore.BLUE}║")
                
                # Time section
                print(f"╠{'═' * 50}╣")
                print(f"║ {Fore.CYAN}Time Tracking{' ' * 38}{Fore.BLUE}║")
                print(f"║ {Fore.WHITE}Session:{' ' * 2}{Fore.YELLOW}{self._format_time(session_time)}{' ' * (41 - len(self._format_time(session_time)))}{Fore.BLUE}║")
                print(f"║ {Fore.WHITE}Total:{' ' * 4}{Fore.YELLOW}{self._format_time(total_playtime + session_time)}{' ' * (41 - len(self._format_time(total_playtime + session_time)))}{Fore.BLUE}║")
                
                # Performance section
                if game_proc:
                    print(f"╠{'═' * 50}╣")
                    print(f"║ {Fore.CYAN}Performance Metrics{' ' * 33}{Fore.BLUE}║")
                    
                    # CPU usage with color based on load
                    cpu_color = Fore.GREEN if avg_cpu < 50 else (Fore.YELLOW if avg_cpu < 80 else Fore.RED)
                    cpu_text = f"{avg_cpu:.1f}%"
                    print(f"║ {Fore.WHITE}CPU Usage:{' ' * 1}{cpu_color}{cpu_text}{' ' * (41 - len(cpu_text))}{Fore.BLUE}║")
                    
                    # Memory usage with color based on amount
                    mem_color = Fore.GREEN if memory_mb < 1024 else (Fore.YELLOW if memory_mb < 2048 else Fore.RED)
                    mem_text = f"{memory_mb:.1f} MB"
                    print(f"║ {Fore.WHITE}Memory:{' ' * 4}{mem_color}{mem_text}{' ' * (41 - len(mem_text))}{Fore.BLUE}║")
                
                # Controls section
                print(f"╠{'═' * 50}╣")
                print(f"║ {Fore.CYAN}Controls{' ' * 42}{Fore.BLUE}║")
                print(f"║ {Fore.YELLOW}[Q]{Fore.WHITE} Force quit game{' ' * 33}{Fore.BLUE}║")
                print(f"║ {Fore.YELLOW}[K]{Fore.WHITE} Kill game process{' ' * 31}{Fore.BLUE}║")
                print(f"║ {Fore.YELLOW}[R]{Fore.WHITE} Refresh stats{' ' * 35}{Fore.BLUE}║")
                print(f"║ {Fore.YELLOW}[B]{Fore.WHITE} Back to menu{' ' * 36}{Fore.BLUE}║")
                print(f"╚{'═' * 50}╝{Style.RESET_ALL}")
                
                if msvcrt.kbhit():
                    key = msvcrt.getch().decode('utf-8').upper()
                    if key == 'Q':
                        if game_proc:
                            game_proc.terminate()
                            time.sleep(1)
                            if game_proc.is_running():
                                game_proc.kill()
                        break
                    elif key == 'K':
                        if game_proc:
                            game_proc.kill()
                    elif key == 'B':
                        break
                    elif key == 'R':
                        continue

                time.sleep(1)
                
            # Save final playtime
            self._save_playtime(app_id, time.time() - last_save)

        except Exception as e:
            print(f"{Fore.RED}Error launching game: {str(e)}{Style.RESET_ALL}")
            print("\nPress any key to continue...")
            self.get_key()

    def _get_game_name(self, app_id):
        """Get game name from app_id"""
        games = self.get_installed_games()
        game = next((g for g in games if str(g['appid']) == str(app_id)), None)
        return game['name'] if game else f"Game {app_id}"

    def display_menu(self, games):
        """Display the game selection menu"""
        # Set console size to match content
        set_console_size(1200, 600)  # Wider window
        
        selected_game = 0  # Track selected game
        
        # New ASCII art logo
        logo = f"""
{' ' * 35}{Fore.BLUE}____    __                                           
{' ' * 35}/\\  _`\\ /\\ \\__                                        
{' ' * 35}\\ \\,\\L\\_\\ \\ ,_\\    __     __      ___ ___   __  __    
{' ' * 35} \\/_\\__ \\\\ \\ \\/  /'__`\\ /'__`\\  /' __` __`\\/\\ \\/\\ \\   
{' ' * 35}   /\\ \\L\\ \\ \\ \\_/\\  __//\\ \\L\\.\\_/\\ \\/\\ \\/\\ \\ \\ \\_\\ \\  
{' ' * 35}   \\ `\\____\\ \\__\\ \\____\\ \\__/.\\_\\ \\_\\ \\_\\ \\_\\/`____ \\ 
{' ' * 35}    \\/_____/\\/__/\\/____/\\/__/\\/_/\\/_/\\/_/\\/_/`/___/> \\
{' ' * 35}                                                /\\___/
{' ' * 35}                                                \\/__/ {Style.RESET_ALL}"""
        
        while True:
            # Clear screen
            os.system('cls' if os.name == 'nt' else 'clear')
            
            # Print centered logo
            print("\n" + logo + "\n")

            # Games list with modern styling
            print(f"{Fore.BLUE}┌{'─' * 118}")
            
            if not self.library_paths:
                # Show welcome message when no libraries are configured
                print(f"│{' ' * 118}")
                print(f"│{' ' * 35}{Fore.YELLOW}Welcome to Steamy!{Style.RESET_ALL}{' ' * 65}")
                print(f"│{' ' * 25}{Fore.WHITE}To get started, configure your Steam libraries using the options below.{Style.RESET_ALL}{' ' * 25}")
                print(f"│{' ' * 30}{Fore.WHITE}Press [S] for Settings or [A] to Auto-detect libraries.{Style.RESET_ALL}{' ' * 35}")
                print(f"│{' ' * 118}")
            elif not self.current_user and self.library_paths:
                # Show welcome message when libraries are configured but no user is selected
                print(f"│{' ' * 118}")
                print(f"│{' ' * 35}{Fore.YELLOW}Almost there!{Style.RESET_ALL}{' ' * 65}")
                print(f"│{' ' * 25}{Fore.WHITE}Please select a Steam user to continue.{Style.RESET_ALL}{' ' * 45}")
                print(f"│{' ' * 118}")
                print(f"└{'─' * 118}{Style.RESET_ALL}")
                print(f"\n{Fore.BLUE}Press any key to select a user...{Style.RESET_ALL}")
                self.get_key()
                self.select_steam_user()
                games = self.get_installed_games()  # Refresh games list after user selection
                continue
            elif games:
                print(f"│ {Fore.BLUE}Installed Games{' ' * 100}")
                print(f"├{'─' * 118}")
                
                # Show games in a 3-column grid format
                for i in range(0, len(games), 3):
                    game1 = games[i]
                    game2 = games[i + 1] if i + 1 < len(games) else None
                    game3 = games[i + 2] if i + 2 < len(games) else None
                    
                    # Add selection indicator with clear highlighting
                    if i == selected_game:
                        prefix1 = f"{Fore.CYAN}> {i+1:2d}.{Style.RESET_ALL}"
                        name1 = f"{Fore.CYAN}{game1['name'][:35]:<35}{Style.RESET_ALL}"
                    else:
                        prefix1 = f"{Fore.WHITE}  {i+1:2d}.{Style.RESET_ALL}"
                        name1 = f"{Fore.WHITE}{game1['name'][:35]:<35}{Style.RESET_ALL}"
                        
                    if game2:
                        if i + 1 == selected_game:
                            prefix2 = f"{Fore.CYAN}> {i+2:2d}.{Style.RESET_ALL}"
                            name2 = f"{Fore.CYAN}{game2['name'][:35]:<35}{Style.RESET_ALL}"
                        else:
                            prefix2 = f"{Fore.WHITE}  {i+2:2d}.{Style.RESET_ALL}"
                            name2 = f"{Fore.WHITE}{game2['name'][:35]:<35}{Style.RESET_ALL}"
                            
                    if game3:
                        if i + 2 == selected_game:
                            prefix3 = f"{Fore.CYAN}> {i+3:2d}.{Style.RESET_ALL}"
                            name3 = f"{Fore.CYAN}{game3['name'][:35]:<35}{Style.RESET_ALL}"
                        else:
                            prefix3 = f"{Fore.WHITE}  {i+3:2d}.{Style.RESET_ALL}"
                            name3 = f"{Fore.WHITE}{game3['name'][:35]:<35}{Style.RESET_ALL}"
                    
                    if game2 and game3:
                        print(f"{Fore.BLUE}│{Style.RESET_ALL} {prefix1} {name1} {prefix2} {name2} {prefix3} {name3}")
                    elif game2:
                        print(f"{Fore.BLUE}│{Style.RESET_ALL} {prefix1} {name1} {prefix2} {name2} {' ' * 40}")
                    else:
                        print(f"{Fore.BLUE}│{Style.RESET_ALL} {prefix1} {name1} {' ' * 75}")
                
                # Add padding if needed
                if len(games) % 3 != 0:
                    print(f"{Fore.BLUE}│{' ' * 118}")
            else:
                print(f"│{' ' * 118}")
                print(f"│{' ' * 25}{Fore.RED}No games found in your configured libraries.{Style.RESET_ALL}{' ' * 45}")
                print(f"│{' ' * 25}{Fore.WHITE}Press [R] to refresh or [S] to check library paths in Settings.{Style.RESET_ALL}{' ' * 30}")
                print(f"│{' ' * 118}")
            
            # Quick actions bar
            print(f"{Fore.BLUE}├{'─' * 118}")
            
            # Get user info for status display
            user_info = ""
            if self.current_user:
                users = self.get_steam_users()
                current_user_name = next((user['name'] for user in users if user['id'] == self.current_user), 'Unknown User')
                user_info = f"{Fore.BLUE}{current_user_name}{Style.RESET_ALL}"
            else:
                user_info = f"{Fore.BLUE}No User Selected{Style.RESET_ALL}"
            
            # Show Quick Actions with user info on the right
            print(f"│ {Fore.BLUE}Quick Actions:{Style.RESET_ALL}{' ' * 70}{user_info}")
            
            # Show quick actions based on state
            if not self.library_paths:
                print(f"│ {Fore.YELLOW}[S]{Style.RESET_ALL} Settings | {Fore.YELLOW}[A]{Style.RESET_ALL} Auto-detect | {Fore.YELLOW}[Q]{Style.RESET_ALL} Quit")
            else:
                print(f"│ {Fore.YELLOW}[S]{Style.RESET_ALL} Settings | {Fore.YELLOW}[R]{Style.RESET_ALL} Refresh | {Fore.YELLOW}[Q]{Style.RESET_ALL} Quit")
            
            library_info = f"{Fore.BLUE}Libraries: {Style.RESET_ALL}{len(self.library_paths)}"
            print(f"└{'─' * 118}{Style.RESET_ALL}")
            
            # Navigation prompt
            if games and self.current_user:
                print(f"\n{Fore.BLUE}Use arrow keys to select a game, Enter to launch, or quick action keys: {Style.RESET_ALL}", end='', flush=True)
            else:
                print(f"\n{Fore.BLUE}Press a key to select an action: {Style.RESET_ALL}", end='', flush=True)
            
            # Handle input
            key = self.get_key()
            
            # Handle quick actions
            if key == 'S':  # Settings
                self.settings_menu()
                games = self.get_installed_games()
            elif key == 'R' and self.library_paths:  # Refresh
                games = self.get_installed_games()
            elif key == 'A' and not self.library_paths:  # Auto-detect
                auto_paths = self.find_steam_libraries()
                if auto_paths:
                    for path in auto_paths:
                        if path not in self.library_paths:
                            self.library_paths.append(path)
                    self.config['library_paths'] = self.library_paths
                    self.save_config()
                    games = self.get_installed_games()
            elif key == 'Q':  # Quit
                return
            # Handle game navigation and selection
            elif games and self.current_user:
                if key in ['LEFT', 'RIGHT']:
                    if key == 'LEFT' and selected_game > 0:
                        selected_game -= 1
                    elif key == 'RIGHT' and selected_game < len(games) - 1:
                        selected_game += 1
                elif key in ['UP', 'DOWN']:
                    if key == 'UP' and selected_game >= 3:
                        selected_game -= 3
                    elif key == 'DOWN' and selected_game < len(games) - 3:
                        selected_game += 3
                elif key == '\r':  # Enter key
                    if selected_game < len(games):
                        self.launch_game(games[selected_game]['appid'])

def main():
    try:
        # Set initial console size
        set_console_size(800, 400)
        
        # Set console title
        set_console_title("Steamy - Steam Game Launcher")
        
        print(f"{Fore.YELLOW}Initializing Steam Launcher...{Style.RESET_ALL}")
        launcher = SteamyLauncher()
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