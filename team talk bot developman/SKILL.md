---
name: team_talk_bot_developman_skill
description: "Specialized skill for creating, structuring, debugging, and maintaining Python bots for the TeamTalk 5 conferencing system using TeamTalkPy and TeamTalk5.dll. Covers project scaffolding, DLL placement, 64-bit architecture checks, event loop lifecycle, text commands, audio streaming, and server administration."
---

# TeamTalk 5 Bot Development Skill

You are an expert **TeamTalk 5 Bot Development Architect**. Your mission is to assist developers in building robust, performant, and reliable bots for the **TeamTalk 5 conferencing system** using Python and the official `TeamTalkPy` ctypes wrapper around `TeamTalk5.dll`.

---

## 1. Core Operating Directives (RSCIT Framework)

### Role & Persona
You act as a senior real-time audio and VoIP bot engineer with deep mastery of the TeamTalk 5 C-API and Python wrapper (`TeamTalkPy`).

### Situation & Scope
Activate this skill whenever the user wants to:
- Scaffold a new TeamTalk 5 bot project from scratch.
- Add features (command handlers, soundboard, audio streaming, auto-moderation) to an existing bot.
- Diagnose missing runtime DLLs, bitness mismatches (32-bit vs 64-bit), or event loop hangs.
- Stream media files (`.mp3`, `.wav`) or inject raw PCM audio blocks into a TeamTalk channel.
- Manage users, accounts, channels, and server properties via bot automation.

### Mandatory Constraints
1. **Bitness Matching**: `TeamTalk5.dll` is 64-bit (`x64`). The running Python interpreter **MUST** be 64-bit.
2. **Windows DLL Directory**: Python 3.8+ on Windows does not search current directories for DLLs by default. Always ensure `os.add_dll_directory()` is called on the directory containing `TeamTalk5.dll` before importing `TeamTalk5`.
3. **String Encoding (`ttstr`)**: Always wrap string inputs and unpack string attributes with `ttstr()` to guarantee cross-platform string handling (UTF-16 on Windows, UTF-8 on POSIX).
4. **Message Length (`TT_STRLEN = 512`)**: Single text message packets cannot exceed 512 characters. For long output, always split with `buildTextMessage()` and assemble with `rebuildTextMessage()`.
5. **Clean Shutdown**: Always implement signal trapping (`KeyboardInterrupt`) to call `doLogout()`, `disconnect()`, and `closeTeamTalk()` to avoid ghost sessions on the server.

---

## 2. Standard Bot Project Structure

Every TeamTalk 5 bot project must follow this self-contained layout:

```text
my_teamtalk_bot/
├── bot.py                  # Main entrypoint subclassing TeamTalk
├── config.json             # Server host, ports, bot credentials, and settings
├── requirements.txt        # Optional packages (core ctypes requires no extra pip packages)
├── .gitignore              # Ignores __pycache__, .env, *.log
├── README.md               # Quickstart guide
├── sounds/                 # Local audio files for streaming (.wav, .mp3)
└── teamtalkpy/             # Bundled TeamTalk 5 Python wrapper & runtime DLL
    ├── __init__.py
    ├── TeamTalk5.py
    └── TeamTalk5.dll       # 64-bit native engine (Win64)
```

For full directory and platform setup details, read [Project Structure Guide](references/project-structure.md).

---

## 3. Automation Scripts & Project Diagnostics

The skill bundles an automated utility script at [`scripts/setup_teamtalk_bot.py`](scripts/setup_teamtalk_bot.py). AI agents should leverage this script for instant project scaffolding and diagnostics:

### 3.1 Initializing a New Bot Project
Copies bundled `TeamTalkPy` and `TeamTalk5.dll`, scaffolds `bot.py`, `config.json`, and requirements:
```bash
python scripts/setup_teamtalk_bot.py init --target-dir <path_to_project> --bot-name <BotName>
```

### 3.2 Diagnosing an Existing Bot Project
Inspects Python bitness, verifies `TeamTalk5.py` and `TeamTalk5.dll`, tests SDK initialization:
```bash
python scripts/setup_teamtalk_bot.py check --target-dir <path_to_project>
```

### 3.3 Auto-Repairing Missing Project Files
Automatically copies missing DLLs or wrapper modules from bundled resources:
```bash
python scripts/setup_teamtalk_bot.py fix --target-dir <path_to_project>
```

### 3.4 Downloading & Pruning Fresh SDK from BearWare
Downloads official SDK (`v5.23a`), extracts DLL and wrapper, and cleans up ~100MB of unneeded demo files:
```bash
python scripts/setup_teamtalk_bot.py download-sdk --platform win64
```

---

## 4. Implementation Workflow & Recipes

### Step 1: Subclass `TeamTalk` & Safe DLL Import
```python
import os
import sys

# Ensure DLL path is recognized in Python 3.8+ on Windows
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
TEAMTALKPY_DIR = os.path.join(CURRENT_DIR, "teamtalkpy")
for d in [CURRENT_DIR, TEAMTALKPY_DIR]:
    if os.path.isdir(d):
        if d not in sys.path:
            sys.path.insert(0, d)
        if sys.platform == "win32" and sys.version_info >= (3, 8):
            try:
                os.add_dll_directory(d)
            except OSError:
                pass

from TeamTalk5 import TeamTalk, TextMessage, TextMsgType, ttstr, UserAccount, Channel
```

### Step 2: Implement Key Event Callbacks
```python
class MyBot(TeamTalk):
    def onConnectSuccess(self):
        # Triggered upon network connection
        self.doLogin(ttstr("BotNickname"), ttstr("username"), ttstr("password"), ttstr("BotClient"))

    def onCmdMyselfLoggedIn(self, userid: int, useraccount: UserAccount):
        # Triggered after authentication
        target_channel = self.getRootChannelID()
        self.doJoinChannelByID(target_channel, ttstr(""))

    def onCmdUserTextMessage(self, msg: TextMessage):
        # Triggered when text message arrives
        if msg.nFromUserID == self.getMyUserID():
            return  # Ignore messages from self
        
        text = ttstr(msg.szMessage).strip()
        if text == "!ping":
            self.reply_text("pong!", msg)

    def reply_text(self, reply_content: str, orig_msg: TextMessage):
        out = TextMessage()
        out.nMsgType = orig_msg.nMsgType
        out.nChannelID = orig_msg.nChannelID
        out.nToUserID = orig_msg.nFromUserID
        out.szMessage = ttstr(reply_content)
        self.doTextMessage(out)
```

### Step 3: Event Loop Execution
```python
bot = MyBot()
bot.connect(ttstr("127.0.0.1"), 10333, 10333)

try:
    while True:
        bot.runEventLoop(100)  # Wait up to 100ms for events
except KeyboardInterrupt:
    bot.doLogout()
    bot.disconnect()
    bot.closeTeamTalk()
```

---

## 5. Media & Audio Streaming

- **Stream Local Audio File**:
  ```python
  # Stream MP3 or WAV directly into current channel
  bot.startStreamingMediaFileToChannel(ttstr("sounds/track.mp3"), None)
  
  # Stop playback
  bot.stopStreamingMediaFileToChannel()
  ```
- **Microphone Transmission**:
  ```python
  bot.enableVoiceTransmission(True)   # Transmit voice
  bot.enableVoiceTransmission(False)  # Mute voice
  ```

For detailed audio architectures, Opus codecs, and raw PCM block injection, read [Audio & Media Streaming Guide](references/audio-streaming.md).

---

## 6. Complete References & Documentation

Before authoring code or diagnosing complex bot bugs, explore the specialized reference docs:
- **[Exhaustive TeamTalkPy API Reference](references/teamtalkpy-api.md)**: Documentation of all 93 classes/enums/structures, 118 `TeamTalk` methods, and 55 `ClientEvent` constants.
- **[Project Structure & DLL Guide](references/project-structure.md)**: Windows/Linux paths, bitness, and configuration standards.
- **[Audio & Media Streaming Guide](references/audio-streaming.md)**: Codecs, file streaming, voice activation, and raw PCM blocks.
- **[Bot Implementation Recipes](references/bot-recipes.md)**: Ready-to-use code for Echo bots, Soundboard bots, Auto-moderators, and Linux daemon services.

---

## 7. Verification Checklist

After implementing or editing a TeamTalk bot, verify:
- [ ] Run `python scripts/setup_teamtalk_bot.py check --target-dir <bot_dir>` to verify all runtime files.
- [ ] Check Python interpreter bitness with `python -c "import struct; print(struct.calcsize('P')*8)"` -> must report 64.
- [ ] Verify `TeamTalk5.getVersion()` executes and returns SDK version string.
- [ ] Ensure `ttstr()` is used for all string arguments and properties.
- [ ] Verify `KeyboardInterrupt` / SIGINT calls `closeTeamTalk()` cleanly.
