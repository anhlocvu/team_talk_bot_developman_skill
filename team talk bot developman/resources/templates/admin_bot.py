"""
TeamTalk 5 Admin & Moderation Bot Template
==========================================
Demonstrates channel management, operator actions, kick/ban/move commands,
and querying server statistics. Requires admin/operator account rights on the server.
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
    UserAccount, Channel, ChannelType, ServerStatistics
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AdminBot")


class AdminBot(TeamTalk):
    def __init__(self, config_file="config.json"):
        super().__init__()
        with open(config_file, "r", encoding="utf-8") as f:
            self.config = json.load(f)
        self.running = False

    def onConnectSuccess(self):
        auth = self.config["auth"]
        self.doLogin(ttstr(auth["nickname"]), ttstr(auth["username"]), ttstr(auth["password"]), ttstr(auth["client_name"]))

    def onCmdMyselfLoggedIn(self, userid: int, useraccount: UserAccount):
        logger.info("Admin bot logged in. UserID: %d. Rights: 0x%08X", userid, useraccount.uUserRights)
        self.doJoinChannelByID(self.getRootChannelID(), ttstr(""))

    def onCmdUserTextMessage(self, msg: TextMessage):
        content = ttstr(msg.szMessage).strip()
        if msg.nFromUserID == self.getMyUserID():
            return

        parts = content.split()
        if not parts:
            return
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd == "!kick" and args:
            try:
                target_user_id = int(args[0])
                user = self.getUser(target_user_id)
                self.doKickUser(target_user_id, user.nChannelID)
                self.reply(f"Kicked User ID {target_user_id} from channel.", msg)
            except Exception as e:
                self.reply(f"Failed to kick user: {e}", msg)

        elif cmd == "!ban" and args:
            try:
                target_user_id = int(args[0])
                user = self.getUser(target_user_id)
                self.doBanUser(target_user_id, user.nChannelID)
                self.reply(f"Banned User ID {target_user_id}.", msg)
            except Exception as e:
                self.reply(f"Failed to ban user: {e}", msg)

        elif cmd == "!move" and len(args) >= 2:
            try:
                target_user_id = int(args[0])
                dest_channel_id = int(args[1])
                self.doMoveUser(target_user_id, dest_channel_id)
                self.reply(f"Moved user {target_user_id} to channel {dest_channel_id}.", msg)
            except Exception as e:
                self.reply(f"Failed to move user: {e}", msg)

        elif cmd == "!makechannel" and args:
            ch_name = " ".join(args)
            new_ch = Channel()
            new_ch.nParentID = self.getRootChannelID()
            new_ch.szName = ttstr(ch_name)
            new_ch.szTopic = ttstr("Created by AdminBot")
            new_ch.uChannelType = ChannelType.CHANNEL_DEFAULT
            new_ch.nMaxUsers = 50
            cmd_id = self.doMakeChannel(new_ch)
            self.reply(f"Created channel '{ch_name}' (CmdID: {cmd_id}).", msg)

        elif cmd == "!stats":
            self.doQueryServerStats()
            self.pending_stats_reply = msg

    def onServerStatistics(self, stats: ServerStatistics):
        if hasattr(self, "pending_stats_reply") and self.pending_stats_reply:
            msg = (
                f"Server Stats: Users served: {stats.nUsersServed} (Peak: {stats.nUsersPeak}) | "
                f"Uptime: {stats.nUptimeMSec // 1000}s | "
                f"Voice TX/RX: {stats.nVoiceBytesTX // 1024} KB / {stats.nVoiceBytesRX // 1024} KB"
            )
            self.reply(msg, self.pending_stats_reply)
            self.pending_stats_reply = None

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
            self.disconnect()
            self.closeTeamTalk()


if __name__ == "__main__":
    bot = AdminBot()
    bot.run()
