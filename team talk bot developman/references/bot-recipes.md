# TeamTalk 5 Bot Recipes & Implementation Patterns

This document contains complete, tested patterns for common TeamTalk 5 bot archetypes.

---

## Recipe 1: Echo & Interactive Command Bot

A general-purpose chatbot that handles user commands, manages arguments, and responds cleanly to both channel and private messages.

```python
import os
import sys
import json
import logging
from TeamTalk5 import TeamTalk, TextMessage, TextMsgType, ttstr, UserAccount

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("EchoBot")


class EchoBot(TeamTalk):
    def __init__(self, config_path="config.json"):
        super().__init__()
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)
        self.running = False
        self.my_user_id = 0

    def onConnectSuccess(self):
        auth = self.config["auth"]
        self.doLogin(ttstr(auth["nickname"]), ttstr(auth["username"]), ttstr(auth["password"]), ttstr(auth["client_name"]))

    def onCmdMyselfLoggedIn(self, userid: int, useraccount: UserAccount):
        self.my_user_id = userid
        logger.info("Bot authenticated as UserID %d", userid)
        self.doJoinChannelByID(self.config.get("channel", {}).get("channel_id", self.getRootChannelID()), ttstr(""))

    def onCmdUserTextMessage(self, msg: TextMessage):
        content = ttstr(msg.szMessage).strip()
        sender_id = msg.nFromUserID
        if sender_id == self.my_user_id:
            return

        prefix = self.config.get("bot", {}).get("command_prefix", "!")
        if not content.startswith(prefix):
            return

        cmd_parts = content[len(prefix):].split()
        if not cmd_parts:
            return
        cmd = cmd_parts[0].lower()
        args = cmd_parts[1:]

        if cmd == "ping":
            self.reply("pong!", msg)
        elif cmd == "echo":
            self.reply(" ".join(args) if args else "Usage: !echo <message>", msg)
        elif cmd == "whoami":
            user = self.getUser(sender_id)
            info = f"Nickname: {ttstr(user.szNickname)} | Username: {ttstr(user.szUsername)} | IP: {ttstr(user.szIPAddress)}"
            self.reply(info, msg)

    def reply(self, text: str, original_msg: TextMessage):
        reply_msg = TextMessage()
        reply_msg.nMsgType = original_msg.nMsgType
        reply_msg.nChannelID = original_msg.nChannelID
        reply_msg.nToUserID = original_msg.nFromUserID
        reply_msg.szMessage = ttstr(text)
        self.doTextMessage(reply_msg)

    def run(self):
        srv = self.config["server"]
        self.connect(ttstr(srv["host"]), srv["tcp_port"], srv["udp_port"])
        self.running = True
        try:
            while self.running:
                self.runEventLoop(100)
        except KeyboardInterrupt:
            pass
        finally:
            self.disconnect()
            self.closeTeamTalk()
```

---

## Recipe 2: Soundboard & Audio Streamer Bot

Allows users in the channel to trigger sound effects stored in a local directory (`sounds/`).

```python
import os
import json
import logging
from TeamTalk5 import TeamTalk, TextMessage, ttstr, UserAccount

logger = logging.getLogger("SoundboardBot")


class SoundboardBot(TeamTalk):
    def __init__(self, sounds_dir="sounds", config_path="config.json"):
        super().__init__()
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)
        self.sounds_dir = os.path.abspath(sounds_dir)
        os.makedirs(self.sounds_dir, exist_ok=True)
        self.current_stream = None

    def onConnectSuccess(self):
        auth = self.config["auth"]
        self.doLogin(ttstr(auth["nickname"]), ttstr(auth["username"]), ttstr(auth["password"]), ttstr(auth["client_name"]))

    def onCmdMyselfLoggedIn(self, userid: int, useraccount: UserAccount):
        self.doJoinChannelByID(self.config.get("channel", {}).get("channel_id", self.getRootChannelID()), ttstr(""))

    def onCmdUserTextMessage(self, msg: TextMessage):
        content = ttstr(msg.szMessage).strip()
        if msg.nFromUserID == self.getMyUserID():
            return

        if content == "!list":
            files = [f for f in os.listdir(self.sounds_dir) if f.lower().endswith(('.mp3', '.wav'))]
            self.send_text("Sounds: " + (", ".join(files) if files else "Empty"), msg)
        elif content.startswith("!play "):
            track = content[6:].strip()
            self.play_sound(track, msg)
        elif content == "!stop":
            self.stop_sound(msg)

    def play_sound(self, name: str, msg: TextMessage):
        target_path = os.path.join(self.sounds_dir, name)
        if not os.path.isfile(target_path):
            self.send_text(f"Sound '{name}' not found. Use !list.", msg)
            return

        self.stopStreamingMediaFileToChannel()
        success = self.startStreamingMediaFileToChannel(ttstr(target_path), None)
        if success:
            self.current_stream = name
            self.send_text(f"Playing '{name}'...", msg)
        else:
            self.send_text(f"Could not stream '{name}'.", msg)

    def stop_sound(self, msg: TextMessage):
        self.stopStreamingMediaFileToChannel()
        self.current_stream = None
        self.send_text("Playback stopped.", msg)

    def send_text(self, text: str, original_msg: TextMessage):
        m = TextMessage()
        m.nMsgType = original_msg.nMsgType
        m.nChannelID = original_msg.nChannelID
        m.nToUserID = original_msg.nFromUserID
        m.szMessage = ttstr(text)
        self.doTextMessage(m)
```

---

## Recipe 3: Channel Gatekeeper & Welcome Bot

Automatically greets new users who enter the channel and announces departures.

```python
from TeamTalk5 import TeamTalk, TextMessage, TextMsgType, ttstr, User

class GatekeeperBot(TeamTalk):
    def onCmdUserJoinedChannel(self, user: User):
        # Triggered whenever a user enters a channel
        if user.nChannelID == self.getMyChannelID() and user.nUserID != self.getMyUserID():
            welcome_msg = f"Welcome to the channel, {ttstr(user.szNickname)}!"
            self.broadcast_channel(welcome_msg)

    def onCmdUserLeftChannel(self, channelid: int, user: User):
        # Triggered whenever a user exits a channel
        if channelid == self.getMyChannelID() and user.nUserID != self.getMyUserID():
            bye_msg = f"{ttstr(user.szNickname)} has left the channel."
            self.broadcast_channel(bye_msg)

    def broadcast_channel(self, text: str):
        msg = TextMessage()
        msg.nMsgType = TextMsgType.MSGTYPE_CHANNEL
        msg.nChannelID = self.getMyChannelID()
        msg.szMessage = ttstr(text)
        self.doTextMessage(msg)
```

---

## Recipe 4: Handling Long Messages (>512 Chars)

When text output exceeds `TT_STRLEN` (512 characters), split and send it as a sequence of linked messages using `buildTextMessage`:

```python
from TeamTalk5 import TeamTalk, buildTextMessage, TextMsgType, ttstr

def send_long_message(bot: TeamTalk, text: str, target_channel_id: int):
    # Splits text into 512-byte chunks with bMore flag set correctly
    packets = buildTextMessage(
        text,
        nMsgType=TextMsgType.MSGTYPE_CHANNEL,
        szFromUsername="",
        nChannelID=target_channel_id,
        nToUserID=0
    )
    for p in packets:
        bot.doTextMessage(p)
```

---

## Recipe 5: Running as a 24/7 Linux Systemd Service

Create `/etc/systemd/system/teamtalk-bot.service`:

```ini
[Unit]
Description=TeamTalk 5 Python Bot Service
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/home/botuser/my_teamtalk_bot
Environment="LD_LIBRARY_PATH=/home/botuser/my_teamtalk_bot/teamtalkpy"
ExecStart=/usr/bin/python3 /home/botuser/my_teamtalk_bot/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now teamtalk-bot
```
