# TeamTalk 5 Bot Project Structure & Runtime Guide

This guide explains how to properly structure, configure, and maintain a Python TeamTalk 5 bot project.

---

## 1. Project Layouts: Basic vs. Modular Architectures

### 1.1 Basic Single-File Bot Layout
Ideal for lightweight utility bots, echo bots, and soundboards:

```text
my_teamtalk_bot/
├── bot.py                  # Main bot entrypoint (event loop, commands, logic)
├── config.json             # Configuration (host, ports, credentials, channel, prefix)
├── requirements.txt        # Python dependencies (minimal; ctypes is standard library)
├── .gitignore              # Standard gitignore (logs, pycache, .env)
├── README.md               # Setup and usage instructions
├── sounds/                 # Audio files for streaming (.mp3, .wav)
│   └── welcome.wav
├── TeamTalk5.dll           # Placed in root for direct os.getcwd() SDK resolution
└── teamtalkpy/             # Self-contained TeamTalk 5 runtime
    ├── __init__.py         # Package marker
    ├── TeamTalk5.py        # Stock, unmodified official SDK wrapper
    └── TeamTalk5.dll       # Native C++ SDK client engine (64-bit on Windows)
```

### 1.2 Enterprise Modular Bot Layout (e.g. `TTMediaBot` & `TTUtilities`)
Ideal for media streaming engines, complex moderation systems, and multi-language bots:

```text
my_enterprise_bot/
├── entrypoint.py           # Launcher (UTF-8 console setup, safe DLL loading, priority)
├── config.json (or .ini)   # Rich configuration file
├── requirements.txt        # Dependencies (yt-dlp, mpv, gTTS, requests, etc.)
├── TeamTalk5.dll           # 64-bit native DLL in working directory
├── mpv.dll                 # (Optional) MPV C-API library for studio streaming
├── TeamTalk_DLL/           # Alternative SDK location recognized by stock TeamTalk5.py
│   └── TeamTalk5.dll
├── teamtalkpy/             # Stock TeamTalk SDK wrapper (read-only)
│   ├── __init__.py
│   └── TeamTalk5.py
├── bot/                    # Modular application package
│   ├── __init__.py         # Bot class definition (subclassing TeamTalk)
│   ├── commands/           # Modular command handlers
│   ├── player/             # Audio playback and DSP controllers
│   ├── moderation/         # Jail, blacklist, flood protection
│   ├── services/           # Speech synthesis, translation, web APIs
│   └── utils.py            # Process priority, string helpers, signal traps
└── locales/                # Internationalization translation catalogs (.mo, .po)
    ├── en/LC_MESSAGES/
    └── vi/LC_MESSAGES/
```

> [!IMPORTANT]
> **Stock SDK Integrity Rule**:
> Never modify `TeamTalk5.py` to fix DLL loading paths. Always keep it identical to the official BearWare distribution. By placing `TeamTalk5.dll` in the current working directory (`os.getcwd()`), or inside a sibling `TeamTalk_DLL/` folder, or by invoking `os.add_dll_directory()` in the entrypoint script, `TeamTalk5.py` loads successfully without altering a single line of SDK code.

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
