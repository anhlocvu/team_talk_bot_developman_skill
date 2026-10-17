"""
TeamTalk Bot Project Setup & Diagnostics Tool
=============================================
This script helps developers and AI agents:
1. Initialize new TeamTalk bot projects with proper directory layouts and DLL placement.
2. Check existing projects for missing files, DLL conflicts, or Python bitness mismatch.
3. Download and extract essential TeamTalk SDK runtime assets while discarding unused files.
4. Auto-repair missing runtime components.
"""

import os
import sys
import json
import shutil
import platform
import argparse
import urllib.request
import subprocess

SDK_DOWNLOAD_URLS = {
    "win64": "https://www.bearware.dk/teamtalksdk/v5.23a/tt5sdk_v5.23a_win64.7z",
    "ubuntu_x86_64": "https://www.bearware.dk/teamtalksdk/v5.23a/tt5sdk_v5.23a_ubuntu26_x86_64.7z",
    "macos": "https://www.bearware.dk/teamtalksdk/v5.23a/tt5sdk_v5.23a_macos_universal.7z",
    "raspbian_arm64": "https://www.bearware.dk/teamtalksdk/v5.23a/tt5sdk_v5.23a_raspbian_arm64.7z"
}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
BUNDLED_TEAMTALKPY = os.path.join(SKILL_ROOT, "resources", "teamtalkpy")
TEMPLATES_DIR = os.path.join(SKILL_ROOT, "resources", "templates")


def detect_platform_key():
    is_64 = sys.maxsize > 2**32
    if sys.platform == "win32":
        return "win64" if is_64 else "win32"
    elif sys.platform.startswith("linux"):
        machine = platform.machine().lower()
        if "arm" in machine or "aarch64" in machine:
            return "raspbian_arm64"
        return "ubuntu_x86_64"
    elif sys.platform == "darwin":
        return "macos"
    return "unknown"


def find_bundled_sources():
    """Locate bundled TeamTalkPy files within the skill or workspace."""
    candidates = [
        BUNDLED_TEAMTALKPY,
        os.path.join(SKILL_ROOT, "tt5sdk_v5.23a_win64", "Library", "TeamTalkPy"),
        os.path.join(os.getcwd(), "resources", "teamtalkpy"),
    ]
    for c in candidates:
        if os.path.isdir(c) and os.path.isfile(os.path.join(c, "TeamTalk5.py")):
            dll_path = os.path.join(c, "TeamTalk5.dll")
            if not os.path.isfile(dll_path):
                # Check sibling or parent
                alt_dll = os.path.join(SKILL_ROOT, "tt5sdk_v5.23a_win64", "Library", "TeamTalk_DLL", "TeamTalk5.dll")
                if os.path.isfile(alt_dll):
                    dll_path = alt_dll
            return c, dll_path
    return None, None


def check_project(target_dir=".", auto_fix=False):
    """Diagnose a TeamTalk bot project and check for missing files."""
    target_dir = os.path.abspath(target_dir)
    print(f"[*] Checking TeamTalk bot project in: {target_dir}")
    issues = []
    warnings = []

    # 1. Check Python architecture
    is_64bit = sys.maxsize > 2**32
    print(f"    - Python version: {platform.python_version()} ({'64-bit' if is_64bit else '32-bit'}) on {sys.platform}")
    if not is_64bit and sys.platform == "win32":
        warnings.append("Python 32-bit detected. The standard TeamTalk 5 64-bit DLL requires 64-bit Python.")

    # 2. Check for TeamTalk5.py and TeamTalk5.dll
    py_locations = [
        os.path.join(target_dir, "TeamTalk5.py"),
        os.path.join(target_dir, "teamtalkpy", "TeamTalk5.py"),
        os.path.join(target_dir, "teamtalk", "TeamTalk5.py"),
        os.path.join(target_dir, "lib", "TeamTalk5.py")
    ]
    found_py = next((p for p in py_locations if os.path.isfile(p)), None)

    dll_locations = [
        os.path.join(target_dir, "TeamTalk5.dll"),
        os.path.join(target_dir, "teamtalkpy", "TeamTalk5.dll"),
        os.path.join(target_dir, "teamtalk", "TeamTalk5.dll"),
        os.path.join(target_dir, "lib", "TeamTalk5.dll"),
        os.path.join(target_dir, "TeamTalk_DLL", "TeamTalk5.dll")
    ]
    found_dll = next((p for p in dll_locations if os.path.isfile(p)), None)

    if not found_py:
        issues.append("TeamTalk5.py wrapper is missing from the project.")
    else:
        print(f"    [+] Found TeamTalk5.py: {os.path.relpath(found_py, target_dir)}")

    if not found_dll and sys.platform == "win32":
        issues.append("TeamTalk5.dll is missing from the project.")
    elif found_dll:
        print(f"    [+] Found TeamTalk5.dll: {os.path.relpath(found_dll, target_dir)}")

    # 3. Check for bot entrypoint
    entrypoints = ["bot.py", "main.py", "app.py"]
    found_entry = next((e for e in entrypoints if os.path.isfile(os.path.join(target_dir, e))), None)
    if not found_entry:
        warnings.append("No standard bot entrypoint found (bot.py or main.py).")
    else:
        print(f"    [+] Found bot entrypoint: {found_entry}")

    # 4. Check for config
    configs = ["config.json", "config.yaml", ".env"]
    found_config = next((c for c in configs if os.path.isfile(os.path.join(target_dir, c))), None)
    if not found_config:
        warnings.append("No configuration file (config.json or .env) found.")
    else:
        print(f"    [+] Found config file: {found_config}")

    # 5. Test import if files are present
    if found_py and (found_dll or sys.platform != "win32"):
        py_dir = os.path.dirname(found_py)
        if py_dir not in sys.path:
            sys.path.insert(0, py_dir)
        try:
            import TeamTalk5
            version = TeamTalk5.getVersion()
            print(f"    [+] Successfully loaded TeamTalk SDK engine! Version: {version}")
        except Exception as e:
            issues.append(f"Failed to import TeamTalk5: {e}")

    # Summary
    print("\n--- Diagnostic Results ---")
    if not issues and not warnings:
        print(" SUCCESS: Project structure is complete and operational!")
        return True

    for w in warnings:
        print(f" [!] WARNING: {w}")
    for i in issues:
        print(f" [X] ERROR: {i}")

    if auto_fix and issues:
        print("\n[*] Attempting auto-fix...")
        fix_project(target_dir)
        return check_project(target_dir, auto_fix=False)

    return False


def fix_project(target_dir):
    """Repair missing files in project using bundled assets."""
    target_dir = os.path.abspath(target_dir)
    src_dir, src_dll = find_bundled_sources()
    if not src_dir:
        print(" [X] Cannot auto-fix: No bundled TeamTalkPy source directory found.")
        return False

    dest_lib_dir = os.path.join(target_dir, "teamtalkpy")
    os.makedirs(dest_lib_dir, exist_ok=True)

    # Copy TeamTalk5.py and __init__.py
    for fname in ["TeamTalk5.py", "__init__.py"]:
        src_file = os.path.join(src_dir, fname)
        if os.path.isfile(src_file):
            shutil.copy2(src_file, os.path.join(dest_lib_dir, fname))
            print(f"    [+] Installed: teamtalkpy/{fname}")

    # Copy DLL
    if src_dll and os.path.isfile(src_dll):
        shutil.copy2(src_dll, os.path.join(dest_lib_dir, "TeamTalk5.dll"))
        print(f"    [+] Installed: teamtalkpy/TeamTalk5.dll")
        # Also copy to root for maximum compatibility
        shutil.copy2(src_dll, os.path.join(target_dir, "TeamTalk5.dll"))
        print(f"    [+] Installed: TeamTalk5.dll (root)")

    print("[*] Repair complete. Re-checking...")
    return True


def init_project(target_dir=".", bot_name="TeamTalkBot", force=False):
    """Scaffold a brand new TeamTalk bot project."""
    target_dir = os.path.abspath(target_dir)
    print(f"[*] Initializing new TeamTalk bot project: {bot_name} at {target_dir}")
    os.makedirs(target_dir, exist_ok=True)

    dest_teamtalkpy = os.path.join(target_dir, "teamtalkpy")
    os.makedirs(dest_teamtalkpy, exist_ok=True)

    # 1. Install TeamTalkPy & DLL
    src_dir, src_dll = find_bundled_sources()
    if src_dir:
        print(f"[*] Copying bundled TeamTalkPy from {src_dir}...")
        for fname in ["TeamTalk5.py", "__init__.py"]:
            shutil.copy2(os.path.join(src_dir, fname), os.path.join(dest_teamtalkpy, fname))
        if src_dll and os.path.isfile(src_dll):
            shutil.copy2(src_dll, os.path.join(dest_teamtalkpy, "TeamTalk5.dll"))
            shutil.copy2(src_dll, os.path.join(target_dir, "TeamTalk5.dll"))
    else:
        print("[!] No bundled assets found. You may need to run '--action download-sdk'.")

    # 2. Create config.json
    config_file = os.path.join(target_dir, "config.json")
    if not os.path.isfile(config_file) or force:
        config_data = {
            "server": {
                "host": "127.0.0.1",
                "tcp_port": 10333,
                "udp_port": 10333,
                "encrypted": False
            },
            "auth": {
                "nickname": bot_name,
                "username": "guest",
                "password": "",
                "client_name": f"{bot_name}_PyBot"
            },
            "channel": {
                "auto_join": True,
                "channel_id": 0,
                "password": ""
            },
            "bot": {
                "command_prefix": "!",
                "reconnect_delay_sec": 5,
                "log_level": "INFO"
            }
        }
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)
        print("    [+] Created: config.json")

    # 3. Create bot.py (standard robust boilerplate)
    bot_file = os.path.join(target_dir, "bot.py")
    if not os.path.isfile(bot_file) or force:
        bot_code = '''import os
import sys
import time
import json
import logging
import signal

# Ensure local teamtalkpy and current directory are on sys.path & DLL directory
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
TEAMTALKPY_DIR = os.path.join(CURRENT_DIR, "teamtalkpy")

if os.path.isdir(TEAMTALKPY_DIR) and TEAMTALKPY_DIR not in sys.path:
    sys.path.insert(0, TEAMTALKPY_DIR)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

if sys.platform == "win32" and sys.version_info >= (3, 8):
    for d in [CURRENT_DIR, TEAMTALKPY_DIR]:
        if os.path.isdir(d):
            try:
                os.add_dll_directory(d)
            except OSError:
                pass

from TeamTalk5 import (
    TeamTalk, ClientEvent, TextMessage, TextMsgType,
    ttstr, UserAccount, User, Channel, buildTextMessage
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TeamTalkBot")


class BaseTeamTalkBot(TeamTalk):
    def __init__(self, config_path="config.json"):
        super().__init__()
        self.config = self.load_config(config_path)
        self.running = False
        self.logged_in = False
        self.my_user_id = 0

    def load_config(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    # ------------------ TeamTalk Event Callbacks ------------------

    def onConnectSuccess(self):
        logger.info("Connected to TeamTalk server successfully.")
        auth = self.config["auth"]
        cmd_id = self.doLogin(
            ttstr(auth["nickname"]),
            ttstr(auth["username"]),
            ttstr(auth["password"]),
            ttstr(auth["client_name"])
        )
        logger.info(f"Sent login command (CmdID: {cmd_id})")

    def onConnectFailed(self):
        logger.error("Connection to TeamTalk server failed.")
        self.running = False

    def onConnectionLost(self):
        logger.warning("Connection to server lost. Reconnecting in %s seconds...", self.config["bot"]["reconnect_delay_sec"])
        self.logged_in = False
        time.sleep(self.config["bot"]["reconnect_delay_sec"])
        self.start_connection()

    def onCmdMyselfLoggedIn(self, userid: int, useraccount: UserAccount):
        self.my_user_id = userid
        self.logged_in = True
        logger.info("Successfully logged in! My UserID: %d", userid)

        # Auto-join channel if enabled
        ch_conf = self.config["channel"]
        if ch_conf.get("auto_join"):
            target_ch = ch_conf.get("channel_id", 0)
            if target_ch == 0:
                target_ch = self.getRootChannelID()
            self.doJoinChannelByID(target_ch, ttstr(ch_conf.get("password", "")))
            logger.info("Joining channel ID: %d", target_ch)

    def onCmdUserTextMessage(self, msg: TextMessage):
        content = ttstr(msg.szMessage)
        sender_id = msg.nFromUserID
        sender_user = ttstr(msg.szFromUsername)

        # Ignore own messages
        if sender_id == self.my_user_id:
            return

        logger.info("TextMsg from %s (User %d, Type %d): %s", sender_user, sender_id, msg.nMsgType, content)

        # Handle command prefix
        prefix = self.config["bot"].get("command_prefix", "!")
        if content.startswith(prefix):
            self.handle_command(content[len(prefix):].strip(), msg)

    def handle_command(self, cmd_line: str, msg: TextMessage):
        parts = cmd_line.split()
        if not parts:
            return
        cmd = parts[0].lower()
        args = parts[1:]

        logger.info("Executing command '%s' with args %s", cmd, args)

        if cmd == "ping":
            self.reply_text("pong!", msg)
        elif cmd == "help":
            self.reply_text("Available commands: !ping, !help, !info", msg)
        elif cmd == "info":
            srv = self.getServerProperties()
            info_str = f"Server: {ttstr(srv.szServerName)} | Protocol: {ttstr(srv.szServerProtocolVersion)}"
            self.reply_text(info_str, msg)

    def reply_text(self, text: str, original_msg: TextMessage):
        reply = TextMessage()
        reply.nMsgType = original_msg.nMsgType
        reply.nChannelID = original_msg.nChannelID
        reply.nToUserID = original_msg.nFromUserID
        reply.szMessage = ttstr(text)
        self.doTextMessage(reply)

    # ------------------ Lifecycle & Loop ------------------

    def start_connection(self):
        srv = self.config["server"]
        logger.info("Connecting to %s:%d (UDP: %d)...", srv["host"], srv["tcp_port"], srv["udp_port"])
        success = self.connect(
            ttstr(srv["host"]),
            srv["tcp_port"],
            srv["udp_port"],
            0,
            0,
            srv.get("encrypted", False)
        )
        if not success:
            logger.error("Failed to initiate connect.")
            return False
        return True

    def run(self):
        self.running = True
        if not self.start_connection():
            return

        logger.info("Bot event loop started. Press Ctrl+C to terminate.")
        try:
            while self.running:
                self.runEventLoop(100)
        except KeyboardInterrupt:
            logger.info("Received stop signal.")
        finally:
            self.stop()

    def stop(self):
        self.running = False
        if self.logged_in:
            logger.info("Logging out...")
            self.doLogout()
        self.disconnect()
        self.closeTeamTalk()
        logger.info("Bot terminated cleanly.")


if __name__ == "__main__":
    bot = BaseTeamTalkBot()
    bot.run()
'''
        with open(bot_file, "w", encoding="utf-8") as f:
            f.write(bot_code)
        print("    [+] Created: bot.py")

    # 4. Create requirements.txt
    req_file = os.path.join(target_dir, "requirements.txt")
    if not os.path.isfile(req_file) or force:
        with open(req_file, "w", encoding="utf-8") as f:
            f.write("# TeamTalk5 SDK uses standard Python ctypes - no external dependencies required for core.\n")
            f.write("# Optional audio/media packages:\n# requests>=2.28.0\n# python-dotenv>=1.0.0\n")
        print("    [+] Created: requirements.txt")

    # 5. Create .gitignore
    gi_file = os.path.join(target_dir, ".gitignore")
    if not os.path.isfile(gi_file) or force:
        with open(gi_file, "w", encoding="utf-8") as f:
            f.write("__pycache__/\n*.pyc\n.env\n*.log\n")
        print("    [+] Created: .gitignore")

    # 6. Create README.md
    readme_file = os.path.join(target_dir, "README.md")
    if not os.path.isfile(readme_file) or force:
        readme_content = f"""# {bot_name}

A Python TeamTalk 5 bot created with the TeamTalk Bot Development Skill.

## Prerequisites
- **Python 3.8+ (64-bit)**
- **Windows 10/11 x64** or **Ubuntu 20.04+ x64**
- TeamTalk 5 Server (local or remote)

## Project Structure
- `bot.py`: Main bot code and event handlers.
- `config.json`: Server connection, credentials, and bot settings.
- `teamtalkpy/`: TeamTalk 5 Python wrapper and `TeamTalk5.dll`.

## Running the Bot
```bash
python bot.py
```
"""
        with open(readme_file, "w", encoding="utf-8") as f:
            f.write(readme_content)
        print("    [+] Created: README.md")

    print("\n[+] Project initialized successfully! Run 'python bot.py' to start.")
    return True


def download_sdk(platform_key="win64", output_dir=None, keep_archive=False):
    """Download TeamTalk SDK and extract essential runtime files only."""
    if platform_key not in SDK_DOWNLOAD_URLS:
        print(f"[X] Unsupported platform key '{platform_key}'. Choices: {list(SDK_DOWNLOAD_URLS.keys())}")
        return False

    url = SDK_DOWNLOAD_URLS[platform_key]
    dest_dir = output_dir or os.path.join(SKILL_ROOT, "downloads")
    os.makedirs(dest_dir, exist_ok=True)

    archive_name = url.split("/")[-1]
    archive_path = os.path.join(dest_dir, archive_name)

    print(f"[*] Downloading TeamTalk 5 SDK from: {url}")
    print(f"    Destination: {archive_path}")

    try:
        def reporthook(count, block_size, total_size):
            if total_size > 0:
                percent = int(count * block_size * 100 / total_size)
                sys.stdout.write(f"\r    Progress: {percent}% ({count * block_size // 1024} KB)")
                sys.stdout.flush()

        urllib.request.urlretrieve(url, archive_path, reporthook)
        print("\n[+] Download completed.")
    except Exception as e:
        print(f"\n[X] Download failed: {e}")
        return False

    # Extract archive using 7z if available
    extract_target = os.path.join(dest_dir, "extracted")
    os.makedirs(extract_target, exist_ok=True)
    print(f"[*] Extracting {archive_name}...")

    extracted = False
    try:
        # Check if 7z or 7za is available
        cmd = ["7z", "x", "-y", f"-o{extract_target}", archive_path]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode == 0:
            extracted = True
    except FileNotFoundError:
        pass

    if not extracted:
        # Try python py7zr or powershell
        try:
            import py7zr
            with py7zr.SevenZipFile(archive_path, mode='r') as z:
                z.extractall(extract_target)
            extracted = True
        except ImportError:
            print("[!] '7z' command or 'py7zr' python library not found.")
            print(f"[!] Please extract '{archive_path}' manually to '{extract_target}'.")

    if extracted:
        print("[+] Extracted SDK successfully.")
        clean_extracted_sdk(extract_target)

    if not keep_archive and os.path.isfile(archive_path):
        os.remove(archive_path)
        print("    [+] Removed archive file to save disk space.")

    return True


def clean_extracted_sdk(extracted_dir):
    """Retain only TeamTalk5.dll and TeamTalkPy, removing redundant folders."""
    print(f"[*] Cleaning redundant files from: {extracted_dir}")
    # Search for TeamTalk5.dll and TeamTalkPy
    kept_files = []
    for root, dirs, files in os.walk(extracted_dir):
        for f in files:
            if f in ["TeamTalk5.dll", "TeamTalk5.py", "__init__.py"]:
                kept_files.append(os.path.join(root, f))

    print(f"    Found {len(kept_files)} essential runtime files.")
    # Stash essential files into clean folder
    clean_dir = os.path.join(extracted_dir, "essential_runtime")
    os.makedirs(clean_dir, exist_ok=True)
    for f in kept_files:
        shutil.copy2(f, clean_dir)
        print(f"    Preserved: {os.path.basename(f)}")

    # Remove all other directories in extracted_dir except essential_runtime
    for item in os.listdir(extracted_dir):
        item_path = os.path.join(extracted_dir, item)
        if item_path != clean_dir:
            if os.path.isdir(item_path):
                shutil.rmtree(item_path, ignore_errors=True)
            else:
                os.remove(item_path)

    print("[+] Redundant SDK files cleaned up. Kept only DLL and Python wrapper.")


def main():
    parser = argparse.ArgumentParser(description="TeamTalk Bot Setup and Diagnostics Tool")
    parser.add_argument("action", choices=["init", "check", "fix", "download-sdk", "clean"],
                        help="Action to perform: init (new project), check (diagnose), fix (repair), download-sdk (fetch SDK)")
    parser.add_argument("--target-dir", "-t", default=".", help="Target project directory (default: current directory)")
    parser.add_argument("--bot-name", "-n", default="TeamTalkBot", help="Name for the bot project")
    parser.add_argument("--platform", "-p", default=detect_platform_key(), choices=list(SDK_DOWNLOAD_URLS.keys()), help="Target platform for SDK download")
    parser.add_argument("--force", "-f", action="store_true", help="Force overwrite existing files during init")

    args = parser.parse_args()

    if args.action == "init":
        init_project(target_dir=args.target_dir, bot_name=args.bot_name, force=args.force)
    elif args.action == "check":
        check_project(target_dir=args.target_dir, auto_fix=False)
    elif args.action == "fix":
        check_project(target_dir=args.target_dir, auto_fix=True)
    elif args.action == "download-sdk":
        download_sdk(platform_key=args.platform)
    elif args.action == "clean":
        clean_extracted_sdk(args.target_dir)


if __name__ == "__main__":
    main()
