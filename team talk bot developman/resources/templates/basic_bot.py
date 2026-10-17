"""
Basic TeamTalk 5 Bot Template
============================
Handles connection, authentication, channel joining, text message commands,
and clean event dispatching.
"""

import os
import sys
import time
import json
import logging

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
    ttstr, UserAccount, User, Channel, buildTextMessage, rebuildTextMessage
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TeamTalkBasicBot")


class BasicBot(TeamTalk):
    def __init__(self, config_file="config.json"):
        super().__init__()
        self.config = self.load_config(config_file)
        self.running = False
        self.my_user_id = 0

    def load_config(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    # ------------------ TeamTalk Events ------------------

    def onConnectSuccess(self):
        logger.info("Connected to TeamTalk server.")
        auth = self.config["auth"]
        cmd_id = self.doLogin(
            ttstr(auth["nickname"]),
            ttstr(auth["username"]),
            ttstr(auth["password"]),
            ttstr(auth["client_name"])
        )
        logger.info("Login command sent (cmd_id=%d).", cmd_id)

    def onConnectFailed(self):
        logger.error("Connection failed.")
        self.running = False

    def onConnectionLost(self):
        logger.warning("Connection lost. Retrying in 5 seconds...")
        time.sleep(5)
        self.connect_to_server()

    def onCmdMyselfLoggedIn(self, userid: int, useraccount: UserAccount):
        self.my_user_id = userid
        logger.info("Logged in as UserID: %d", userid)

        # Join designated channel or root
        target_channel = self.config.get("channel", {}).get("channel_id", 0)
        if target_channel == 0:
            target_channel = self.getRootChannelID()
        password = self.config.get("channel", {}).get("password", "")
        self.doJoinChannelByID(target_channel, ttstr(password))
        logger.info("Joining channel ID: %d", target_channel)

    def onCmdUserTextMessage(self, msg: TextMessage):
        content = ttstr(msg.szMessage)
        sender_id = msg.nFromUserID
        sender_name = ttstr(msg.szFromUsername)

        if sender_id == self.my_user_id:
            return  # Do not respond to self

        logger.info("[%s] (User %d): %s", sender_name, sender_id, content)

        prefix = self.config.get("bot", {}).get("command_prefix", "!")
        if content.startswith(prefix):
            self.execute_command(content[len(prefix):].strip(), msg)

    def execute_command(self, cmd_line: str, msg: TextMessage):
        parts = cmd_line.split()
        if not parts:
            return
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd == "ping":
            self.send_reply("pong!", msg)
        elif cmd == "echo":
            self.send_reply(" ".join(args), msg)
        elif cmd == "users":
            users = self.getServerUsers()
            names = [ttstr(u.szNickname) for u in users]
            self.send_reply(f"Online users ({len(names)}): {', '.join(names)}", msg)
        elif cmd == "help":
            self.send_reply("Commands: !ping, !echo <text>, !users, !help", msg)

    def send_reply(self, text: str, original_msg: TextMessage):
        reply = TextMessage()
        reply.nMsgType = original_msg.nMsgType
        reply.nChannelID = original_msg.nChannelID
        reply.nToUserID = original_msg.nFromUserID
        reply.szMessage = ttstr(text)
        self.doTextMessage(reply)

    # ------------------ Runner ------------------

    def connect_to_server(self):
        srv = self.config["server"]
        return self.connect(
            ttstr(srv["host"]),
            srv["tcp_port"],
            srv["udp_port"],
            0,
            0,
            srv.get("encrypted", False)
        )

    def run(self):
        self.running = True
        if not self.connect_to_server():
            logger.error("Could not issue connect command.")
            return

        logger.info("Event loop running. Press Ctrl+C to stop.")
        try:
            while self.running:
                self.runEventLoop(100)
        except KeyboardInterrupt:
            logger.info("Exiting...")
        finally:
            self.stop()

    def stop(self):
        self.running = False
        self.doLogout()
        self.disconnect()
        self.closeTeamTalk()
        logger.info("Clean shutdown complete.")


if __name__ == "__main__":
    bot = BasicBot()
    bot.run()
