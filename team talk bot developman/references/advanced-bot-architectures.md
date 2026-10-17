# Advanced TeamTalk 5 Bot Architectures & Real-World Blueprints

This document synthesizes production-proven design patterns, architectural blueprints, and engineering techniques extracted from two battle-tested, high-grade TeamTalk 5 bots:
1. **`TTMediaBot`**: A high-fidelity, studio-grade media streaming engine for Windows leveraging `libmpv`, WASAPI, `yt-dlp`, real-time synchronized lyrics/subtitles on status messages, hybrid song recognition, and audio DSP.
2. **`TTUtilities`**: An enterprise-grade server moderation, community engagement, and multi-featured utility bot built via direct object-oriented `TeamTalk` subclassing, featuring auto-jail flood protection, VPN detection, multi-engine TTS, automatic translation, dynamic private channels, and gettext localization.

Both template source trees are available in the skill's `resources/templates/` directory (`TTMediaBot` and `TTUtilities`) for direct inspection.

---

## 1. Blueprint A: High-Fidelity Media Streaming Engine (`TTMediaBot`)

### 1.1 Architecture Overview

Standard TeamTalk file streaming (`startStreamingMediaFileToChannel`) is limited to basic local playback without fine-grained seeking, buffering, or format flexibility. `TTMediaBot` demonstrates the **C-API MPV Injection Architecture**:

```text
[Media Source: YouTube / Local / Stream / Web]
                       │
                 (yt-dlp Engine)
                       │
                       ▼
          [MPV Core via ctypes (mpv.dll)]
          ├── Rubber Band v3 (Pitch Shift)
          ├── Silence Trimming (Filter graph)
          ├── 256MB Lookahead Buffer Cache
          └── WASAPI Audio Output (Bit-perfect, ultra-low latency)
                       │
                       ▼
          [Virtual Audio Cable / Sound Input Device]
                       │
                       ▼
          [TeamTalk 5 Engine (TeamTalk5.dll)]
          ├── initSoundInputDevice()
          ├── enableVoiceTransmission(True)
          └── doChangeStatus() (Live Subtitle / Lyrics Display)
```

### 1.2 Core Components & Implementation Patterns

#### A. Direct C-API `mpv` Integration
Rather than running `mpv.exe` as a subprocess, `TTMediaBot` uses `mpv.py` to bind directly to `mpv.dll` (libmpv C-API via `ctypes`):
- Provides programmatic event handling (`mpv.MpvEventId.PROPERTY_CHANGE`, `END_FILE`).
- Real-time property control: `time-pos`, `duration`, `pause`, `volume`, `pitch`.
- Zero subprocess startup overhead.

```python
# Initializing MPV with WASAPI and aggressive buffer settings
import mpv

player = mpv.MPV(
    ao="wasapi",                     # Native Windows Audio Session API
    audio_device="wasapi/{GUID}",   # Direct routing to Virtual Audio Cable
    ytdl=False,                      # Handled natively by Python yt-dlp
    demuxer_max_bytes=256 * 1024 * 1024,  # 256MB RAM cache
    demuxer_readahead_secs=3600,     # Up to 1-hour lookahead
    audio_pitch_correction=False     # Managed via Rubber Band filter
)
```

#### B. Live Synchronized Lyrics & Subtitles on Status Message
A breakthrough feature in `TTMediaBot` is streaming lyrics/subtitles in real-time onto the bot's TeamTalk status message (`szStatusMsg`):
- Fetches `.srt`, `.vtt`, or synced lyrics (`LRCLIB`, `Musixmatch`, YouTube ASR).
- Tracks playback timestamp (`time-pos` property event from `mpv`).
- Dispatches status update calls through `TeamTalk.doChangeStatus()`:

```python
def update_live_subtitle(bot: TeamTalk, subtitle_line: str):
    """Update bot status string with current lyric line in real-time."""
    current_status = bot.getMyStatusMessage()
    if subtitle_line and current_status != subtitle_line:
        # Status message length is limited by TT_STRLEN (512 chars)
        bot.doChangeStatus(0, ttstr(subtitle_line[:250]))
```

#### C. Windows Process Priority Scheduling
To prevent audio dropouts, glitches, and stuttering during CPU spikes or multitasking, elevate the process priority:

```python
import sys
import ctypes

def optimize_process_priority():
    """Set process priority to HIGH or REALTIME on Windows."""
    if sys.platform == "win32":
        try:
            # HIGH_PRIORITY_CLASS = 0x00000080
            # REALTIME_PRIORITY_CLASS = 0x00000100
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetCurrentProcess()
            kernel32.SetPriorityClass(handle, 0x00000080)
        except Exception:
            pass
```

#### D. Hybrid Multi-Tier Song Recognition
`TTMediaBot` integrates a 3-tier fallback engine to identify any playing music in 3 to 5 seconds:
1. **Tier 1 (YouTube Chapters)**: Instant metadata extraction if available.
2. **Tier 2 (Shazam API)**: Concurrent audio slice capture (10-second mono WAV) for studio/commercial music.
3. **Tier 3 (Google Speech Voice AI)**: Recognition for live performances, spoken audio, or acoustic covers.

#### E. Studio Audio DSP (Pitch Shifting & Silence Trimming)
- **Pitch Shift**: Uses MPV's `rubberband` filter:
  ```python
  player.command("af", "add", "@pitch:rubberband=pitch-scale=1.059463") # +1 semitone
  ```
- **Silence Trimming**: Automatically skips dead silence at track start/end:
  ```python
  player.command("af", "add", "@silence:silenceremove=start_periods=1:start_threshold=-50dB")
  ```

---

## 2. Blueprint B: Enterprise Server Moderation & Community Suite (`TTUtilities`)

### 2.1 Architecture Overview

`TTUtilities` demonstrates the **Subclassing Event Architecture**:
Instead of wrapping `TeamTalk` inside a helper class, the bot subclass directly inherits from `TeamTalk5.TeamTalk`. This gives direct, unhindered access to all 118 native C-API methods and internal callback overrides:

```text
                  class TeamTalk (C-API Wrapper)
                                │
                                ▼
                   class TTUtilities(TeamTalk)
    ├── Event Handlers (onConnectSuccess, onUserTextMessage, ...)
    ├── Config Handler (configparser / INI format)
    ├── Auto-Moderation Engine (Jail, Blacklist, VPN, Duration Ban)
    ├── Audio & Speech Engine (gTTS, msspeech, YT Player)
    ├── Localization Module (gettext, multi-language catalogs)
    └── Dynamic Channel Manager (Temporary private rooms)
```

### 2.2 Core Components & Implementation Patterns

#### A. Event-Driven Direct Subclassing
```python
from TeamTalk5 import TeamTalk, TextMessage, User, Channel, ttstr

class ServerOpsBot(TeamTalk):
    def __init__(self, config):
        super().__init__()
        self.config = config
        
    def onConnectSuccess(self):
        # Authenticate immediately upon connection
        self.doLogin(
            ttstr(self.config["bot_nick"]),
            ttstr(self.config["username"]),
            ttstr(self.config["password"]),
            ttstr("ServerOps_v1.0")
        )
        
    def onCmdMyselfLoggedIn(self, userid: int, useraccount):
        # Join designated control or home channel
        self.doJoinChannelByID(self.config["home_channel_id"], ttstr(""))
        
    def onCmdUserTextMessage(self, msg: TextMessage):
        if msg.nFromUserID == self.getMyUserID():
            return
        self.handle_command_or_moderation(msg)
```

#### B. Smart Jail System & Flood Protection
Automatically isolate offending users into a restricted jail channel. If they attempt to switch channels or bypass the jail, trigger immediate punishment:

```python
class JailController:
    def __init__(self, bot: TeamTalk, jail_channel_id: int):
        self.bot = bot
        self.jail_channel_id = jail_channel_id
        self.jailed_users = {}  # {user_id: {"attempts": int, "until": timestamp}}
        
    def jail_user(self, user_id: int, duration_sec: int = 300):
        self.jailed_users[user_id] = {
            "attempts": 0,
            "until": time.time() + duration_sec
        }
        self.bot.doMoveUser(user_id, self.jail_channel_id)
        
    def handle_user_moved(self, user_id: int, new_channel_id: int):
        """Called inside onCmdUserJoinedChannel event."""
        if user_id in self.jailed_users:
            if new_channel_id != self.jail_channel_id:
                # Jail bypass attempt detected!
                self.jailed_users[user_id]["attempts"] += 1
                if self.jailed_users[user_id]["attempts"] > 3:
                    # Repeated violation: escalate to ban
                    self.bot.doBanUser(user_id)
                else:
                    # Force return to jail
                    self.bot.doMoveUser(user_id, self.jail_channel_id)
```

#### C. Multi-Engine Text-to-Speech (TTS)
Inject spoken announcements or user text into the channel:
1. **Edge TTS / MSSpeech**: High-quality neural voices in multiple languages.
2. **Google TTS (`gTTS`)**: Reliable fallback.
3. **Audio Routing**: Synthesize audio to a temporary file, then invoke `startStreamingMediaFileToChannel()`, or feed directly into sound input device.

#### D. Dynamic Hidden Private Channels
Enables two users to request a private conference:
1. Bot executes `doMakeChannel(new_channel)`.
2. Generates a secure, cryptographically random password (`secrets.token_urlsafe(16)`).
3. Sets channel properties: `CHANNEL_SOLITARY` or hidden flags.
4. Moves both users into the channel and dispatches the temporary password via private `TextMessage`.
5. Watches for channel exit; deletes the channel once both users leave.

#### E. INI Configuration & Gettext Internationalization
`TTUtilities` uses `configparser` (`config.ini`) to allow human-readable server administration, combined with standard Python `gettext` (`locales/`) for multilingual prompt delivery:

```python
import gettext
import configparser

config = configparser.ConfigParser()
config.read("config.ini", encoding="utf-8")

# Setup locale
lang = config.get("Bot", "language", fallback="en")
try:
    trans = gettext.translation("messages", localedir="locales", languages=[lang])
    trans.install()
    _ = trans.gettext
except Exception:
    _ = lambda s: s
```

---

## 3. Comparison Matrix: Choosing the Right Architecture

| Feature / Goal | Standard Bot Recipe | `TTMediaBot` Blueprint | `TTUtilities` Blueprint |
| :--- | :--- | :--- | :--- |
| **Primary Focus** | Simple Commands & Alerts | Studio Music & Audio DSP | Moderation & Community Ops |
| **Audio Quality** | Default TeamTalk Streamer | Audiophile (WASAPI + MPV) | Mixed (TTS + Streamer) |
| **Media Sources** | Local `.mp3`/`.wav` only | YouTube, Streams, Local, Playlists | Local, YouTube, TTS |
| **Seeking & Cache** | Limited | 256MB RAM Cache + Lookahead | Standard |
| **Subtitles / Lyrics**| None | Live Status Message Sync | None |
| **Auto-Moderation** | Basic Kick/Ban commands | None | Advanced (Jail, Blacklist, VPN) |
| **Config Format** | `config.json` | `config.json` | `config.ini` |
| **Code Structure** | Single-file script | Modular package (`bot/`, `services/`) | Modular package (`bot/`, `locales/`) |

---

## 4. Key Takeaways for AI Agents

1. **Do not reinvent audio streaming from scratch**: If the user asks for high-quality audio, YouTube playback, or lyrics, reference `TTMediaBot`'s `mpv` integration and WASAPI setup.
2. **Do not reinvent moderation or channel automation**: If the user asks for auto-jail, bad word filtering, temporary channels, or TTS, reference `TTUtilities`.
3. **Inspect the actual source trees**: AI agents should read the files directly in `resources/templates/TTMediaBot/` and `resources/templates/TTUtilities/` for implementation details.
