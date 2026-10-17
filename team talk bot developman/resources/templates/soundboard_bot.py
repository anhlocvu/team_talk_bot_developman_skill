"""
TeamTalk 5 Soundboard & Media Streaming Bot Template
===================================================
Demonstrates playing local audio files (MP3/WAV) into a TeamTalk channel
using startStreamingMediaFileToChannel and stopStreamingMediaFileToChannel.
"""

import os
import sys
import json
import logging

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
    TeamTalk, TextMessage, TextMsgType, ttstr,
    UserAccount, Channel, MediaFileInfo
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SoundboardBot")


class SoundboardBot(TeamTalk):
    def __init__(self, config_file="config.json"):
        super().__init__()
        with open(config_file, "r", encoding="utf-8") as f:
            self.config = json.load(f)
        self.running = False
        self.is_streaming = False
        self.sounds_dir = os.path.join(CURRENT_DIR, "sounds")
        os.makedirs(self.sounds_dir, exist_ok=True)

    def onConnectSuccess(self):
        auth = self.config["auth"]
        self.doLogin(ttstr(auth["nickname"]), ttstr(auth["username"]), ttstr(auth["password"]), ttstr(auth["client_name"]))

    def onCmdMyselfLoggedIn(self, userid: int, useraccount: UserAccount):
        target_channel = self.config.get("channel", {}).get("channel_id", self.getRootChannelID())
        self.doJoinChannelByID(target_channel, ttstr(""))
        logger.info("Bot logged in (ID %d) and joined channel %d", userid, target_channel)

    def onCmdUserTextMessage(self, msg: TextMessage):
        content = ttstr(msg.szMessage).strip()
        if msg.nFromUserID == self.getMyUserID():
            return

        if content.startswith("!play "):
            filename = content[6:].strip()
            self.play_audio(filename, msg)
        elif content == "!stop":
            self.stop_audio(msg)
        elif content == "!list":
            files = [f for f in os.listdir(self.sounds_dir) if f.lower().endswith(('.mp3', '.wav', '.ogg'))]
            self.reply("Available sounds: " + (", ".join(files) if files else "No audio files in /sounds"), msg)

    def play_audio(self, filename: str, request_msg: TextMessage):
        file_path = os.path.join(self.sounds_dir, filename)
        if not os.path.isfile(file_path):
            self.reply(f"File not found: {filename}. Type !list to see available sounds.", request_msg)
            return

        if self.is_streaming:
            self.stopStreamingMediaFileToChannel()
            self.is_streaming = False

        logger.info("Streaming audio file to channel: %s", file_path)
        # Passing None for VideoCodec since we are streaming audio only
        success = self.startStreamingMediaFileToChannel(ttstr(file_path), None)
        if success:
            self.is_streaming = True
            self.reply(f"Playing '{filename}'...", request_msg)
        else:
            self.reply(f"Failed to stream audio file '{filename}'. Check format and permissions.", request_msg)

    def stop_audio(self, request_msg: TextMessage):
        if self.is_streaming:
            self.stopStreamingMediaFileToChannel()
            self.is_streaming = False
            self.reply("Audio playback stopped.", request_msg)
        else:
            self.reply("No audio is currently playing.", request_msg)

    def onStreamMediaFile(self, info: MediaFileInfo):
        # Triggered when media file streaming status changes
        logger.info("Media file status: duration=%d ms", info.nDurationMSec)

    def reply(self, text: str, original_msg: TextMessage):
        m = TextMessage()
        m.nMsgType = original_msg.nMsgType
        m.nChannelID = original_msg.nChannelID
        m.nToUserID = original_msg.nFromUserID
        m.szMessage = ttstr(text)
        self.doTextMessage(m)

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
            if self.is_streaming:
                self.stopStreamingMediaFileToChannel()
            self.disconnect()
            self.closeTeamTalk()


if __name__ == "__main__":
    bot = SoundboardBot()
    bot.run()
