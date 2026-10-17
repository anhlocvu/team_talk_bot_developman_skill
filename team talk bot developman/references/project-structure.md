# TeamTalk 5 Bot Project Structure & Runtime Guide

This guide explains how to properly structure, configure, and maintain a Python TeamTalk 5 bot project.

---

## 1. Recommended Project Layout

A robust TeamTalk 5 bot project should follow this clean layout:

```text
my_teamtalk_bot/
├── bot.py                  # Main bot entrypoint (event loop, commands, logic)
├── config.json             # Configuration (host, ports, credentials, channel, prefix)
├── requirements.txt        # Python dependencies (minimal; ctypes is standard library)
├── .env.example            # Environment variables template (optional)
├── .gitignore              # Standard gitignore (logs, pycache, .env)
├── README.md               # Setup and usage instructions
├── sounds/                 # Audio files for streaming (.mp3, .wav)
│   └── welcome.wav
└── teamtalkpy/             # Self-contained TeamTalk 5 runtime
    ├── __init__.py         # Package marker
    ├── TeamTalk5.py        # Object-oriented ctypes wrapper
    └── TeamTalk5.dll       # Native C++ SDK client engine (64-bit on Windows)
```

> [!TIP]
> Placing `TeamTalk5.dll` directly inside the `teamtalkpy/` folder (or at project root) ensures that the bot is completely self-contained and portable across machines without requiring global SDK installation.

---

## 2. DLL Resolution & Windows Python 3.8+ Rules

In Python 3.8 and later on Windows, the operating system's default DLL search behavior changed significantly. Directories on `PATH` or the script's directory are no longer searched by `ctypes.cdll` unless explicitly declared using `os.add_dll_directory()`.

### Safe DLL Loading Boilerplate
Include this snippet at the top of your `bot.py` or entrypoint before importing `TeamTalk5`:

```python
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
TEAMTALKPY_DIR = os.path.join(CURRENT_DIR, "teamtalkpy")

# Add directories to sys.path
for d in [CURRENT_DIR, TEAMTALKPY_DIR]:
    if os.path.isdir(d) and d not in sys.path:
        sys.path.insert(0, d)

# Add directories to native DLL search path (Windows Python >= 3.8)
if sys.platform == "win32" and sys.version_info >= (3, 8):
    for d in [CURRENT_DIR, TEAMTALKPY_DIR]:
        if os.path.isdir(d):
            try:
                os.add_dll_directory(d)
            except OSError:
                pass
```

---

## 3. Architecture & Bitness Matching

> [!CRITICAL]
> The bitness of the Python interpreter **MUST** match the bitness of `TeamTalk5.dll`:
> - 64-bit `TeamTalk5.dll` requires **64-bit Python** (`AMD64`).
> - 32-bit `TeamTalk5.dll` requires **32-bit Python** (`x86`).
> Mixing 32-bit Python with a 64-bit DLL will fail with: `[WinError 193] %1 is not a valid Win32 application`.

To check your Python bitness:
```bash
python -c "import struct; print(struct.calcsize('P') * 8, 'bit Python')"
```

---

## 4. Multi-Platform Support (Linux & macOS)

### Linux (Ubuntu 20.04+, Debian, Raspbian)
1. On Linux, the native library is named `libTeamTalk5.so`.
2. Place `libTeamTalk5.so` in your `teamtalkpy/` directory or system library path (`/usr/local/lib/`).
3. Set `LD_LIBRARY_PATH` when running:
   ```bash
   export LD_LIBRARY_PATH=$(pwd)/teamtalkpy:$LD_LIBRARY_PATH
   python bot.py
   ```

### Headless Server Notes
If running on a Linux VPS without a sound card:
- You do NOT need audio input/output devices to send/receive text messages, admin actions, or stream media files (`startStreamingMediaFileToChannel`).
- For sound card simulation, use ALSA dummy driver (`modprobe snd-dummy`) or PulseAudio null-sink.

---

## 5. Configuration File Design (`config.json`)

Keep credentials and server settings out of code:

```json
{
  "server": {
    "host": "127.0.0.1",
    "tcp_port": 10333,
    "udp_port": 10333,
    "encrypted": false
  },
  "auth": {
    "nickname": "HelperBot",
    "username": "guest",
    "password": "",
    "client_name": "HelperBot_v1"
  },
  "channel": {
    "auto_join": true,
    "channel_id": 0,
    "password": ""
  },
  "bot": {
    "command_prefix": "!",
    "reconnect_delay_sec": 5,
    "log_level": "INFO"
  }
}
```

---

## 6. Project Diagnostic & Repair Checklist

Use the bundled setup script to diagnose any project anytime:
```bash
python scripts/setup_teamtalk_bot.py check --target-dir path/to/bot
```

If files are missing or broken, auto-repair with:
```bash
python scripts/setup_teamtalk_bot.py fix --target-dir path/to/bot
```

| Check Item | Requirement | Resolution |
|---|---|---|
| Python Version | Python 3.8+ | Upgrade Python |
| Python Bitness | 64-bit | Install 64-bit Python |
| `TeamTalk5.py` | Present in `teamtalkpy/` or root | Copy from `resources/teamtalkpy/` |
| `TeamTalk5.dll` | Present in `teamtalkpy/` or root | Copy from `resources/teamtalkpy/` |
| `config.json` | Present and valid JSON | Create from template |
| Import Test | `TeamTalk5.getVersion()` succeeds | Verify DLL bitness and dependencies |
