"""
Windows Application Scanner - Advanced Version
=================================================

This script scans the computer to find all installed applications
with their REAL execution paths, without any manual configuration.

New Features:
- Automatic detection of real execution paths
- Deep Windows registry scanning
- Smart shortcut resolution
- Environment variable detection
- Path validation
- Optimized UWP/Store application handling
"""

import os
import winreg
import json
import subprocess
import re
import shutil
from pathlib import Path
import glob

class AdvancedApplicationScanner:
    def __init__(self):
        self.applications = {}
        self.found_executables = {}

        # Priority scan methods
        self.scan_methods = [
            self.scan_registry_uninstall,
            self.scan_registry_app_paths,
            self.scan_start_menu_shortcuts,
            self.scan_program_directories,
            self.scan_uwp_applications,
            self.scan_environment_path,
            self.scan_known_locations
        ]

        # Important locations to scan
        self.scan_locations = [
            r"C:\Program Files",
            r"C:\Program Files (x86)",
            os.path.expanduser(r"~\AppData\Local"),
            os.path.expanduser(r"~\AppData\Roaming"),
            r"C:\Windows\System32",
            r"C:\Windows\SysWOW64"
        ]

    def scan_registry_uninstall(self):
        """Deep scan of installed programs registry"""
        print("🔍 Deep scanning Windows registry...")

        registry_keys = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
        ]

        for hkey, subkey_path in registry_keys:
            try:
                with winreg.OpenKey(hkey, subkey_path) as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, subkey_name) as subkey:
                                self._extract_app_from_registry(subkey)
                        except Exception:
                            continue
            except Exception as e:
                print(f"⚠️ Registry error {subkey_path}: {e}")

    def scan_registry_app_paths(self):
        """Scan application paths in registry"""
        print("🔍 Scanning application paths from registry...")

        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths") as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        app_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, app_name) as app_key:
                            try:
                                path = winreg.QueryValueEx(app_key, "")[0]
                                if path and os.path.exists(path):
                                    clean_name = self.clean_app_name(app_name.replace('.exe', ''))
                                    if clean_name:
                                        self._add_application(clean_name, {
                                            "name": clean_name,
                                            "path": path,
                                            "process": app_name,
                                            "source": "registry_app_paths"
                                        })
                            except FileNotFoundError:
                                pass
                    except Exception:
                        continue
        except Exception as e:
            print(f"⚠️ App Paths error: {e}")

    def scan_start_menu_shortcuts(self):
        """Smart scan of Start Menu shortcuts"""
        print("🔍 Smart scanning shortcuts...")

        start_menu_paths = [
            os.path.expanduser(r"~\AppData\Roaming\Microsoft\Windows\Start Menu\Programs"),
            r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
        ]

        for start_path in start_menu_paths:
            if os.path.exists(start_path):
                for root, dirs, files in os.walk(start_path):
                    for file in files:
                        if file.endswith('.lnk'):
                            shortcut_path = os.path.join(root, file)
                            self._process_shortcut(shortcut_path)

    def scan_program_directories(self):
        """Smart scan of program directories"""
        print("🔍 Smart scanning program directories...")

        for location in self.scan_locations:
            if os.path.exists(location):
                try:
                    for item in os.listdir(location):
                        item_path = os.path.join(location, item)
                        if os.path.isdir(item_path):
                            self._scan_directory_for_apps(item_path, item)
                except PermissionError:
                    continue
                except Exception:
                    continue

    def scan_uwp_applications(self):
        """Advanced scan of UWP/Store applications"""
        print("🔍 Advanced scanning UWP applications...")

        try:
            # Enhanced PowerShell command for UWP
            ps_command = """
            Get-AppxPackage | Where-Object {
                $_.Name -ne $null -and
                $_.InstallLocation -ne $null -and
                $_.Name -notlike "*Microsoft.Windows*" -and
                $_.Name -notlike "*windows.immersivecontrolpanel*"
            } | ForEach-Object {
                [PSCustomObject]@{
                    Name = $_.Name
                    PackageFullName = $_.PackageFullName
                    InstallLocation = $_.InstallLocation
                    DisplayName = (Get-AppxPackageManifest $_).Package.Properties.DisplayName
                }
            } | ConvertTo-Json
            """

            result = subprocess.run([
                "powershell", "-Command", ps_command
            ], capture_output=True, text=True, timeout=45)

            if result.returncode == 0 and result.stdout.strip():
                try:
                    apps_data = json.loads(result.stdout)
                    if not isinstance(apps_data, list):
                        apps_data = [apps_data]

                    for app in apps_data:
                        if app and app.get('Name'):
                            self._process_uwp_app(app)
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            print(f"⚠️ UWP scan error: {e}")

    def scan_environment_path(self):
        """Scan applications in system PATH"""
        print("🔍 Scanning system PATH...")

        path_dirs = os.environ.get('PATH', '').split(os.pathsep)
        for path_dir in path_dirs:
            if os.path.exists(path_dir):
                try:
                    for file in os.listdir(path_dir):
                        if file.endswith('.exe'):
                            full_path = os.path.join(path_dir, file)
                            clean_name = self.clean_app_name(file.replace('.exe', ''))
                            if clean_name and self._is_valid_application(clean_name):
                                self._add_application(clean_name, {
                                    "name": clean_name,
                                    "path": full_path,
                                    "process": file,
                                    "source": "system_path"
                                })
                except (PermissionError, OSError):
                    continue

    def scan_known_locations(self):
        """Scan known locations for popular applications"""
        print("🔍 Scanning known locations...")

        known_apps = {
            "Google Chrome": [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
            ],
            "Mozilla Firefox": [
                r"C:\Program Files\Mozilla Firefox\firefox.exe",
                r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe"
            ],
            "Microsoft Edge": [
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
            ],
            "VLC Media Player": [
                r"C:\Program Files\VideoLAN\VLC\vlc.exe",
                r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"
            ],
            "Notepad++": [
                r"C:\Program Files\Notepad++\notepad++.exe",
                r"C:\Program Files (x86)\Notepad++\notepad++.exe"
            ],
            "Visual Studio Code": [
                r"C:\Users\{}\AppData\Local\Programs\Microsoft VS Code\Code.exe".format(os.getenv('USERNAME')),
                r"C:\Program Files\Microsoft VS Code\Code.exe"
            ]
        }

        for app_name, paths in known_apps.items():
            for path in paths:
                if os.path.exists(path):
                    clean_name = self.clean_app_name(app_name)
                    self._add_application(clean_name, {
                        "name": app_name,
                        "path": path,
                        "process": os.path.basename(path),
                        "source": "known_location"
                    })
                    break  # Take the first valid path found

    def _extract_app_from_registry(self, subkey):
        """Extract application information from registry"""
        try:
            display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]

            # Get all available information
            install_location = self._safe_registry_read(subkey, "InstallLocation")
            uninstall_string = self._safe_registry_read(subkey, "UninstallString")
            display_icon = self._safe_registry_read(subkey, "DisplayIcon")

            # Clean name
            clean_name = self.clean_app_name(display_name)
            if not clean_name or len(clean_name) < 2:
                return

            # Find the real execution path
            executable_path = self._find_executable_from_registry_data(
                install_location, uninstall_string, display_icon, clean_name
            )

            if executable_path:
                self._add_application(clean_name, {
                    "name": display_name,
                    "path": executable_path,
                    "process": os.path.basename(executable_path),
                    "source": "registry_uninstall",
                    "install_location": install_location
                })

        except FileNotFoundError:
            pass
        except Exception:
            pass

    def _safe_registry_read(self, key, value_name):
        """Safe registry value reading"""
        try:
            return winreg.QueryValueEx(key, value_name)[0]
        except FileNotFoundError:
            return ""
        except Exception:
            return ""

    def _find_executable_from_registry_data(self, install_location, uninstall_string, display_icon, app_name):
        """Find the real executable from registry data"""

        # Method 1: Use display icon if it's an .exe
        if display_icon and display_icon.endswith('.exe') and os.path.exists(display_icon):
            return display_icon

        # Method 2: Look in installation directory
        if install_location and os.path.exists(install_location):
            main_exe = self._find_main_executable_in_directory(install_location, app_name)
            if main_exe:
                return main_exe

        # Method 3: Parse uninstall string
        if uninstall_string:
            exe_from_uninstall = self._extract_exe_from_uninstall_string(uninstall_string)
            if exe_from_uninstall and os.path.exists(exe_from_uninstall):
                return exe_from_uninstall

        return None

    def _find_main_executable_in_directory(self, directory, app_name):
        """Find the main executable in a directory"""
        if not os.path.exists(directory):
            return None

        # Priority name patterns
        app_name_clean = re.sub(r'[^a-zA-Z0-9]', '', app_name.lower())
        priority_patterns = [
            f"{app_name_clean}.exe",
            f"{app_name.lower().replace(' ', '')}.exe",
            f"{app_name.split()[0].lower()}.exe"
        ]

        # First look for priority executables
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.exe'):
                    file_lower = file.lower()
                    # Check priority patterns
                    for pattern in priority_patterns:
                        if file_lower == pattern:
                            return os.path.join(root, file)

        # If not found, look for the first main executable
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.exe'):
                    # Avoid tools and installers
                    if not any(skip in file.lower() for skip in
                             ['uninstall', 'setup', 'installer', 'updater', 'launcher', 'helper']):
                        return os.path.join(root, file)

        return None

    def _extract_exe_from_uninstall_string(self, uninstall_string):
        """Extract .exe path from uninstall string"""
        # Patterns to extract exe path
        patterns = [
            r'"([^"]+\.exe)"',  # Exe in quotes
            r'(\S+\.exe)',      # Exe without quotes
        ]

        for pattern in patterns:
            match = re.search(pattern, uninstall_string)
            if match:
                potential_exe = match.group(1)
                # Look in the same directory for the main exe
                if os.path.exists(potential_exe):
                    directory = os.path.dirname(potential_exe)
                    main_exe = self._find_main_executable_in_directory(directory, "")
                    return main_exe if main_exe else potential_exe

        return None

    def _process_shortcut(self, shortcut_path):
        """Process a .lnk shortcut"""
        try:
            app_name = os.path.splitext(os.path.basename(shortcut_path))[0]
            clean_name = self.clean_app_name(app_name)

            if not clean_name or len(clean_name) < 2:
                return

            # Resolve shortcut
            target = self._resolve_shortcut_target(shortcut_path)
            if target and os.path.exists(target) and target.endswith('.exe'):
                self._add_application(clean_name, {
                    "name": app_name,
                    "path": target,
                    "process": os.path.basename(target),
                    "source": "start_menu_shortcut",
                    "shortcut_path": shortcut_path
                })
        except Exception:
            pass

    def _resolve_shortcut_target(self, shortcut_path):
        """Resolve .lnk shortcut target"""
        try:
            # Method 1: Use win32com if available
            try:
                import win32com.client
                shell = win32com.client.Dispatch("WScript.Shell")
                shortcut = shell.CreateShortcut(shortcut_path)
                return shortcut.TargetPath
            except ImportError:
                pass

            # Method 2: Use PowerShell
            try:
                ps_command = f"""
                $sh = New-Object -ComObject WScript.Shell
                $shortcut = $sh.CreateShortcut('{shortcut_path}')
                $shortcut.TargetPath
                """
                result = subprocess.run([
                    "powershell", "-Command", ps_command
                ], capture_output=True, text=True, timeout=10)

                if result.returncode == 0:
                    return result.stdout.strip()
            except Exception:
                pass

        except Exception:
            pass

        return None

    def _scan_directory_for_apps(self, directory, folder_name):
        """Scan a directory for applications"""
        try:
            main_exe = self._find_main_executable_in_directory(directory, folder_name)
            if main_exe:
                clean_name = self.clean_app_name(folder_name)
                if clean_name and len(clean_name) > 2:
                    self._add_application(clean_name, {
                        "name": folder_name,
                        "path": main_exe,
                        "process": os.path.basename(main_exe),
                        "source": "directory_scan",
                        "install_directory": directory
                    })
        except Exception:
            pass

    def _process_uwp_app(self, app_data):
        """Process a UWP application"""
        try:
            package_name = app_data.get('Name', '')
            display_name = app_data.get('DisplayName', package_name)
            package_full_name = app_data.get('PackageFullName', package_name)

            # Clean display name
            clean_name = self.clean_app_name(display_name if display_name else package_name)
            if not clean_name:
                return

            # Create UWP opening command
            uwp_command = f"shell:appsfolder\\{package_full_name}!App"

            self._add_application(clean_name, {
                "name": display_name if display_name else clean_name,
                "path": uwp_command,
                "process": package_name,
                "source": "uwp_store",
                "type": "uwp",
                "package_name": package_name
            })

        except Exception:
            pass

    def _add_application(self, clean_name, app_data):
        """Add an application to the list with duplicate handling"""
        key = clean_name.lower()

        # If application already exists, prioritize certain sources
        if key in self.applications:
            existing_source = self.applications[key].get("source", "")
            new_source = app_data.get("source", "")

            # Source priority order
            source_priority = {
                "known_location": 5,
                "registry_app_paths": 4,
                "start_menu_shortcut": 3,
                "registry_uninstall": 2,
                "directory_scan": 1,
                "system_path": 1,
                "uwp_store": 3
            }

            existing_priority = source_priority.get(existing_source, 0)
            new_priority = source_priority.get(new_source, 0)

            # Only replace if new source is higher priority
            if new_priority <= existing_priority:
                return

        # Validate that path exists (except for UWP)
        if app_data.get("type") != "uwp":
            if not os.path.exists(app_data["path"]):
                return

        # Add voice commands
        app_data["commands"] = self._generate_voice_commands(clean_name)

        self.applications[key] = app_data

    def _generate_voice_commands(self, app_name):
        """Generate smart voice commands for an application"""
        commands = set()
        name_lower = app_name.lower()

        # Full name
        commands.add(name_lower)

        # Individual words (more than 2 characters)
        words = re.findall(r'\b\w{3,}\b', name_lower)
        commands.update(words)

        # Acronyms for compound names
        if len(words) > 1:
            acronym = ''.join(word[0] for word in words)
            if len(acronym) >= 2:
                commands.add(acronym)

        # Common alternative names
        name_mappings = {
            'google chrome': ['chrome', 'google browser'],
            'mozilla firefox': ['firefox', 'mozilla browser'],
            'microsoft edge': ['edge', 'microsoft browser'],
            'vlc media player': ['vlc', 'video player'],
            'visual studio code': ['vscode', 'vs code'],
            'notepad++': ['notepad plus plus', 'text editor'],
            'microsoft word': ['word', 'word processor'],
            'microsoft excel': ['excel', 'spreadsheet'],
            'microsoft powerpoint': ['powerpoint', 'presentation']
        }

        for app_pattern, alternatives in name_mappings.items():
            if app_pattern in name_lower:
                commands.update(alternatives)

        return list(commands)

    def _is_valid_application(self, app_name):
        """Check if an application name is valid"""
        if not app_name or len(app_name) < 2:
            return False

        # Filter system/utilities
        invalid_patterns = [
            'uninstall', 'setup', 'installer', 'updater', 'helper',
            'service', 'driver', 'runtime', 'redistributable',
            'microsoft visual c++', 'vcredist', '.net framework'
        ]

        app_lower = app_name.lower()
        return not any(pattern in app_lower for pattern in invalid_patterns)

    def clean_app_name(self, name):
        """Clean and normalize an application name"""
        if not name:
            return ""

        # Remove unwanted elements
        cleaned = re.sub(r'\s*\([^)]*\)', '', name)  # Parentheses
        cleaned = re.sub(r'\s*\[[^\]]*\]', '', cleaned)  # Brackets
        cleaned = re.sub(r'\s+v?\d+(\.\d+)*(\.\d+)*', '', cleaned)  # Versions
        cleaned = re.sub(r'\s+(x64|x86|32-bit|64-bit|win32|win64)', '', cleaned, re.IGNORECASE)
        cleaned = re.sub(r'\s+(update|hotfix|patch)', '', cleaned, re.IGNORECASE)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()  # Normalize spaces

        # Special cases
        if 'google chrome' in cleaned.lower():
            return 'Google Chrome'
        elif 'mozilla firefox' in cleaned.lower():
            return 'Mozilla Firefox'
        elif 'microsoft edge' in cleaned.lower():
            return 'Microsoft Edge'

        return cleaned if self._is_valid_application(cleaned) else ""

    def run_full_scan(self):
        """Run a complete scan with all methods"""
        print("🚀 Starting advanced full scan...")

        for method in self.scan_methods:
            try:
                method()
            except Exception as e:
                print(f"⚠️ Error in {method.__name__}: {e}")

        # Post-processing: verification and cleanup
        self._post_process_applications()

        print(f"✅ Scan complete! {len(self.applications)} applications found.")
        return self.applications

    def _post_process_applications(self):
        """Post-process found applications"""
        print("🔧 Post-processing applications...")

        # Remove applications with invalid paths
        to_remove = []
        for key, app_data in self.applications.items():
            if app_data.get("type") != "uwp":
                if not os.path.exists(app_data["path"]):
                    to_remove.append(key)

        for key in to_remove:
            del self.applications[key]

        print(f"🧹 {len(to_remove)} applications with invalid paths removed")

    def save_to_assistant_format(self, filename="applications_assistant.json"):
        """Save directly in vocal assistant format"""
        assistant_apps = {}

        for key, app_data in self.applications.items():
            assistant_apps[key] = {
                "nom": app_data["name"],
                "chemin": app_data["path"],
                "processus": app_data["process"],
                "commandes": app_data["commands"],
                "source": app_data["source"]
            }

        output_file = os.path.join(os.path.dirname(__file__), filename)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(assistant_apps, f, indent=2, ensure_ascii=False)

        print(f"💾 {len(assistant_apps)} applications saved to: {output_file}")
        return output_file

    def print_scan_summary(self):
        """Print scan summary"""
        print("\n" + "="*60)
        print("📋 APPLICATION SCAN SUMMARY")
        print("="*60)

        # Statistics by source
        sources = {}
        for app_data in self.applications.values():
            source = app_data.get("source", "unknown")
            sources[source] = sources.get(source, 0) + 1

        print("\n📊 Applications by source:")
        for source, count in sorted(sources.items()):
            print(f"   • {source}: {count} applications")

        # Example applications found
        print(f"\n🎯 Example applications found ({min(10, len(self.applications))}):")
        for i, (key, app_data) in enumerate(list(self.applications.items())[:10]):
            commands_preview = ", ".join(app_data["commands"][:3])
            if len(app_data["commands"]) > 3:
                commands_preview += "..."
            print(f"   {i+1:2d}. {app_data['name']}")
            print(f"       Commands: {commands_preview}")
            print(f"       Path: {app_data['path'][:50]}...")

        print(f"\n✅ TOTAL: {len(self.applications)} applications ready for vocal assistant")

def main():
    print("🔍 Windows Application Scanner - Advanced Version")
    print("=" * 60)

    scanner = AdvancedApplicationScanner()

    # Run full scan
    applications = scanner.run_full_scan()

    # Save in assistant format
    output_file = scanner.save_to_assistant_format()

    # Print summary
    scanner.print_scan_summary()

    print(f"\n🎉 Scan completed successfully!")
    print(f"📁 File generated: {output_file}")
    print(f"🤖 {len(applications)} applications ready for vocal assistant")

if __name__ == "__main__":
    main()