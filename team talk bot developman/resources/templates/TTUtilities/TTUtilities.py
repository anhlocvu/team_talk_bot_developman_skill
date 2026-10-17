# -*- coding: utf-8 -*
from TeamTalk5 import TeamTalk, User, UserType, UserAccount, UserRight, TextMessage, BanType, ttstr, BannedUser, TextMsgType, Subscription, TTMessage, VideoCodec, Channel, ChannelType, AudioCodec, OpusCodec, Codec, OPUS_APPLICATION_VOIP, RemoteFile
import TeamTalk5
import gettext
import logging
import time
from datetime import datetime
import re
import configparser
import os
import requests
import json
import zipfile
import sys
import argparse
import subprocess
from tqdm import tqdm
import random
import threading
from threading import Thread, Lock
from concurrent.futures import ThreadPoolExecutor
import paramiko
import wikipedia
import langdetect
from gtts import gTTS
from msspeech import MSSpeech
import asyncio
import ast
from deep_translator import GoogleTranslator
from bot.config_handler import ConfigHandler
from bot.help import HelpCommands
import string
import yt_dlp
from bot.player import Player
from bot.account import Account

def load_messages(filename):
    with open(filename, "r", encoding="utf-8") as f:
        messages = [line.strip() for line in f]
    return messages

def load_blacklist(filename):
    with open(filename, "r", encoding="utf-8") as f:
        blacklist = [line.strip().lower() for line in f]
    return blacklist

if not os.path.exists("files"):
    os.makedirs("files")


class TTUtilities(TeamTalk):
    config_handler = ConfigHandler()
    help_commands=HelpCommands()
    user_speech_settings = {}
    duration_kicks = {}
    pending_kicks = {}
    banned_users = {}
    private_channels = {}
    private_channel_lock = Lock()
    download_in_progress = False
    upload_timers = {}
    pending_uploads = {}
    notifications = {}
    username_notifications = {}
    user_messages = {}

    def __init__(self, cookiefile=None):
        super().__init__()
        # Load config from the config handler
        self.server_config = self.config_handler.get_server_config()
        self.bot_config = self.config_handler.get_bot_config()
        self.playback_config = self.config_handler.get_playback_config()
        self.telegram_config = self.config_handler.get_telegram_config()
        self.exclusion_config = self.config_handler.get_exclusion_config()
        self.accounts_config = self.config_handler.get_accounts_config()
        self.weather_config = self.config_handler.get_weather_config()
        self.ssh_config = self.config_handler.get_ssh_config()
        self.teamtalk_license_config = self.config_handler.get_teamtalk_license_config()
        self.just_joined = True
        self.detection_mode = None
        self.custom_username = ""
        self.excluded_ips = []
        self.doSubscribe(0, Subscription.SUBSCRIBE_USER_MSG)
        self.encrypted=False
        self.user_ip_info = {}
        self.user_join_timers={}
        self.auto_translate = False
        self.source_lang = None
        self.target_lang = None
        self.last_translated_message = None
        self.translation_pool = ThreadPoolExecutor(max_workers=1)
        self.translate_lock = threading.Lock()
        self.last_t_command_time=0
        self.user_translation_modes = {}
        self.user_translation_cooldowns = {}
        self.char_limit_mode=None
        self.blacklist_mode=None
        self.speech_engine = MSSpeech()
        self.user_speech_settings = {}
        self.speech_thread = None
        self.voice_thread = None
        self.duration_bans = {}
        self.last_command_sender_id = None
        self.last_command_sender_username = None
        self.commands = self.help_commands.commands
        self.cookiefile = cookiefile
        self.player = Player(cookiefile=self.cookiefile)
        self.account_creator=Account()
        self.player.end_callback = self.on_playback_end
        self.loading_new_track = False

        # Set language
        self.language = self.bot_config.get("language")
        gettext.bindtextdomain("messages", "locales")
        gettext.textdomain("messages")
  
        try:
            translation = gettext.translation("messages", "locales", [self.language])
            translation.install()
            self._ = _
        except FileNotFoundError:
            print(f"Language '{self.language}' not found, defaulting to English.")
            translation = gettext.translation("messages", "locales", ["en"])
            translation.install()
            self._ = gettext.gettext

        if self.teamtalk_license_config['license_name'] is not None and self.teamtalk_license_config['license_key'] is not None:
            TeamTalk5.setLicense(ttstr(self.teamtalk_license_config['license_name']), ttstr(self.teamtalk_license_config['license_key']))

        self.check_for_updates()
        try:
            print(self._("Initializing audio devices..."))
            self.initSoundInputDevice(self.playback_config['input_device'])
            print(self._("Audio devices Initialized."))
        except Exception as e:
            print(self._("Error while initializing audio devices: {e}").format(e=e))

        try:
            self.connect(ttstr(self.server_config["address"]), self.server_config["port"], self.server_config["port"], bEncrypted=self.server_config["encrypted"])
        except:
            print(self._("Error, Please check your config file and try again, or recreate your config file by deleting existing file and then run the bot"))
            input(self._("Press Enter to quit..."))
            sys.exit(1)

    def generate_password(self, length=random.randint(15, 32)):
        """Generates a random password of specified length."""
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for i in range(length))

    def check_for_updates(self):
        current_version = "3.0"
        update_url = "https://blindmasters.org/TTUtilities/version.txt"
        if sys.platform == 'windows':
            download_url = "https://blindmasters.org/TTUtilities/TTUtilities.zip"
        else:
            download_url = "https://blindmasters.org/TTUtilities/TTUtilities-linux.zip"

        try:
            response = requests.get(update_url)
            response.raise_for_status()

            server_version = response.text.strip()

            if server_version > current_version:
                print(self._("A new version has been detected: {server_version}").format(server_version=server_version))
                response = requests.get(download_url, stream=True)
                response.raise_for_status()

                total_size = int(response.headers.get('content-length', 0))
                block_size = 4096
                with open("TTUtilities.zip", "wb") as f:
                    for data in tqdm(response.iter_content(block_size), total=total_size / block_size, unit='KiB'):
                        f.write(data)

                with zipfile.ZipFile("TTUtilities.zip", "r") as zip_ref:
                    zip_ref.extractall(".")

                print(self._("Update downloaded and extracted successfully!"))
                input(self._("Press Enter to quit."))
                sys.exit(0)
            else:
                print(self._("No updates found."))

        except requests.exceptions.RequestException:
            print(self._("Failed to check for updates"))

    def onConnectSuccess(self):
        print(self._("Connected successfully!"))
        self.doLogin(ttstr(self.bot_config["nickname"]), ttstr(self.server_config["username"]), ttstr(self.server_config["password"]), ttstr(self.bot_config["client_name"]))

    def onConnectFailed(self):
        print(self._("Could not connect to server {server_address} port={port}").format(server_address=self.server_config["address"], port=self.server_config["port"]))
        print(self._("Trying to reconnect."))
        self.reconnect()

    def onConnectionLost(self):
        print(self._("Connection lost. Trying to reconnect..."))
        self.reconnect()

    def reconnect(self):
        time.sleep(3)
        os.execv(sys.executable, [sys.executable] + sys.argv)
        os._exit(0)

    def onCmdMyselfLoggedIn(self, userid, useraccount):
        print(self._("Logged in successfully"))
        while True:
            channel_id=self.getChannelIDFromPath(ttstr(self.bot_config['default_channel']))
            if channel_id == 0 or channel_id is None:
                continue
            else:
                break
        self.doJoinChannelByID(channel_id, ttstr(self.bot_config['channel_password']))
        self.subscribe_user_messages()
        self.subscribe_channel_messages()
        if self.bot_config["status_message"] is not None:
            self.doChangeStatus(ttstr(self.bot_config["gender"]), ttstr(self.bot_config["status_message"]))
        else:
            self.doChangeStatus(ttstr(self.bot_config["gender"]), ttstr(""))

    def onCmdMyselfKickedFromChannel(self, channelid, user):
        print(self._("I've been kicked from the channel. Reconnecting in 5 seconds..."))
        time.sleep(5)
        self.doLogin(ttstr(self.bot_config["nickname"]), ttstr(self.server_config["username"]), ttstr(self.server_config["password"]), ttstr(self.bot_config["client_name"]))
        time.sleep(0.1)
        self.doJoinChannelByID(self.getRootChannelID(), ttstr(""))
        time.sleep(0.1)
        self.subscribe_user_messages()
        self.subscribe_channel_messages()
        time.sleep(0.1)
        if self.bot_config["status_message"] is not None:
            self.doChangeStatus(ttstr(self.bot_config["gender"]), ttstr(self.bot_config["status_message"]))
        else:
            self.doChangeStatus(ttstr(self.bot_config["gender"]), ttstr(""))
        time.sleep(0.1)
        self.send_broadcast_message(self._("Hey! Why did you kick me?"))

        self.config_handler.read_config_file()

    def subscribe_user_messages(self):
        users = self.getServerUsers()
        my_user_id = self.getMyUserID()

        for user in users:
            if user.nUserID != my_user_id:
                self.doSubscribe(user.nUserID, Subscription.SUBSCRIBE_USER_MSG)
                if self.bot_config['intercept_channel_messages'] is True:
                    self.doSubscribe(user.nUserID, 131072)
                    print(self._("intercepting channel messages for user {user}").format(user=ttstr(user.szNickname)))
                print(self._("subscribed to user messages for user {user}").format(user=ttstr(user.szNickname)))

    def subscribe_channel_messages(self):
        channel_id = self.getMyChannelID()

        result = self.doSubscribe(channel_id, Subscription.SUBSCRIBE_CHANNEL_MSG)
        print(self._("Subscribed to channel messages"))

    def handle_user_command(self, textmessage: TextMessage):
        user_id = textmessage.nFromUserID
        user=self.getUser(user_id)
        if ttstr(textmessage.szMessage).startswith(self._("/rate")):
            try:
                _, rate_value = textmessage.szMessage.split()
                rate_value = int(rate_value)
                if -100 <= rate_value <= 100:
                    self.user_speech_settings.setdefault(user_id, {})["rate"] = rate_value
                    self.privateMessage(user_id, self._("Rate set to {rate}.").format(rate=rate_value))
                else:
                    self.privateMessage(user_id, self._("Invalid rate value. Rate should be between -100 and 100."))
            except ValueError:
                self.privateMessage(user_id, self._("Invalid command. Usage: /rate <rate_value>."))
        elif ttstr(textmessage.szMessage).startswith(self._("/pitch")):
            try:
                _, pitch_value = textmessage.szMessage.split()
                pitch_value = int(pitch_value)
                if -100 <= pitch_value <= 100:
                    self.user_speech_settings.setdefault(user_id, {})["pitch"] = pitch_value
                    self.privateMessage(user_id, self._("Pitch set to {pitch}.").format(pitch=pitch_value))
                else:
                    self.privateMessage(user_id, self._("Invalid pitch value. Pitch should be between -100 and 100."))
            except ValueError:
                self.privateMessage(user_id, self._("Invalid command. Usage: /pitch <pitch_value>"))
        elif ttstr(textmessage.szMessage).startswith(self._("/volume")):
            try:
                _, volume_value = textmessage.szMessage.split()
                volume_value = float(volume_value)
                if 0.1 <= volume_value <= 1.0:
                    self.user_speech_settings.setdefault(user_id, {})["volume"] = volume_value
                    self.privateMessage(user_id, self._("Volume set to {volume}.").format(volume=volume_value))
                else:
                    self.privateMessage(user_id, self._("Invalid volume value. Volume should be between 0.1 and 1.0."))
            except ValueError:
                self.privateMessage(user_id, self._("Invalid command. Usage: /volume <volume_value>"))
        elif ttstr(textmessage.szMessage).startswith(self._("/voice")) and " " in ttstr(textmessage.szMessage):
            try:
                _, voice_name = ttstr(textmessage.szMessage).split(" ", 1)
                self.user_speech_settings.setdefault(user_id, {})["voice"] = voice_name
                self.privateMessage(user_id, self._("Voice set to {voice_name}.").format(voice_name=voice_name))
            except ValueError:
                self.privateMessage(user_id, self._("Invalid command. Usage: /voice <voice_name>."))
        elif textmessage.szMessage== ttstr(self._("/s")):
            if user.nChannelID != self.getMyChannelID():
                self.privateMessage(textmessage.nFromUserID, self._("Sorry, You are not in the same channel"))
                return
            self.handle_stop(textmessage)

    def onCmdUserLoggedIn(self, user: User):
        if self.just_joined:
            self.just_joined = False
            return
        self.subscribe_user_messages()

        if self.accounts_config['detect_server_admins']==True:
            if user.uUserType==UserType.USERTYPE_ADMIN:
                if ttstr(user.szUsername) in self.accounts_config['authorized_users']:
                    pass
                else:
                    self.accounts_config['authorized_users'].append(ttstr(user.szUsername))

        nickname = ttstr(user.szNickname)
        if nickname in self.notifications:
            notification_data = self.notifications[nickname]
            user_id = notification_data["user_id"]
            telegram_chat_id = notification_data["telegram_chat_id"]

            self.send_telegram_notification(telegram_chat_id, self._("Hello. Important: The user {name} has logged in to the server.").format(name=nickname))
            del self.notifications[nickname]

        username = ttstr(user.szUsername)
        if username in self.username_notifications:
            notification_data = self.username_notifications[username]
            user_id = notification_data["user_id"]
            telegram_chat_id = notification_data["telegram_chat_id"]

            self.send_telegram_notification(telegram_chat_id, self._("Hello there. Important: The user {username} has logged in to the server.").format(username=username))
            del self.username_notifications[username]

        if username in self.user_messages:
            for sender_data in self.user_messages[username]:
                message = sender_data["message"]
                sender_username = sender_data["sender_username"] or "Unknown User"
                sender_nickname = sender_data["sender_nickname"]
                self.privateMessage(user.nUserID, self._("You have a message from {username} ({nickname}): {message}").format(username=sender_username, nickname=sender_nickname, message=message))
            del self.user_messages[username]

        if username and username in self.exclusion_config["usernames"] or \
           nickname and nickname in self.exclusion_config["nicknames"]:
            print(self._("User {nickname} is excluded, skipping action.").format(nickname=nickname))
            return

        if ttstr(user.szUsername) in self.bot_config["jail_users"] or ttstr(user.szNickname) in self.bot_config["jail_names"]:
            jail_channel_id = self.getChannelIDFromPath(ttstr(self.bot_config["jail_channel"]))
            self.doMoveUser(user.nUserID, jail_channel_id)

        if self.should_kick_user(user):
            self.kick_user(user.nUserID)
            return

        if ttstr(user.szIPAddress) in self.duration_bans:
            duration_seconds, end_time = self.duration_bans[user.szIPAddress]
            if time.time() < end_time:
                self.kick_user(user.nUserID)
            else:
                del self.duration_bans[user.szIPAddress]
        elif ttstr(user.szUsername) in self.duration_bans:
            duration_seconds, end_time = self.duration_bans[user.szUsername]
            if time.time() < end_time:
                self.kick_user(user.nUserID)
            else:
                del self.duration_bans[user.szUsername]

        if ttstr(user.szNickname) in self.pending_kicks or ttstr(user.szNickname).lower() in self.pending_kicks:
            kick_type, duration_seconds, end_time = self.pending_kicks[ttstr(user.szNickname).lower()]
            if time.time() < end_time:
                self.kick_user(user.nUserID)
                # Add to duration_kicks to prevent immediate re-entry
                user_data = (
                    ttstr(user.szNickname),
                    ttstr(user.szIPAddress),
                    ttstr(user.szUsername) if ttstr(user.szUsername) != "guest" and ttstr(user.szUsername) != self.accounts_config['custom_username'] else None,
                )

                self.duration_kicks[user_data] = (duration_seconds, end_time)
            del self.pending_kicks[ttstr(user.szNickname).lower()]

        # Check for pending kicks by username
        if ttstr(user.szUsername) in self.pending_kicks or ttstr(user.szUsername).lower() in self.pending_kicks:
            kick_type, duration_seconds, end_time = self.pending_kicks[ttstr(user.szUsername).lower()]
            if time.time() < end_time:
                self.kick_user(user.nUserID)
                user_data = (
                    ttstr(user.szNickname),
                    ttstr(user.szIPAddress),
                    ttstr(user.szUsername),
                )

                self.duration_kicks[user_data] = (duration_seconds, end_time)
            del self.pending_kicks[ttstr(user.szUsername).lower()]

        blacklist = load_blacklist("blacklist.txt")

        if self.accounts_config["detection_mode"] == 1:
            if ttstr(user.szUsername)!=ttstr("guest"):
                return
        elif self.accounts_config["detection_mode"] == 3:
            if ttstr(user.szUsername) != self.accounts_config["custom_username"]:
                return

        user_id = user.nUserID
        nickname_words = ttstr(user.szNickname.lower()).split()  # Split nickname into words

        if any(word in blacklist for word in nickname_words):
            if self.bot_config["blacklist_mode"]==1:
                self.kick_user(user_id)
            elif self.bot_config["blacklist_mode"]==2:
                self.ban_user(user_id, BanType.BANTYPE_USERNAME)
                self.kick_user(user_id)
            return

        if self.bot_config['prevent_noname'] is True:
            if ttstr(user.szNickname) == ttstr("") or re.match(r"^NoName\s*(?:-\s*#\d+)?$", ttstr(user.szNickname)):
                self.privateMessage(user_id, self.bot_config['noname_note'])
                self.kick_user(user.nUserID)
                return


        ip_address = ttstr(user.szIPAddress)

        if ip_address in self.exclusion_config["ips"]:
                return
        elif user.szNickname in self.duration_kicks:
            return

        if self.bot_config['vpn_detection'] == True:
            if self.is_vpn(ip_address):
                self.ban_user(user.nUserID, BanType.BANTYPE_IPADDR)
                self.send_broadcast_message(self._("{nickname} has been banned for using a VPN.").format(nickname=ttstr(user.szNickname)))
                self.kick_user(user.nUserID)

        if len(ttstr(user.szNickname)) > self.bot_config["char_limit"] and self.bot_config['char_limit'] > 0:
            if self.bot_config["char_limit_mode"]==1:
                self.send_broadcast_message(self._("{nickname} has been kicked due to username exceeding {chars} characters.").format(nickname=ttstr(user.szNickname), chars=self.bot_config["char_limit"]))
                self.privateMessage(user_id, self._("You have been kicked due to username exceeding {chars} characters.").format(chars=self.bot_config["char_limit"]))
                self.kick_user(user_id)
            elif self.bot_config["char_limit_mode"]==2:
                self.ban_user(user_id, BanType.BANTYPE_USERNAME)
                self.kick_user(user_id)

        country, city = self.get_user_location(user.nUserID)
        if country and city:
            if country.lower() in self.bot_config['banned_countries']:
                self.ban_user(user.nUserID, BanType.BANTYPE_USERNAME)
                self.send_broadcast_message(self._("Hey {nickname}, This is not the place for you and your country {country}. Go away.").format(nickname=ttstr(user.szNickname), country=country))
                self.kick_user(user.nUserID) 
                return
            else:
                welcome_messages = [
                    self._("Welcome, {nickname} from {country}!").format(nickname=ttstr(user.szNickname), country=country),
                    self._("Ahoy there, {nickname} from {country}! Welcome aboard!").format(nickname=ttstr(user.szNickname), country=country),
                    self._("Greetings, {nickname} of {country}! We're glad to have you here.").format(nickname=ttstr(user.szNickname), country=country),
                    self._("Howdy, {nickname}! Welcome from {country}.").format(nickname=ttstr(user.szNickname), country=country),
                    self._("Whoa! {nickname} just arrived from {country}! Let's party!").format(nickname=ttstr(user.szNickname), country=country),
                    self._("Look who's here! {nickname} from {country} just logged in!").format(nickname=ttstr(user.szNickname), country=country),
                    self._("Good vibes only for {nickname} from {country}! Welcome, my friend!").format(nickname=ttstr(user.szNickname), country=country),
                    self._("Surprise, surprise! It's {nickname} from {country}! Glad to have you!").format(nickname=ttstr(user.szNickname), country=country),
                    self._("Let the fun begin! Welcome, {nickname} from the land of {country}!").format(nickname=ttstr(user.szNickname), country=country)
                ]

                welcome_message = random.choice(welcome_messages)
                self.send_broadcast_message(welcome_message)

            if user.nUserID not in self.user_ip_info: # Store after checking ban
                self.user_ip_info[user.nUserID] = {"country": country, "city": city} 
        else:
            print(self._("cannot identify the country name for that IP address  likely due to an invalid IP address: {ip_address}").format(ip_address=ttstr(user.szIPAddress)))
            self.send_broadcast_message(self._("{nickname} has joined the server").format(nickname=ttstr(user.szNickname)))

    def should_kick_user(self, user: User):
        """Checks if the user should be kicked based on duration kick information."""
        for user_data in list(self.duration_kicks.keys()):
            (nickname, ip_address, username) = user_data
            (duration_seconds, end_time) = self.duration_kicks[user_data]

            if time.time() < end_time:
                if (nickname == ttstr(user.szNickname) or 
                    (ip_address == ttstr(user.szIPAddress) and username != "guest") or
                    (username == ttstr(user.szUsername) and username != "guest" and username != self.accounts_config['custom_username'])):
                    return True
            else:
                del self.duration_kicks[user_data]
        return False

    def send_telegram_notification(self, chat_id, message):
        """Sends a notification to the specified Telegram chat ID."""
        url = f"https://api.telegram.org/bot{self.telegram_config['telegram_bot_token']}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": message
        }
        try:
            response = requests.post(url, json=data)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(_("Error sending Telegram notification: {e}").format(e=e))

    def onCmdUserJoinedChannel(self, user: User):
        if ttstr(user.szUsername) in self.bot_config["jail_users"] or user.szNickname in self.bot_config["jail_names"]:
            jail_channel_id = self.getChannelIDFromPath(ttstr(self.bot_config["jail_channel"]))
            if user.nChannelID != jail_channel_id:
                self.doMoveUser(user.nUserID, jail_channel_id)  # Move user back to jail channel
                self.track_user_joins(user)

    def onCmdUserLeftChannel(self, channelid: int, user: User):
        user_id = user.nUserID
        if user_id in self.user_translation_modes:
            del self.user_translation_modes[user_id]
        if user_id in self.user_translation_cooldowns:
            del self.user_translation_cooldowns[user_id]
        self.cleanup_private_channel(user)

    def onCmdUserLoggedOut(self, user: User):
        user_id = user.nUserID
        if user_id in self.user_translation_modes:
            del self.user_translation_modes[user_id]
        if user_id in self.user_translation_cooldowns:
            del self.user_translation_cooldowns[user_id]
        if user_id in self.user_speech_settings:
            del self.user_speech_settings[user_id]
        if user_id in self.user_ip_info:
            del self.user_ip_info[user_id]
        self.cleanup_private_channel(user)

    def cleanup_private_channel(self, user: User):
        """Checks if a private channel needs to be deleted."""
        with self.private_channel_lock:
            channel_keys = list(self.private_channels.keys()) 

            for users in channel_keys:
                if ttstr(user.szNickname) in users:
                    self.doRemoveChannel(self.private_channels[users].nChannelID)
                    del self.private_channels[users]

    def track_user_joins(self, user: User):
        user_id = user.nUserID
        if user_id not in self.user_join_timers:
            self.user_join_timers[user_id] = {
                "start_time": time.time(),
                "join_count": 1
            }
            Thread(target=self.monitor_user_joins, args=(user_id,)).start()
        else:
            self.user_join_timers[user_id]["join_count"] += 1

    def monitor_user_joins(self, user_id):
        timer_data = self.user_join_timers[user_id]
        warning_sent = False  # Flag to keep track if warning has been sent
        while time.time() - timer_data["start_time"] < self.bot_config["jail_timer_seconds"]:
            if timer_data["join_count"] >=3 and not warning_sent:
                self.privateMessage(user_id, self._("Warning: You are trying to get out of the jail for more than 3 times, If you continue to spam: You'll be banned, I repeat: Do not spam"))
                warning_sent=True
            time.sleep(1)
            if timer_data["join_count"] >= self.bot_config["jail_flood_count"]:
                user = self.getUser(user_id)
                if ttstr(user.szUsername)=="guest":
                    self.ban_user(user_id, BanType.BANTYPE_IPADDR)
                else:
                    self.ban_user(user_id, BanType.BANTYPE_USERNAME)
                self.kick_user(user_id)
                self.send_broadcast_message(self._("{nickname} has been banned due to jail flood protection.").format(nickname=ttstr(user.szNickname)))
                break
        del self.user_join_timers[user_id]

    def split_long_message(self, message, chunk_size=500):
        chunks = []
        while message:
            chunk = message[:chunk_size]
            message = message[chunk_size:]
            if message:
                last_space = chunk.rfind(" ")
                if last_space != -1:
                    chunk = chunk[:last_space]
                    message = chunk[last_space + 1:] + message
            chunks.append(chunk)
        return chunks

    def onCmdUserTextMessage(self, textmessage: TextMessage):
        print(self._("Message received: {message} from {username}").format(message=ttstr(textmessage.szMessage), username=ttstr(textmessage.szFromUsername)))
        blacklist = load_blacklist("blacklist.txt")
        pattern = r"\b(" + "|".join(blacklist) + r")\b"

        if re.search(pattern, ttstr(textmessage.szMessage), re.IGNORECASE):
            streamer=TeamTalk5.VideoCodec()
            streamer.nCodec=1
            self.startStreamingMediaFileToChannel(ttstr(os.path.join("files", "blacklist.wav")), streamer)
            if self.bot_config['blacklist_mode']==1:
                self.kick_user(textmessage.nFromUserID)
            else:
                self.ban_user(textmessage.nFromUserID)
                self.kick_user(textmessage.nFromUserID)
            return

        if textmessage.szMessage.startswith(ttstr(self._("/weather"))):
            command, *rest = ttstr(textmessage.szMessage).split(maxsplit=1)
            sender_user_id = textmessage.nFromUserID
            sender_channel_id = self.getUser(sender_user_id).nChannelID

            if rest:
                target_user = self.getUserByName(rest[0])
                if not target_user:
                    if textmessage.nMsgType == 1:
                        self.privateMessage(sender_user_id, self._("User '{user}' not found.").format(user=rest[0]))
                    else:
                        self.send_message(self._("User '{user}' not found.").format(user=rest[0]), sender_channel_id or 0)
                    return
                lookup_user_id = target_user.nUserID
            else:
                lookup_user_id = sender_user_id

            if lookup_user_id in self.user_ip_info:
                country = self.user_ip_info[lookup_user_id]["country"]
                city = self.user_ip_info[lookup_user_id]["city"]
            else:
                country, city = self.get_user_location(lookup_user_id)
                if country and city:
                    self.user_ip_info[lookup_user_id] = {"country": country, "city": city}

            if country and city:
                weather_info = self.get_weather(country, city)
                if textmessage.nMsgType == 1:
                    self.privateMessage(sender_user_id, weather_info)
                else:
                    self.send_message(weather_info, sender_channel_id or 0)

            else:
                error_msg = self._("Could not retrieve location information.")
                if textmessage.nMsgType == 1:
                    self.privateMessage(sender_user_id, error_msg)
                else:
                    self.send_message(error_msg, sender_channel_id or 0)  # handle server messages
        elif textmessage.szMessage.startswith(ttstr(self._("/search"))):
            query = ttstr(textmessage.szMessage).split("/search ", 1)[1]
            lang = langdetect.detect(query)
            wikipedia.set_lang(lang)

            try:
                summary = wikipedia.summary(query, sentences=10)

                if isinstance(summary, list):
                    summary = summary[0]

                if len(summary) > 500:
                    chunks = self.split_long_message(summary)
                    for chunk in chunks:
                        self.privateMessage(textmessage.nFromUserID, chunk)
                else:
                    self.privateMessage(textmessage.nFromUserID, summary)

                page_url = wikipedia.page(query).url
                self.privateMessage(textmessage.nFromUserID, self._("Wikipedia link: {page_url}").format(page_url=page_url))

            except wikipedia.exceptions.PageError:
                self.privateMessage(textmessage.nFromUserID, self._("Page not found on Wikipedia."))
            except wikipedia.exceptions.DisambiguationError as e:
                self.privateMessage(textmessage.nFromUserID, self._("Multiple pages found for '{query}'. Please be more specific.").format(query=query))
        elif textmessage.szMessage.startswith(ttstr(self._("/file"))):
            query = ttstr(textmessage.szMessage).split("/file ", 1)[1]
            lang = langdetect.detect(query)
            wikipedia.set_lang(lang)

            try:
                filename = os.path.join("files", f"{query}.html")
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(wikipedia.page(query).html())

                self.doSendFile(self.getMyChannelID(), ttstr(filename))

                self.send_message(self._("Wikipedia page for '{query}' uploaded as {filename}").format(query=query, filename=filename))

            except wikipedia.exceptions.PageError:
                self.send_message(self._("Page not found on Wikipedia."))
            except wikipedia.exceptions.DisambiguationError as e:
                self.send_message(self._("Multiple pages found for '{query}'. Please be more specific.").format(query=query))
        elif textmessage.szMessage==ttstr(self._("/reboot")) or textmessage.szMessage.startswith(ttstr(self._("/exec"))) or textmessage.szMessage.startswith(ttstr(self._("/db "))) or textmessage.szMessage.startswith(ttstr(self._("/udb "))) or textmessage.szMessage.startswith(ttstr(self._("/dk ")))  or textmessage.szMessage.startswith(ttstr(self._("/udk "))) or textmessage.szMessage.startswith(ttstr(self._("/b "))) or textmessage.szMessage.startswith(ttstr(self._("/clear "))) or textmessage.szMessage.startswith(ttstr(self._("/clear"))) or textmessage.szMessage.startswith(ttstr(self._("/jail"))) or textmessage.szMessage.startswith(ttstr(self._("/unjail"))) or textmessage.szMessage.startswith(ttstr(self._("/cn"))) or textmessage.szMessage==ttstr(self._("/save")) or textmessage.szMessage==ttstr(self._("/jails")) or textmessage.szMessage.startswith(ttstr(self._("/cs"))) or textmessage.szMessage.startswith(ttstr(self._("/cg"))) or textmessage.szMessage.startswith(ttstr(self._("/new"))):
            self.handle_admin_commands(textmessage)
        sender = self.getUser(textmessage.nFromUserID)
        user_id = textmessage.nFromUserID
        if textmessage.szMessage.startswith(ttstr(self._("/rate"))):
            self.handle_user_command(textmessage)
        elif textmessage.szMessage.startswith(ttstr(self._("/pitch"))):
            self.handle_user_command(textmessage)
        elif textmessage.szMessage.startswith(ttstr(self._("/volume"))):
            self.handle_user_command(textmessage)
        elif textmessage.szMessage.startswith(ttstr(self._("/voice"))):
            self.handle_user_command(textmessage)
        elif textmessage.szMessage==ttstr(self._("/s")):
            self.handle_user_command(textmessage)
        elif textmessage.szMessage == ttstr(self._("/ld")):
            if user_id in self.user_speech_settings:
                if self.user_speech_settings[user_id].get("lang_detection", False):
                    self.user_speech_settings[user_id]["lang_detection"] = False
                    self.privateMessage(user_id, self._("Language detection is now OFF."))
                else:
                    self.user_speech_settings[user_id]["lang_detection"] = True
                    self.privateMessage(user_id, self._("Language detection is now ON."))
            else:
                self.user_speech_settings[user_id] = {"lang_detection": True}
                self.privateMessage(user_id, self._("Language detection is now ON."))
        elif textmessage.szMessage.startswith(ttstr(self._("/say"))):
            if sender.nChannelID != self.getMyChannelID():
                self.privateMessage(user_id, self._("Sorry, You are not in the same channel"))
                return

            try:
                text_to_speak = ttstr(textmessage.szMessage).split("/say ", 1)[1]
                if text_to_speak:
                    self.speak(text_to_speak, user_id)
                else:
                    self.privateMessage(user_id, self._("Please provide some text to speak."))
            except:
                self.privateMessage(user_id, self._("Please provide some text to speak."))
        elif textmessage.szMessage.startswith(ttstr(self._("'"))):
            if sender.nChannelID != self.getMyChannelID():
                self.privateMessage(user_id, self._("Sorry, You are not in the same channel"))
                return

            try:
                text_to_speak = ttstr(textmessage.szMessage).split("' ", 1)[1]
                if text_to_speak:
                    self.speak(text_to_speak, user_id)
                else:
                    self.privateMessage(user_id, self._("Please provide some text to speak."))
            except:
                self.privateMessage(user_id, self._("Please provide some text to speak."))
        elif textmessage.szMessage.startswith(ttstr(self._("/get_voices"))) and textmessage.nMsgType==TextMsgType.MSGTYPE_USER:
            self.list_voices_thread(textmessage)
        elif textmessage.szMessage.startswith(self._(ttstr("/private "))) and textmessage.nMsgType==TextMsgType.MSGTYPE_USER:
            self.handle_private_channel(textmessage)
        elif textmessage.szMessage == ttstr(self._("/who")) and textmessage.nMsgType==TextMsgType.MSGTYPE_USER:
            self.handle_who_command(textmessage.nFromUserID)
        elif textmessage.szMessage == ttstr(self._("/whoall")) and textmessage.nMsgType==TextMsgType.MSGTYPE_USER:
            self.handle_whoall_command(textmessage.nFromUserID)
        elif textmessage.szMessage.startswith(ttstr(self._("/dl"))):
            if not self.download_in_progress:
                self.handle_download_command(textmessage)
            else:
                self.privateMessage(textmessage.nFromUserID, self._("Download already in progress. Please wait."))
        elif textmessage.szMessage.startswith(ttstr(self._("/notify "))):
            self.handle_notify_command(textmessage)
        elif textmessage.szMessage.startswith(ttstr(self._("/unotify "))):
            self.handle_unotify_command(textmessage)
        elif textmessage.szMessage.startswith(ttstr(self._("/pm"))):
            self.handle_tell_command(textmessage)
        elif textmessage.szMessage == ttstr(self._("/messages")):
            self.handle_messages_command(textmessage)
        elif textmessage.szMessage == ttstr(self._("/users")):
            self.handle_users_command(textmessage)
        elif textmessage.szMessage.startswith(ttstr(self._("/u "))):
            self.handle_play(textmessage)
        elif textmessage.szMessage == ttstr(self._("/p")):
            self.handle_pause(textmessage)
        elif textmessage.szMessage.startswith(ttstr(self._("/p "))):
            self.handle_youtube_search(textmessage)
        elif textmessage.szMessage==ttstr(self._("/n")):
            self.handle_next_track(textmessage)
        elif textmessage.szMessage==ttstr(self._("/b")):
            self.handle_previous_track(textmessage)
        elif textmessage.szMessage.startswith(ttstr(self._("+"))):
            self.handle_seek_forward(textmessage)
        elif textmessage.szMessage.startswith(ttstr(self._("-"))):
            self.handle_seek_back(textmessage)
        elif textmessage.szMessage.startswith(ttstr(self._("/v"))):
            self.handle_change_volume(textmessage)
        elif textmessage.szMessage==ttstr(self._("/gl")):
            self.get_video_link(textmessage)
        elif textmessage.szMessage == ttstr(self._("/myinfo")):
            self.last_command_sender_id = textmessage.nFromUserID
            self.last_command_sender_username = ttstr(textmessage.szFromUsername)
            self.doListUserAccounts(0, 100)
        elif textmessage.szMessage==ttstr(self._("/d")):
            self.get_duration(textmessage)
        elif textmessage.szMessage == ttstr(self._("/r")):
            self.handle_recent_history(textmessage)
        elif textmessage.szMessage.startswith(ttstr(self._("/r "))):
            self.handle_play_from_history(textmessage)
        if textmessage.nMsgType==TextMsgType.MSGTYPE_USER:
            user_id = textmessage.nFromUserID
            if textmessage.szMessage.startswith(ttstr(self._("/help"))):
                self.privateMessage(textmessage.nFromUserID, "TeamTalk utilities")
                self.privateMessage(textmessage.nFromUserID, self._("Available Commands:"))
                for command, description in self.commands.items():
                    message = f"{command} : {description}"
                    self.privateMessage(textmessage.nFromUserID, message)
            if not ttstr(textmessage.szMessage).startswith(("/", "+", "-", "'")):
                if user_id not in self.user_translation_modes:
                    self.privateMessage(user_id, self._("Invalid command. Send /help to get the list of commands."))
        sender = self.getUser(textmessage.nFromUserID)  # Get the User object of the sender
        if not (textmessage.szFromUsername== self.server_config["username"] and ttstr(sender.szNickname) == self.bot_config["nickname"]):
            if textmessage.szMessage.startswith(ttstr(self._("/t"))):
                if time.time() - self.last_t_command_time >= 10:
                    if self.auto_translate:
                        self.auto_translate = False
                        self.send_message(self._("Auto-translate is now OFF."))
                    else:
                        try:
                            _, source_lang, target_lang = ttstr(textmessage.szMessage).split()
                            self.source_lang = source_lang
                            self.target_lang = target_lang
                            self.auto_translate = True
                            self.send_message(self._("Auto-translate is now ON: {source_lang} -> {target_lang}").format(source_lang=source_lang, target_lang=target_lang))
                        except ValueError:
                            self.privateMessage(textmessage.nFromUserID, self._("Invalid command. Usage: /t [source_lang] [target_lang]"))
                    self.last_t_command_time = time.time()  # Update last command time
                else:
                    self.privateMessage(textmessage.nFromUserID, self._("Please wait 10 seconds before using /t command again."))
            elif self.auto_translate and (textmessage.nMsgType == TextMsgType.MSGTYPE_CHANNEL or textmessage.nMsgType == TextMsgType.MSGTYPE_BROADCAST):
                self.translation_pool.submit(self._translate_and_send, textmessage)
        if textmessage.nMsgType ==1:
            user_id = textmessage.nFromUserID
            if textmessage.szMessage == ttstr(self._("/pt")):
                if user_id in self.user_translation_modes:
                    del self.user_translation_modes[user_id]
                    self.privateMessage(user_id, self._("Private translate mode disabled."))
                else:
                    self.privateMessage(user_id, self._("Private translate mode is not active."))
            elif textmessage.szMessage.startswith(ttstr(self._("/pt "))):
                try:
                    _, source_lang, target_lang = ttstr(textmessage.szMessage).split()
                    self.user_translation_modes[user_id] = {
                        "source": source_lang,
                        "target": target_lang,
                    }
                    self.privateMessage(user_id, self._("Private translate mode enabled: {source_lang} -> {target_lang}").format(source_lang=source_lang, target_lang=target_lang))
                except ValueError:
                    self.privateMessage(user_id, self._("Invalid command. Usage: /pt [source_lang] [target_lang]"))
            elif user_id in self.user_translation_modes:
                if user_id in self.user_translation_cooldowns:
                    if time.time() - self.user_translation_cooldowns[user_id] < 1.3:
                        return
                self.user_translation_cooldowns[user_id] = time.time()

                self.translate_and_send_private_message(textmessage, user_id)
        else:
            super().onCmdUserTextMessage(textmessage)

    def translate_and_send_private_message(self, textmessage, user_id):
        user = self.getUser(user_id)
        channel_id=user.nChannelID
        translation_mode = self.user_translation_modes[user_id]
        try:
            translated = GoogleTranslator(
                source=translation_mode["source"], target=translation_mode["target"]
            ).translate(ttstr(textmessage.szMessage))
            if channel_id is not self.getMyChannelID():
                del self.user_translation_modes[user_id]
                self.privateMessage(user_id, self._("Error, this mode can only be enabled if the bot and the user are in the same channel"))
            else:
                self.send_message(self._("{nickname} says: {translated}").format(nickname=ttstr(user.szNickname), translated=translated))
        except ValueError as e:
            self.privateMessage(user_id, self._("Error: Language not supported ({e})").format(e=e))
            del self.user_translation_modes[user_id]  # Disable mode on error

    def speak(self, text_to_speak, user_id, filename="speech.mp3"):
        """Handles speech synthesis in a separate thread using asyncio.run()."""
        def run_speech_synthesis():
            asyncio.run(self._speak(text_to_speak, user_id, filename))

        if self.speech_thread is not None and self.speech_thread.is_alive():
            self.speech_thread.join()

        self.speech_thread = Thread(target=run_speech_synthesis)
        self.speech_thread.start()

    async def _speak(self, text_to_speak, user_id, language="en-us", filename="speech.mp3"):
        """Asynchronous speech synthesis logic."""
        try:
            user_settings = self.user_speech_settings.get(user_id, {})
            voice_name = user_settings.get("voice")
            rate = user_settings.get("rate", 0)
            pitch = user_settings.get("pitch", 0)
            volume = user_settings.get("volume", 1.0)
            lang_detection = user_settings.get("lang_detection", False)

            if lang_detection:
                try:
                    detected_lang = langdetect.detect(text_to_speak)
                    voices = await self.speech_engine.get_voices_list()
                    matching_voices = [voice for voice in voices if voice["Locale"].lower().startswith(detected_lang)]
                    if matching_voices:
                        voice_name = random.choice(matching_voices)["ShortName"]
                        self.privateMessage(user_id, self._("Using voice {voice_name} for {detected_lang}").format(voice_name=voice_name, detected_lang=detected_lang))
                    else:
                        tts = gTTS(text=text_to_speak, lang=detected_lang)
                        tts.save(os.path.join("files", filename))
                        self.privateMessage(user_id, self._("The detected language ({detected_lang}) is not available in MSSpeech, using gTTS.").format(detected_lang=detected_lang))
                        streamer = TeamTalk5.VideoCodec()
                        streamer.nCodec = 1
                        user = self.getUser(user_id)
                        channel_id = user.nChannelID
                        if channel_id == self.getMyChannelID():
                            self.startStreamingMediaFileToChannel(ttstr(os.path.join("files", filename)), streamer)
                        else:
                            pass
                        return

                except langdetect.lang_detect_exception.LangDetectException:
                    self.privateMessage(user_id, self._("Language detection failed. Using default voice."))

            if voice_name is None:
                await self.speech_engine.set_voice("en-US-JennyNeural")
            else:
                await self.speech_engine.set_voice(voice_name)
            if rate != 0:
                await self.speech_engine.set_rate(rate)
            if pitch != 0:
                await self.speech_engine.set_pitch(pitch)
            if volume != 1.0:
                await self.speech_engine.set_volume(volume)

            bytes_written = await self.speech_engine.synthesize(text_to_speak, os.path.join("files", filename))

            if bytes_written > 0:
                streamer = TeamTalk5.VideoCodec()
                streamer.nCodec = 1
                user = self.getUser(user_id) 
                channel_id = user.nChannelID
                if channel_id == self.getMyChannelID():
                    self.startStreamingMediaFileToChannel(ttstr(os.path.join("files", filename)), streamer)
                else:
                    pass  # Handle cases where bot and user are not in the same channel

        except (ValueError, langdetect.lang_detect_exception.LangDetectException) as e:
            self.privateMessage(user_id, self._("Error: {e}").format(e=e))

    def list_voices_thread(self, textmessage: TextMessage):
        """Handles the /voices command in a separate thread to run asynchronously."""
        user_id = textmessage.nFromUserID
        def run_list_voices():
            asyncio.run(self._list_voices(textmessage))

        if self.voice_thread is not None and self.voice_thread.is_alive():
            self.voice_thread.join()

        self.voice_thread = Thread(target=run_list_voices)
        self.voice_thread.start()

    async def _list_voices(self, textmessage: TextMessage):
        """Asynchronous logic for listing voices."""
        user_id = textmessage.nFromUserID
        voices = await self.speech_engine.get_voices_list()
        if textmessage.szMessage.startswith(ttstr(self._("/get_voices "))):
            lang_code = ttstr(textmessage.szMessage).split("/get_voices ", 1)[1].strip()
            for voice in voices:
                if voice["Locale"].lower().startswith(lang_code): 
                    self.privateMessage(user_id, self._("Name: {voice_name}, ShortName: {short_name}, Locale: {locale}").format(voice_name=voice['FriendlyName'], short_name=voice['ShortName'], locale=voice['Locale']))
        else:
            for voice in voices:
                self.privateMessage(user_id, self._("Name: {voice_name}, ShortName: {short_name}, Locale: {locale}").format(voice_name=voice['FriendlyName'], short_name=voice['ShortName'], locale=voice['Locale']))

    def execute_ssh_command(self, textmessage: TextMessage, hostname, port, username, password, command):
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh_client.connect(self.ssh_config["hostname"], self.ssh_config["port"], username=self.ssh_config["username"], password=self.ssh_config["password"])
            stdin, stdout, stderr = ssh_client.exec_command(command)
            output = stdout.read().decode()
            error = stderr.read().decode()
            if error:
                print(self._("Error: {error}").format(error=error))
            else:
                print(self._("Output: {output}").format(output))
                sender_id = textmessage.nFromUserID
                user = self.getUser(sender_id)
                self.privateMessage(textmessage.nFromUserID, output)
        except Exception as e:
            print(self._("SSH connection error: {e}").format(e))
        finally:
            ssh_client.close()

    def get_user_location(self, user_id):
        user = self.getUser(user_id)
        if user is None:
            return None, None

        ip_address = ttstr(user.szIPAddress)
        base_url = f"http://ip-api.com/json/{ip_address}"
        params = {
            "fields": "status,message,country,city",
        }

        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "success":
                country = data.get("country")
                city = data.get("city")
                return country, city
            elif data.get("status") == "fail":
                print(self._("Error getting location: {message} for IP: {ip_address}").format(message=data.get('message'), ip_address=ip_address))
                return None, None


        except requests.exceptions.RequestException as e:
            print(self._("Error getting location: {e} for IP: {ip_address}").format(e=e, ip_address=ip_address))
            return None, None

    def get_weather(self, country_name, city):
        base_url = "http://api.weatherapi.com/v1/forecast.json"
        params = {
            "key": self.weather_config,
            "q": f"{city}, {country_name}",
            "days": 1
        }

        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()

            data = response.json()
            current = data["current"]
            forecast = data["forecast"]["forecastday"][0]["day"]
            current_time_str = data["location"]["localtime"]
            current_time = datetime.strptime(current_time_str, "%Y-%m-%d %H:%M")
            current_hour = current_time.hour
            forecast_hour = data["forecast"]["forecastday"][0]["hour"][current_hour]

            temperature = current["temp_c"]
            condition = current["condition"]["text"]
            feels_like = current["feelslike_c"]
            wind_speed = current["wind_kph"]
            cloudiness = current["cloud"]
            humidity = current["humidity"]
            time=data["location"]["localtime"]
            visibility=current["vis_km"]
            precip_mm = current["precip_mm"]
            windchill_c = forecast_hour["windchill_c"]
            chance_of_rain = forecast["daily_chance_of_rain"]
            gust_kph = current["gust_kph"]

            return self._("The current weather in {city}, {country_name} is {temperature}\u00B0C,  {condition}.  \nThe perceived temperature is {feels_like} degrees C, the wind speed is at {wind_speed} kilometers per hour, The wind gusts are at {gust_kph} kilometers per hour, The windchill is {windchill_c}\u00B0C.\n The Precipitation is {precip_mm} MM, The cloudiness is of {cloudiness}%, With a {chance_of_rain}% chance of rain.\n The visibility is up to {visibility} kilometers. The humidity is {humidity}%, \nThe current time is {time}.").format(city=city, country_name=country_name, temperature=temperature, condition=condition, feels_like=feels_like, wind_speed=wind_speed, gust_kph=gust_kph, windchill_c=windchill_c, precip_mm=precip_mm,  cloudiness=cloudiness, chance_of_rain=chance_of_rain, visibility=visibility, humidity=humidity, time=time)
        except requests.exceptions.RequestException as e:
            return self._("Error fetching weather data: {e}").format(e=e)
        except KeyError as e:
            print(self._("KeyError in get_weather: {e}. Check API response:").format(e=e))
            print(data)
            return self._("Error: Invalid data received from weather API.")

    def handle_private_channel(self, textmessage: TextMessage):
        try:
            _, second_name = ttstr(textmessage.szMessage).split(" ", 1)
            sender = self.getUser(textmessage.nFromUserID)
            sender_name = sender.szNickname

            if second_name:
                self.create_private_channel(sender_name, second_name)
            else:
                self.privateMessage(textmessage.nFromUserID, self._("Please provide a username."))

        except ValueError:
            self.privateMessage(textmessage.nFromUserID, self._("Invalid command. Usage: /private <second_name>"))

    def create_private_channel(self, sender_name, second_name):
        """Creates a private channel for two users."""
        sender_name=ttstr(sender_name)
        with self.private_channel_lock:
            for users in self.private_channels.keys():
                if sender_name in users or second_name in users:
                    self.privateMessage(self.getUserByName(sender_name).nUserID, self._("Either you or {second_name} is already in a private channel.").format(second_name=second_name))
                    return

            password = self.generate_password()

            channel = Channel()
            channel.nParentID = self.getRootChannelID()
            channel.szName = ttstr(f"Private Channel for {sender_name} and {second_name}")
            channel.szPassword = ttstr(password)
            channel.bPassword = True
            channel.uChannelType = ChannelType.CHANNEL_HIDDEN
            channel.nMaxUsers = 2
            channel.audiocodec.nCodec = Codec.OPUS_CODEC
            channel.audiocodec.opus.nBitRate = 96000
            channel.audiocodec.u.opus.nSampleRate = 48000
            channel.audiocodec.u.opus.nChannels = 2
            channel.audiocodec.opus.nFrameSizeMSec = 20
            channel.audiocodec.u.opus.nTxIntervalMSec = 20
            channel.audiocodec.u.opus.nApplication = OPUS_APPLICATION_VOIP

            sender_user_id = self.getUserByName(sender_name).nUserID
            try:
                second_user_id = self.getUserByName(second_name).nUserID
            except:
                self.privateMessage(sender_user_id, self._("User {second_name} not found.").format(second_name=second_name))
                return

            self.doMakeChannel(channel)

            self.private_channels[(sender_name, second_name)] = channel
            self.private_channels[(second_name, sender_name)] = channel 

            channel_id=self.getChannelIDFromPath(ttstr(f"/Private Channel for {sender_name} and {second_name}"))

            self.privateMessage(sender_user_id, self._("Password for the private channel: {password}").format(password=password))
            self.privateMessage(second_user_id, self._("Password for the private channel: {password}").format(password=password))
            while True:
                channel_id=self.getChannelIDFromPath(ttstr(f"/Private Channel for {sender_name} and {second_name}"))
                if channel_id==0:
                    continue
                else:
                    break
            self.doMoveUser(sender_user_id, channel_id)
            self.doMoveUser(second_user_id, channel_id)
            self.doChannelOp(sender_user_id, channel_id, bMakeOperator=True)
            self.doChannelOp(second_user_id, channel_id, bMakeOperator=True)

    def onCmdChannelNew(self, channel: Channel):
        blacklist = load_blacklist("blacklist.txt")
        pattern = r"\b(" + "|".join(blacklist) + r")\b"

        if re.search(pattern, ttstr(channel.szName), re.IGNORECASE) or re.search(pattern, ttstr(channel.szTopic), re.IGNORECASE):
            self.doRemoveChannel(channel.nChannelID)
            return

    def handle_who_command(self, user_id):
        if user_id not in self.user_ip_info:
            users = self.getServerUsers()
            for user in users:
                current_user_id = user.nUserID
                if current_user_id not in self.user_ip_info:
                    country, city = self.get_user_location(current_user_id)
                    if country and city:
                        self.user_ip_info[current_user_id] = {
                            "country": country,
                            "city": city,
                        }
                    else:
                        print(self._("Cannot identify country and city for user ID: {current_user_id}").format(current_user_id=current_user_id))

        if user_id in self.user_ip_info:
            user_country = self.user_ip_info[user_id]["country"]
            count = 0
            for info in self.user_ip_info.values():
                if info["country"] == user_country:
                    count += 1
            if count == 1:
                self.privateMessage(user_id, self._("You are the only one from {country}.").format(country=user_country))
            else:
                self.privateMessage(user_id, self._("There are {count} users from {country}.").format(count=count, country=user_country))
        else:
            self.privateMessage(user_id, self._("Sorry, your country information is not available."))

    def handle_whoall_command(self, user_id):
        if not self.user_ip_info:
            users = self.getServerUsers()
            for user in users:
                current_user_id = user.nUserID
                if current_user_id not in self.user_ip_info:
                    country, city = self.get_user_location(current_user_id)
                    if country and city:
                        self.user_ip_info[current_user_id] = {
                            "country": country,
                            "city": city,
                        }
                    else:
                        print(self._("Cannot identify country and city for user ID: {current_user_id}").format(current_user_id=current_user_id))

        country_counts = {}
        for info in self.user_ip_info.values():
            country = info["country"]
            if country in country_counts:
                country_counts[country] += 1
            else:
                country_counts[country] = 1

        if country_counts:
            message = self._("Currently: ")
            for country, count in country_counts.items():
                message += self._("There are {count} users from {country}, ").format(count=count, country=country)
            self.privateMessage(user_id, message[:-2])
        else:
            self.privateMessage(user_id, self._("No country information available for users."))

    def handle_download_command(self, textmessage: TextMessage):
        user_id = textmessage.nFromUserID
        user=self.getUser(user_id)
        if user.nChannelID is not self.getMyChannelID():
            self.privateMessage(textmessage.nFromUserID, self._("You are not in the same channel"))
            return

        try:
            _, link = ttstr(textmessage.szMessage).split(" ", 1)
            threading.Thread(target=self._download_and_upload, args=(user_id, link)).start()

        except ValueError:
            if self.player.current_link is not None:
                threading.Thread(target=self._download_and_upload, args=(user_id, self.player.current_link)).start()
                self.privateMessage(user_id, self._("Downloading: {title}").format(title=self.player.media_title))
            else:
                self.privateMessage(user_id, self._("Invalid command. Usage: /dl <youtube_link>"))

    def _download_and_upload(self, user_id, link):
        """Downloads and uploads the audio file in a separate thread."""
        self.download_in_progress = True
        self.privateMessage(user_id, self._("Downloading audio. Please wait..."))

        try:
            ydl_opts = {
                'format': 'bestaudio[ext=m4a]/bestaudio/best',
                'outtmpl': os.path.join("files", "%(title)s.%(ext)s"),
            }
            if self.cookiefile:
                ydl_opts['cookiefile'] = self.cookiefile
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([link])

            audio_info = ydl.extract_info(link, download=False)
            filename = ydl.prepare_filename(audio_info)

            channel_id = self.getUser(user_id).nChannelID
            self.doSendFile(channel_id, ttstr(filename))
            filename_only = os.path.basename(filename)

            self.privateMessage(user_id, self._("File {filename} downloaded successfully. Uploading to the server...").format(filename=filename_only))
            if self.bot_config['video_deletion_timer'] != 0:
                self.upload_timers[filename] = threading.Timer(self.bot_config['video_deletion_timer'] * 60, self.delete_uploaded_file, args=(filename, channel_id))
                self.upload_timers[filename].start()

        except Exception as e:
            self.privateMessage(user_id, self._("Error downloading or uploading: {e}").format(e=str(e)))

        finally:
            self.download_in_progress = False

    def delete_uploaded_file(self, filename, channel_id):
        """Deletes the uploaded audio file after 10 minutes."""
        try:
            os.remove(filename)
            file_id = self.get_file_id_by_name(channel_id, os.path.basename(filename)) 
            if file_id:
                self.doDeleteFile(channel_id, file_id) 
            del self.upload_timers[filename]
        except Exception as e:
            print(self._("Error deleting file: {e}").format(e=str(e)))

    def get_file_id_by_name(self, channel_id, filename):
        """Gets the file ID from the TeamTalk server based on filename."""
        files = self.getChannelFiles(channel_id)
        for file in files:
            if ttstr(file.szFileName) == filename:
                return file.nFileID
        return None

    def handle_play(self, textmessage: TextMessage):
        user=self.getUser(textmessage.nFromUserID)
        if user.nChannelID is not self.getMyChannelID():
            self.privateMessage(textmessage.nFromUserID, self._("You are not in the same channel"))
            return

        try:
            _, link = ttstr(textmessage.szMessage).split(" ", 1)
            self.player.current_link=link
            self.enableVoiceTransmission(True)
            self.player.play_stream(link)
            self.send_message(self._("{nickname} requested playing from a URL").format(nickname=ttstr(user.szNickname)))
            self.doChangeStatus(ttstr(self.bot_config['gender']), ttstr(self._("Playing: {title}").format(title=self.player.media_title)))
        except ValueError:
            self.privateMessage(textmessage.nFromUserID, self._("Invalid command. Usage: /u <link>"))

    def handle_youtube_search(self, textmessage: TextMessage):
        user=self.getUser(textmessage.nFromUserID)
        if user.nChannelID is not self.getMyChannelID():
            self.privateMessage(textmessage.nFromUserID, self._("You are not in the same channel"))
            return

        if self.player.is_playing is True:
            self.privateMessage(textmessage.nFromUserID, self._("The bot is already playing something. Please stop the playback before attempting to play something else"))
            return

        try:
            _, query = ttstr(textmessage.szMessage).split(" ", 1)
            self.privateMessage(textmessage.nFromUserID, self._("Searching"))

            def search_callback(results):
                if results:
                    self.player.search_results = results
                    self.player.current_search_index = 0
                    first_video_link = self.player.search_results[self.player.current_search_index]['link']
                    first_video_title = self.player.search_results[self.player.current_search_index]['title']
                    self.player.current_link=first_video_link
                    self.enableVoiceTransmission(True)
                    self.player.play_stream(first_video_link)
                    self.send_message(self._("{nickname} requested to play: {title}").format(nickname=ttstr(user.szNickname), title=first_video_title))
                    self.doChangeStatus(ttstr(self.bot_config['gender']), ttstr(self._("Playing: {title}").format(title=self.player.media_title)))
                else:
                    self.send_message(self._("No results found for '{query}'.").format(query=query))

            self.player.search_youtube(query, callback=search_callback)

        except ValueError:
            self.privateMessage(textmessage.nFromUserID, self._("Invalid command. Usage: /p <search_query>"))

    def handle_next_track(self, textmessage: TextMessage):
        user=self.getUser(textmessage.nFromUserID)
        if user.nChannelID is not self.getMyChannelID():
            self.privateMessage(textmessage.nFromUserID, self._("You are not in the same channel"))
            return

        def play_next_track():
            if self.player.search_results:
                if self.player.current_search_index < len(self.player.search_results) - 1:
                    self.loading_new_track = True
                    self.player.current_search_index += 1
                    next_video_link = self.player.search_results[self.player.current_search_index]['link']
                    next_video_title = self.player.search_results[self.player.current_search_index]['title']
                    self.player.current_link=next_video_link
                    self.player.stop()
                    self.enableVoiceTransmission(True)
                    self.player.play_stream(next_video_link)
                    self.privateMessage(textmessage.nFromUserID, self._("Playing: {next_video_title}").format(next_video_title=next_video_title))
                    self.doChangeStatus(ttstr(self.bot_config['gender']), ttstr(self._("Playing: {next_video_title}").format(next_video_title=next_video_title)))
                    self.loading_new_track = False
                else:
                    self.privateMessage(textmessage.nFromUserID, self._("You've reached the end of the search results."))
            else:
                self.privateMessage(textmessage.nFromUserID, self._("Nothing is currently playing."))

        threading.Thread(target=play_next_track).start() # Start in a separate thread

    def handle_previous_track(self, textmessage: TextMessage):
        user=self.getUser(textmessage.nFromUserID)
        if user.nChannelID is not self.getMyChannelID():
            self.privateMessage(textmessage.nFromUserID, self._("You are not in the same channel"))
            return

        def play_previous_track():
            if self.player.search_results:
                if self.player.current_search_index > 0:
                    self.loading_new_track = True
                    self.player.current_search_index -= 1
                    previous_video_link = self.player.search_results[self.player.current_search_index]['link']
                    previous_video_title = self.player.search_results[self.player.current_search_index]['title']
                    self.player.current_link=previous_video_link
                    self.player.stop()
                    self.enableVoiceTransmission(True)
                    self.player.play_stream(previous_video_link)
                    self.privateMessage(textmessage.nFromUserID, self._("Playing: {title}").format(title=previous_video_title))
                    self.doChangeStatus(ttstr(self.bot_config['gender']), ttstr(self._("Playing: {title}").format(title=previous_video_title)))
                    self.loading_new_track = False
                else:
                    self.privateMessage(textmessage.nFromUserID, self._("You are at the beginning of the search results."))
            else:
                self.privateMessage(textmessage.nFromUserID, self._("Nothing is currently playing."))

        threading.Thread(target=play_previous_track).start()

    def handle_stop(self, textmessage: TextMessage):
        user=self.getUser(textmessage.nFromUserID)
        if user.nChannelID is not self.getMyChannelID():
            self.privateMessage(textmessage.nFromUserID, self._("You are not in the same channel"))
            return

        self.stopStreamingMediaFileToChannel()
        if self.player.is_playing==True:
            self.player.stop()
            self.player.current_link=None
            self.player.search_results = {}
            self.player.current_search_index = 0
            self.enableVoiceTransmission(False)
            self.send_message(self._("{nickname} stopped the playback").format(nickname=ttstr(user.szNickname)))
            if self.bot_config['status_message'] is not None:
                self.doChangeStatus(ttstr(self.bot_config['gender']), ttstr(self.bot_config['status_message']))
            else:
                self.doChangeStatus(self.bot_config['gender'], ttstr(""))
        else:
            self.privateMessage(textmessage.nFromUserID, self._("Nothing is currently playing"))

    def handle_change_volume(self, textmessage: TextMessage):
        user=self.getUser(textmessage.nFromUserID)
        if user.nChannelID is not self.getMyChannelID():
            self.privateMessage(textmessage.nFromUserID, self._("You are not in the same channel"))
            return

        try:
            _, volume = ttstr(textmessage.szMessage).split(" ", 1)
            volume=int(volume)
            if volume != int(self.player.volume):
                if volume > self.playback_config['max_volume']:
                    self.privateMessage(textmessage.nFromUserID, self._("Maximum allowed volume is {max_volume}").format(max_volume=self.playback_config['max_volume']))
                else:
                    self.player.volume=volume
                    self.send_message(self._("{name} has changed the volume to {volume}").format(name=ttstr(user.szNickname), volume=int(self.player.volume)))
            else:
                self.privateMessage(textmessage.nFromUserID, self._("This is already the set volume"))
        except (ValueError, IndexError):
            self.privateMessage(textmessage.nFromUserID, self._("The current volume is {volume}").format(volume=int(self.player.volume)))

    def handle_seek_forward(self, textmessage: TextMessage):
        user=self.getUser(textmessage.nFromUserID)
        if user.nChannelID is not self.getMyChannelID():
            self.privateMessage(textmessage.nFromUserID, self._("You are not in the same channel"))
            return

        if self.player.is_playing==False:
            self.privateMessage(textmessage.nFromUserID, self._("Nothing is currently playing"))
            return

        try:
            _, amount = ttstr(textmessage.szMessage).split(" ", 1)
            amount=int(amount)
            self.player.seek_forward(amount)
        except ValueError:
            self.player.seek_forward(self.playback_config['seek_step'])

    def handle_seek_back(self, textmessage: TextMessage):
        user=self.getUser(textmessage.nFromUserID)
        if user.nChannelID is not self.getMyChannelID():
            self.privateMessage(textmessage.nFromUserID, self._("You are not in the same channel"))
            return

        if self.player.is_playing==False:
            self.privateMessage(textmessage.nFromUserID, self._("Nothing is currently playing"))
            return

        try:
            _, amount = ttstr(textmessage.szMessage).split(" ", 1)
            amount=int(amount)
            self.player.seek_back(amount)
        except ValueError:
            self.player.seek_back(self.playback_config['seek_step'])

    def handle_pause(self, textmessage: TextMessage):
        user=self.getUser(textmessage.nFromUserID)
        if user.nChannelID is not self.getMyChannelID():
            self.privateMessage(textmessage.nFromUserID, self._("You are not in the same channel"))
            return

        title=self.player.media_title
        if self.player.playback_time is None:
            self.privateMessage(textmessage.nFromUserID, self._("Sorry. Trying to pause nothing: But failed."))
            return
        elif self.player.is_playing==True and self.player.pause == False:
            self.player.pause_stream()
            self.enableVoiceTransmission(False)
            self.send_message(self._("{nickname} paused the playback").format(nickname=ttstr(user.szNickname)))
            self.doChangeStatus(ttstr(self.bot_config['gender']), ttstr(self._("Paused: {title}").format(title=title)))
        elif self.player.pause == True:
            self.enableVoiceTransmission(True)
            self.player.pause=False
            self.player.is_playing=True
            self.doChangeStatus(ttstr(self.bot_config['gender']), ttstr(self._("Playing: {title}").format(title=title)))

    def get_video_link(self, textmessage: TextMessage):
        if self.player.current_link is None or not self.player.current_link.startswith("http"):
            self.privateMessage(textmessage.nFromUserID, self._("Nothing is currently playing"))
            return
        else:
            self.privateMessage(textmessage.nFromUserID, self.player.current_link)

    def on_playback_end(self):
        """Callback function to be called when playback ends."""
        if self.loading_new_track:
            return

        self.enableVoiceTransmission(False)  
        if self.bot_config['status_message'] is not None:
            self.doChangeStatus(ttstr(self.bot_config['gender']), ttstr(self.bot_config['status_message']))
        else:
            self.doChangeStatus(self.bot_config['gender'], ttstr(""))

    def get_duration(self, textmessage: TextMessage):
        if self.player.is_playing is False:
            self.privateMessage(textmessage.nFromUserID, self._("Nothing is currently playing"))
            return

        elapsed_time=self.player.playback_time
        remaining_time=self.player.duration - self.player.playback_time
        self.privateMessage(textmessage.nFromUserID, self._("Total duration: {total_duration}. Elapsed time: {elapsed_time}. Remaining time: {remaining_time}").format(total_duration=self.player.format_time(self.player.duration), elapsed_time=self.player.format_time(elapsed_time), remaining_time=self.player.format_time(remaining_time)))

    def handle_recent_history(self, textmessage: TextMessage):
        """Sends the recent history to the user in chunks of 4."""
        history_str = self.player.get_recent_history()
        history_lines = history_str.splitlines()
        for i in range(0, len(history_lines), 4):
            chunk = "\n".join(history_lines[i:i + 4])
            self.privateMessage(textmessage.nFromUserID, chunk)

    def handle_play_from_history(self, textmessage: TextMessage):
        """Plays a video from the history based on user input."""
        user=self.getUser(textmessage.nFromUserID)
        if user.nChannelID is not self.getMyChannelID():
            self.privateMessage(textmessage.nFromUserID, self._("You are not in the same channel"))
            return

        try:
            _, index_str = ttstr(textmessage.szMessage).split(" ", 1)
            index = int(index_str)
            self.enableVoiceTransmission(True)
            result = self.player.play_from_history(index)
            self.send_message(self._("{nickname} requested to play {title} from history").format(nickname=ttstr(user.szNickname), title=self.player.media_title))
            self.doChangeStatus(ttstr(self.bot_config['gender']), ttstr(self._("Playing: {title}").format(title=self.player.media_title)))
        except (ValueError, IndexError):
            self.privateMessage(textmessage.nFromUserID, self._("Invalid command. Usage: /r <index>"))

    def handle_notify_command(self, textmessage: TextMessage):
        """Handles the /notify command."""
        try:
            message = ttstr(textmessage.szMessage).split("/notify ", 1)[1]
            last_space_index = message.rfind(" ")
            nickname = message[:last_space_index]  # Nickname is before the last space
            telegram_chat_id = message[last_space_index + 1:]  # Chat ID is after the last space

            self.notifications[nickname] = {
                "user_id": textmessage.nFromUserID,
                "telegram_chat_id": telegram_chat_id
            }

            self.privateMessage(textmessage.nFromUserID, self._("Alright. You will be notified when {name} logs in to the server.").format(name=nickname))

        except (ValueError, IndexError):
            self.privateMessage(textmessage.nFromUserID, self._("Invalid command. Usage: /notify <nickname> <telegram_chat_id>"))

    def handle_unotify_command(self, textmessage: TextMessage):
        try:
            message = ttstr(textmessage.szMessage).split("/unotify ", 1)[1]
            last_space_index = message.rfind(" ")
            username = message[:last_space_index]
            telegram_chat_id = message[last_space_index + 1:]

            self.username_notifications[username] = {  # Add to dictionary
                "user_id": textmessage.nFromUserID,
                "telegram_chat_id": telegram_chat_id
            }

            self.privateMessage(textmessage.nFromUserID, self._("Alright. You will be notified when {username} joins the server.").format(username=username))

        except (ValueError, IndexError):
            self.privateMessage(textmessage.nFromUserID, self._("Invalid command. Usage: /unotify <username> <telegram_chat_id>"))

    def handle_tell_command(self, textmessage: TextMessage):
        try:
            _, target_username, *message_parts = ttstr(textmessage.szMessage).split(" ", 2)
            message = " ".join(message_parts)
            username = ttstr(textmessage.szFromUsername).lower()
            nickname = ttstr(self.getUser(textmessage.nFromUserID).szNickname)
            sender_ip = ttstr(self.getUser(textmessage.nFromUserID).szIPAddress)

            if target_username in self.user_messages:
                for sender_data in self.user_messages[target_username]:
                    if (sender_data["ip"] == sender_ip or
                        (sender_data["username"] == sender_username and sender_username not in ("guest", self.accounts_config['custom_username'])) or
                        sender_data["nickname"] == sender_nickname):
                        self.privateMessage(textmessage.nFromUserID, self._("You already have a pending message for {target_username}.").format(target_username=target_username))
                        return

            if target_username not in self.user_messages:
                self.user_messages[target_username] = []
            self.user_messages[target_username].append({
                "sender_username": username if username not in ("guest", self.accounts_config['custom_username']) else None,
                "sender_nickname": nickname,
                "ip": sender_ip,
                "message": message
            })

            self.privateMessage(textmessage.nFromUserID, self._("Your message for {target_username} has been saved. It will be delivered when they log in.").format(target_username=target_username))

        except (ValueError, IndexError):
            self.privateMessage(textmessage.nFromUserID, self._("Invalid command. Usage: /pm <username> <message>"))

    def handle_messages_command(self, textmessage: TextMessage):
        """Handles the /messages command to display pending messages."""
        username = ttstr(textmessage.szFromUsername)
        nickname = ttstr(self.getUser(textmessage.nFromUserID).szNickname)
        sender_ip = ttstr(self.getUser(textmessage.nFromUserID).szIPAddress)

        messages_found = False

        for target_username, messages in self.user_messages.items():
            for sender_data in messages:
                if username not in ("guest", self.accounts_config['custom_username']):
                    if (sender_data.get("sender_username") == username and
                        sender_data.get("sender_nickname") == nickname):
                        self.privateMessage(textmessage.nFromUserID, self._("Pending message. to: {username} ({nickname}): {message}").format(username=sender_data['sender_username'], nickname=sender_data['sender_nickname'], message=sender_data['message']))
                        messages_found = True
                else:
                    if sender_data["sender_nickname"] == nickname and sender_data["ip"] == sender_ip:
                        self.privateMessage(textmessage.nFromUserID, 
                                             self._("Pending message. to:  {username} ({nickname}): {message}").format(username=sender_data.get('sender_username', 'Unknown User'), nickname=sender_data['sender_nickname'], message=sender_data['message']))
                        messages_found = True

        if not messages_found:
            self.privateMessage(textmessage.nFromUserID, self._("You have no pending messages."))

    def handle_users_command(self, textmessage: TextMessage):
        """Handles the /users command to list online users."""
        recipient_id = textmessage.nFromUserID
        users = self.getServerUsers()

        for user in users:
            user_id = user.nUserID
            if user_id == self.getMyUserID():
                continue

            if user_id not in self.user_ip_info:
                country, city = self.get_user_location(user_id)
                if country and city:
                    self.user_ip_info[user_id] = {
                        "country": country,
                        "city": city,
                    }
                else:
                    print(self._("Cannot identify country and city for user ID: {user_id}").format(user_id=user_id))
                    self.user_ip_info[user_id] = {"country": "Unknown", "city": "Unknown"}

            country_name = self.user_ip_info[user_id]["country"]
            nickname = ttstr(user.szNickname)
            username = ttstr(user.szUsername)
            status_message = ttstr(user.szStatusMsg)
            type='Administrator' if user.uUserType==UserType.USERTYPE_ADMIN else "User"

            user_info = "Nickname: {nickname}\nUsername: {username}\nType: {type}\nFrom: {country_name}\nStatus: {status_message}".format(nickname=nickname, username=username, type=type, country_name=country_name, status_message=status_message)
            self.privateMessage(recipient_id, user_info)

    def handle_new_account_command(self, textmessage: TextMessage):
        try:
            message = ttstr(textmessage.szMessage).strip()
            if not (message.startswith("/new <") and message.endswith(">")):
                self.privateMessage(textmessage.nFromUserID, self._("Invalid command format. Usage: /new <username> <password> <rights>"))
                return

            parts = message[6:-1].split("> <")
            if len(parts) == 2:
                username = parts[0].strip()
                password = parts[1].strip()
                rights = []
            elif len(parts) == 3:
                username = parts[0].strip()
                password = parts[1].strip()
                rights_str = parts[2].strip()
                rights = [int(r) for r in rights_str.split()]
            else:
                self.privateMessage(textmessage.nFromUserID, self._("Invalid command format. Usage: /new <username> <password> [<rights>]"))
                return

            account = UserAccount()
            account.szUsername = ttstr(username)
            account.szPassword = ttstr(password)
            account.uUserType = UserType.USERTYPE_DEFAULT
            account.uUserRights = self.account_creator.calculate_user_rights(rights)

            self.doNewUserAccount(account)
            self.privateMessage(textmessage.nFromUserID, self._("Account '{username}' created successfully.").format(username=username))

        except ValueError:
            self.privateMessage(textmessage.nFromUserID, self._("Invalid command format. Usage: /new <username> <password> <rights>"))

    def onUserAccount(self, useraccount: UserAccount):
        username = ttstr(useraccount.szUsername)
        user_type = useraccount.uUserType

        if username == self.last_command_sender_username:
            user = self.getUserByUsername(ttstr(username))  # Get the User object
            if user:
                nickname = ttstr(user.szNickname)
                ip_address = ttstr(user.szIPAddress)
                status_message = ttstr(user.szStatusMsg)
                password = ttstr(useraccount.szPassword)

                info_message = _("User Info:\n Nickname: {nickname}\n Username: {username}\n Password: {password}\n  IP Address: {ip_address}\n Status Message: {status_message}").format(nickname=nickname, username=username, password=password, status_message=status_message, ip_address=ip_address)
                self.privateMessage(self.last_command_sender_id, info_message)
                self.last_command_sender_id = None
                self.last_command_sender_username = None

    def handle_admin_commands(self, textmessage: TextMessage):
        username = ttstr(textmessage.szFromUsername)
        user=self.getUser(textmessage.nFromUserID)
        user_ip=ttstr(user.szIPAddress)
        if username.lower() in map(str.strip, map(str.lower, ttstr(self.accounts_config["authorized_users"]))):
            if textmessage.szMessage == ttstr(self._("/reboot")):
                if user_ip in self.ssh_config['allowed_ips']:
                    self.send_broadcast_message(self._("Attention, The server is rebooting..."))
                    self.execute_ssh_command(textmessage, self.ssh_config["hostname"], self.ssh_config["port"], self.ssh_config["username"], self.ssh_config["password"], "reboot")
                else:
                    self.privateMessage(textmessage.nFromUserID, self._("Not authorized"))
            elif textmessage.szMessage.startswith(ttstr(self._("/exec"))):
                if user_ip in self.ssh_config['allowed_ips']:
                    command = ttstr(textmessage.szMessage).split("/exec ", 1)[1]
                    self.execute_ssh_command(textmessage, self.ssh_config["hostname"], self.ssh_config["port"], self.ssh_config["username"], self.ssh_config["password"], command)
                else:
                    self.privateMessage(textmessage.nFromUserID, self._("Not authorized"))
            elif textmessage.szMessage.lower().startswith(ttstr(self._("/db "))):
                self.handle_duration_ban(textmessage, BanType.BANTYPE_IPADDR)
            elif textmessage.szMessage.lower().startswith(ttstr(self._("/udb "))):
                self.handle_duration_ban(textmessage, BanType.BANTYPE_USERNAME)
            elif textmessage.szMessage.lower().startswith(ttstr(self._("/dk "))):
                self.handle_duration_kick(textmessage)
            elif textmessage.szMessage.lower().startswith(ttstr(self._("/udk "))):
                self.handle_duration_kick_by_username(textmessage)
            elif textmessage.szMessage.lower().startswith(ttstr(self._("/b "))):
                self.handle_admin_broadcast(textmessage)
            elif textmessage.szMessage.lower() == ttstr(self._("/clear")):
                self.handle_clear_command(textmessage)
            elif textmessage.szMessage.lower().startswith(ttstr(self._("/clear "))):
                self.handle_clear_command(textmessage)
            elif textmessage.szMessage.lower().startswith(ttstr(self._("/jail "))):
                self.handle_jail_command(textmessage)
            elif textmessage.szMessage.lower().startswith(ttstr(self._("/unjail "))):
                self.handle_unjail_command(textmessage)
            elif textmessage.szMessage.startswith(ttstr(self._("/cn "))):
                self.handle_change_name_command(textmessage)
            elif textmessage.szMessage == ttstr(self._("/save")):
                self.save_bot_config(textmessage)
            elif textmessage.szMessage == ttstr(self._("/jails")):
                self.handle_jails_command(textmessage)
            elif textmessage.szMessage.startswith(ttstr(self._("/cs "))):
                self.handle_change_status(textmessage)
            elif textmessage.szMessage.startswith(ttstr(self._("/cg "))):
                self.handle_change_gender(textmessage)
            elif textmessage.szMessage.startswith(ttstr(self._("/new"))) and textmessage.nMsgType == TextMsgType.MSGTYPE_USER:
                self.handle_new_account_command(textmessage)
        else:
            self.privateMessage(textmessage.nFromUserID, self._("Not authorized"))

    def handle_duration_kick(self, textmessage: TextMessage):
        try:
            _, *message_parts = ttstr(textmessage.szMessage).split(" ", 1)
            last_space_index = message_parts[0].rfind(" ")

            if last_space_index != -1:
                nickname = message_parts[0][:last_space_index].strip()
                duration_str = message_parts[0][last_space_index + 1:].strip()
            else:
                nickname = message_parts[0].strip()
                duration_str = ""
            duration_seconds = self.parse_duration_string(duration_str)

            user = self.getUserByName(nickname)
            if user is not None:
                self.kick_user(user.nUserID)
                self.send_message(self._("{nickname} has been kicked for {duration}.").format(nickname=ttstr(user.szNickname), duration=duration_str), self.getMyChannelID())
                user_data = (
                    ttstr(user.szNickname),
                    ttstr(user.szIPAddress),
                    ttstr(user.szUsername) if ttstr(user.szUsername) != "guest" and ttstr(user.szUsername) != self.accounts_config['custom_username'] else None,
                )
                self.duration_kicks[user_data] = (duration_seconds, time.time() + duration_seconds)
            else:
                # Add user to pending_kicks
                self.pending_kicks[nickname] = ("nickname", duration_seconds, time.time() + duration_seconds)
                self.send_message(self._("User '{nickname}' not found. They will be kicked when they log in for {duration}.").format(nickname=nickname, duration=duration_str), self.getMyChannelID())

        except ValueError as e:
            self.send_message(self._("Invalid command format: {e}").format(e=e), self.getMyChannelID())

    def handle_duration_kick_by_username(self, textmessage: TextMessage):
        try:
            _, *message_parts = ttstr(textmessage.szMessage).split(" ", 1)
            last_space_index = message_parts[0].rfind(" ")

            if last_space_index != -1:
                username = message_parts[0][:last_space_index].strip()
                duration_str = message_parts[0][last_space_index + 1:].strip()
            else:
                username = message_parts[0].strip()
                duration_str = ""
            duration_seconds = self.parse_duration_string(duration_str)

            user = self.getUserByUsername(ttstr(username))
            if user is not None:
                self.kick_user(user.nUserID)
                self.send_message(self._("User with username '{username}' has been kicked for {duration}.").format(username=ttstr(user.szUsername), duration=duration_str), self.getMyChannelID())
                user_data = (
                    ttstr(user.szNickname),
                    ttstr(user.szIPAddress),
                    ttstr(user.szUsername),
                )
                self.duration_kicks[user_data] = (duration_seconds, time.time() + duration_seconds)
            else:
                self.pending_kicks[username] = ("username", duration_seconds, time.time() + duration_seconds)
                self.send_message(self._("User with username '{username}' not found. They will be kicked when they log in for {duration}.").format(username=username, duration=duration_str), self.getMyChannelID())

        except ValueError as e:
            self.send_message(self._("Invalid command format: {e}").format(e=e), self.getMyChannelID())

    def handle_duration_ban(self, textmessage: TextMessage, ban_type: BanType):
        try:
            _, *message_parts = ttstr(textmessage.szMessage).split(" ", 1)
            last_space_index = message_parts[0].rfind(" ")

            if last_space_index != -1:
                nickname = message_parts[0][:last_space_index].strip()
                duration_str = message_parts[0][last_space_index + 1:].strip()
            else:
                nickname = message_parts[0].strip()
                duration_str = ""
            duration_seconds = self.parse_duration_string(duration_str)

            user = self.getUserByName(nickname)
            if user is not None:
                if ban_type == BanType.BANTYPE_IPADDR:
                    self.ban_user(user.nUserID, BanType.BANTYPE_IPADDR)
                    self.send_message(self._("{nickname} has been banned for {duration}.").format(nickname=ttstr(user.szNickname), duration=duration_str), self.getMyChannelID())
                    Thread(target=self.remove_ban_after_duration, args=(user, duration_seconds, BanType.BANTYPE_IPADDR)).start() 
                else:
                    self.ban_user(user.nUserID, BanType.BANTYPE_USERNAME)
                    self.send_message(self._("{nickname} has been banned for {duration}.").format(nickname=ttstr(user.szNickname), duration=duration_str), self.getMyChannelID())
                    Thread(target=self.remove_ban_after_duration, args=(user, duration_seconds, BanType.BANTYPE_USERNAME)).start()

                self.kick_user(user.nUserID)

            else:
                self.send_message(self._("User '{nickname}' not found. Cannot ban offline users.").format(nickname=nickname), self.getMyChannelID())
        except ValueError as e:
            self.send_message(self._("Invalid command format: {e}").format(e=e), self.getMyChannelID())

    def parse_duration_string(self, duration_str):
        duration_parts = duration_str.split(":")
        duration_seconds = 0
        for part in duration_parts:
            if part[-1] == "s":
                duration_seconds += int(part[:-1])
            elif part[-1] == "m":
                duration_seconds += int(part[:-1]) * 60
            elif part[-1] == "h":
                duration_seconds += int(part[:-1]) * 3600
            elif part[-1] == "d":
                duration_seconds += int(part[:-1]) * 24 * 3600
            elif part[-1] == "w":
                duration_seconds += int(part[:-1]) * 7 * 24 * 3600
            elif part[-1] == "mo":
                duration_seconds += int(part[:-1]) * 30 * 24 * 3600
            elif part[-1] == "y":
                duration_seconds += int(part[:-1]) * 365 * 24 * 3600
            else:
                raise ValueError(self._("Invalid duration format"))
        return duration_seconds
    
    def remove_ban_after_duration(self, user: User, duration_seconds: int, ban_type: BanType):
        time.sleep(duration_seconds)
        if ban_type == BanType.BANTYPE_IPADDR:
            self.doUnBanUser(user.szIPAddress, 0)
            self.send_message(self._("{nickname} (IP ban) has been unbanned.").format(nickname=ttstr(user.szNickname)), self.getMyChannelID())
        else:
            banned_user = BannedUser()
            banned_user.szUsername = user.szUsername
            banned_user.uBanTypes=BanType.BANTYPE_USERNAME 
            self.doUnbanUserEx(banned_user)
            self.send_message(self._("{nickname} (Username ban) has been unbanned.").format(nickname=ttstr(user.szNickname)), self.getMyChannelID())

    def handle_jail_command(self, textmessage: TextMessage):
        try:
            _, nickname = ttstr(textmessage.szMessage).split(" ", 1)
            user = self.getUserByName(nickname)
            if user is not None:
                self.bot_config["jail_users"].append(ttstr(user.szUsername))
                self.config_handler.save_bot_config(self.bot_config)

                jail_channel_id = self.getChannelIDFromPath(ttstr(self.bot_config["jail_channel"]))
                self.doMoveUser(user.nUserID, jail_channel_id)
                self.send_message(self._("{nickname} has been jailed.").format(nickname=ttstr(user.szNickname)), self.getMyChannelID())
            else:
                self.privateMessage(textmessage.nFromUserID, self._("User '{nickname}' not found.").format(nickname=ttstr(user.szNickname)))
        except ValueError:
            self.privateMessage(textmessage.nFromUserID, self._("Invalid command. Usage: /jail <nickname>"))

    def handle_unjail_command(self, textmessage: TextMessage):
        try:
            _, nickname = ttstr(textmessage.szMessage).split(" ", 1)
            user = self.getUserByName(nickname)
            if user is not None:
                if ttstr(user.szUsername) in self.bot_config["jail_users"]:
                    self.bot_config["jail_users"].remove(ttstr(user.szUsername))
                self.config_handler.save_bot_config(self.bot_config)

                root_channel_id = self.getRootChannelID()
                self.doMoveUser(user.nUserID, root_channel_id)
                self.send_message(self._("{nickname} has been unjailed.").format(nickname=ttstr(user.szNickname)), self.getMyChannelID())
            else:
                self.privateMessage(textmessage.nFromUserID, self._("User '{nickname}' not found.").format(nickname=ttstr(user.szNickname)))
        except ValueError:
            self.privateMessage(textmessage.nFromUserID, self._("Invalid command. Usage: /unjail <nickname>"))

    def handle_change_name_command(self, textmessage: TextMessage):
        """Changes the bot's nickname."""
        try:
            _, new_name = ttstr(textmessage.szMessage).split(" ", 1)
            if new_name:
                self.bot_config["nickname"] = new_name
                self.doChangeNickname(ttstr(new_name))
                self.privateMessage(textmessage.nFromUserID, self._("Bot name changed to '{new_name}'.").format(new_name=new_name))
            else:
                self.privateMessage(textmessage.nFromUserID, self._("Please provide a new name."))
        except ValueError:
            self.privateMessage(textmessage.nFromUserID, self._("Invalid command. Usage: /cn <new_name>"))

    def handle_change_status(self, textmessage: TextMessage):
        """Changes the bot's status message."""
        try:
            _, status_message = ttstr(textmessage.szMessage).split(" ", 1)
            if status_message:
                self.bot_config["status_message"] = status_message
                self.doChangeStatus(self.bot_config['gender'], ttstr(status_message))
                self.privateMessage(textmessage.nFromUserID, self._("Success"))
            else:
                self.privateMessage(textmessage.nFromUserID, self._("Please provide a message."))
        except ValueError:
            self.privateMessage(textmessage.nFromUserID, self._("Invalid command. Usage: /cs <new_status>"))

    def handle_change_gender(self, textmessage: TextMessage):
        try:
            _, gender_mode = ttstr(textmessage.szMessage).split(" ", 1)
            if gender_mode =="m".lower():
                self.bot_config["gender"] =0
                self.doChangeStatus(ttstr(self.bot_config['gender']), ttstr(self.bot_config['status_message']))
                self.privateMessage(textmessage.nFromUserID, self._("Success"))
            elif gender_mode =="f".lower():
                self.bot_config["gender"] =256
                self.doChangeStatus(ttstr(self.bot_config['gender']), ttstr(self.bot_config['status_message']))
                self.privateMessage(textmessage.nFromUserID, self._("Success"))
            elif gender_mode =="n".lower():
                self.bot_config["gender"] =4096
                self.doChangeStatus(ttstr(self.bot_config['gender']), ttstr(self.bot_config['status_message']))
                self.privateMessage(textmessage.nFromUserID, self._("Success"))
            else:
                self.privateMessage(textmessage.nFromUserID, self._("Available modes are: m for male, f for female, n for neutral."))
        except ValueError:
            self.privateMessage(textmessage.nFromUserID, self._("Invalid command. Usage: /cg gender. Available modes: m for male, f for female, n for neutral."))

    def save_bot_config(self, textmessage: TextMessage):
        self.config_handler.save_bot_config(self.bot_config)
        self.privateMessage(textmessage.nFromUserID, self._("Bot configuration saved."))

    def handle_jails_command(self, textmessage: TextMessage):
        jailed_users = self.bot_config["jail_users"]
        if jailed_users:
            jailed_users_str = ", ".join(jailed_users)
            self.privateMessage(textmessage.nFromUserID, self._("Jailed users: {jailed_users}").format(jailed_users=jailed_users_str))
        else:
            self.privateMessage(textmessage.nFromUserID, self._("No users are currently jailed."))

    def handle_clear_command(self, textmessage: TextMessage):
        """Clears bans and duration kicks."""
        parts = ttstr(textmessage.szMessage).split(" ", 1)
        if len(parts) == 2:
            target = ttstr(parts[1])
            self.clear_for_target(target)
        else:
            self.clear_all()

    def clear_for_target(self, target):
        """Clears bans, duration kicks, and pending kicks for a specific user."""
        # Try to unban by username
        if target in self.banned_users:
            self.unban_user(self.banned_users[target])
            self.send_message(self._("Cleared bans and duration kicks for {target}.").format(target=ttstr(target)), self.getMyChannelID())
            return

        # Check in duration_kicks (could be nickname, IP, or username)
        for user_data in list(self.duration_kicks.keys()):
            (nickname, ip_address, username) = user_data
            if target in (nickname, ip_address, username):
                del self.duration_kicks[user_data]
                self.send_message(self._("Cleared duration kick for {target}.").format(target=ttstr(target)), self.getMyChannelID())
                return

        # Check in pending_kicks (could be nickname or username)
        if target.lower() in self.pending_kicks:
            del self.pending_kicks[target.lower()]
            self.send_message(self._("Cleared pending kick for {target}.").format(target=ttstr(target)), self.getMyChannelID())
            return

        self.send_message(self._("Target '{target}' not found.").format(target=ttstr(target)), self.getMyChannelID())

    def clear_all(self):
        """Clears all bans, duration kicks, and pending kicks."""

        # Check if any of the dictionaries have entries
        if not self.banned_users and not self.duration_kicks and not self.pending_kicks:
            self.send_message(self._("There are no active bans, duration kicks, or pending kicks to clear."), self.getMyChannelID())
            return

        # Make a copy of the keys before iterating
        ban_keys = list(self.banned_users.keys()) 

        for ban_key in ban_keys: 
            try:
                self.unban_user(self.banned_users[ban_key]) 
                self.clear_kick_duration(self.banned_users[ban_key])
            except KeyError as e:
                print(self._("KeyError during clear_all: {e}").format(e=e))

        self.duration_kicks.clear()
        self.pending_kicks.clear()
        self.send_message(self._("Cleared all bans and duration kicks."), self.getMyChannelID())

    def unban_user(self, banned_user):
        """Unbans a user based on the stored banned_users dictionary."""
        try:
            if banned_user.uBanTypes == BanType.BANTYPE_IPADDR:
                self.doUnBanUser(banned_user.szIPAddress, 0)
                del self.banned_users[banned_user.szIPAddress]
            elif banned_user.uBanTypes == BanType.BANTYPE_USERNAME:
                self.doUnbanUserEx(banned_user)
                del self.banned_users[banned_user.szUsername]
        except:
            print(self._("Error during unban_user: {e}").format(e=e))

    def clear_kick_duration(self, banned_user):
        """Clears duration kicks for a user."""
        try:
            if ttstr(banned_user.szNickname) in self.duration_kicks:
                del self.duration_kicks[banned_user.szNickname]
        except KeyError as e:
            print(self._("KeyError during clear_kick_duration: {e}").format(e=e))

    def handle_admin_broadcast(self, textmessage: TextMessage):
        try:
            message = ttstr(textmessage.szMessage).split("/b ", 1)[1]
            self.send_broadcast_message(self._("Message from administrators: {message}").format(message=message))
        except:
            pass

    def getUserByName(self, nickname):
        nickname = ttstr(nickname)
        users = self.getServerUsers()
        for user in users:
            if user.szNickname.strip() == nickname:
                return user
        return None

    def privateMessage(self, user_id, message_text):
        message = TextMessage()
        message.nMsgType = 1
        message.nToUserID = user_id
        message.nFromUserID = self.getMyUserID()
        message.szMessage = ttstr(message_text)
        self.doTextMessage(message)

    def send_message(self, message_text, channel_id=None):
        if channel_id is None:
            channel_id=self.getMyChannelID()
        message = TextMessage()
        message.nMsgType = TextMsgType.MSGTYPE_CHANNEL
        message.nChannelID = channel_id
        message.szMessage = ttstr(message_text)
        self.doTextMessage(message)

    def is_vpn(self, ip_address):
        base_url = f"http://ip-api.com/json/{ip_address}"
        params = {
            "fields": "status,message,country,countryCode,city,proxy",
        }

        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "success":
                if data.get("proxy") and self.bot_config['vpn_detection']==True:
                    return True
                else:
                    return False

            elif data.get("status") == "fail":
                 print(self._("Error: {error} for IP: {ip_address}").format(error=data.get('message'), ip_address=ip_address))
                 return False


        except requests.exceptions.RequestException as e:
            print(self._("Error checking VPN status: {e} for IP: {ip_address}").format(e=e, ip_address=ip_address))
            return False

    def ban_user(self, user_id, ban_type=BanType.BANTYPE_USERNAME):
        banned_user = BannedUser()
        while True:
            user = self.getUser(user_id)
            if user is not None:
                break
            else:
                continue
        if ban_type == BanType.BANTYPE_IPADDR:
            while True:
                ip_address=user.szIPAddress
                if ip_address is None or ip_address == "":
                    continue
                else:
                    banned_user.szIPAddress =ip_address
                    break
            self.banned_users[user.szIPAddress] = banned_user
            banned_user.uBanTypes =BanType.BANTYPE_IPADDR
        else:
            if user.szUsername=='guest' or user.szUsername==self.accounts_config['custom_username']:
                while True:
                    ip_address=user.szIPAddress
                    if ip_address is None or ip_address == "":
                        continue
                    else:
                        banned_user.szIPAddress =ip_address
                        break
                self.banned_users[user.szIPAddress] = banned_user
                banned_user.uBanTypes =BanType.BANTYPE_IPADDR
            else:
                banned_user.szUsername = user.szUsername
                self.banned_users[user.szUsername] = banned_user
                banned_user.uBanTypes =BanType.BANTYPE_USERNAME
        self.doBan(banned_user)

    def send_broadcast_message(self, message_text):
        message = TextMessage()
        message.nMsgType = TextMsgType.MSGTYPE_BROADCAST
        message.szMessage = ttstr(message_text)
        self.doTextMessage(message)

    def kick_user(self, user_id):
        user_channel_id = self.getUser(user_id).nChannelID
        self.doKickUser(user_id, user_channel_id)
        self.doKickUser(user_id, 0)

    def send_broadcast_messages_at_intervals(self, messages, interval_minutes):
        random.seed()
        while True:
            if self.bot_config["random_message_interval"] > 0:
                message = random.choice(messages)
                nickname = self.get_nicknames()

                message = message.format(name=ttstr(nickname))

                self.send_broadcast_message(message)

                time.sleep(self.bot_config["random_message_interval"] * 60)

    def get_nicknames(self):
        online_users = self.getServerUsers()
        if online_users:
            random_user = random.choice(online_users)
            return random_user.szNickname
        else:
            return None

    def translate_and_send_message(self, textmessage):
        self.translation_pool.submit(self._translate_and_send, textmessage)  # Submit task to the pool

    def _translate_and_send(self, textmessage):
        if textmessage.szMessage != self.last_translated_message:
            try:
                detected_lang = langdetect.detect(ttstr(textmessage.szMessage))
                if detected_lang == self.target_lang:
                    return  # Skip translation if the source language matches the target language

                translated = GoogleTranslator(source=self.source_lang, target=self.target_lang).translate(ttstr(textmessage.szMessage))
                self.send_message(f"{translated}")
                self.last_translated_message = textmessage.szMessage
            except ValueError as e:
                self.send_message(self._("Error: Language not supported ({e})").format(e=e))
                self.auto_translate = False

if __name__ == "__main__":
    logging.basicConfig(filename='errors.log', level=logging.ERROR, 
                        format='%(asctime)s - %(levelname)s - %(message)s')
    parser = argparse.ArgumentParser(description="TT Utilities")
    parser.add_argument("-c", "--cookiefile", help="Path to the cookies file.")
    args = parser.parse_args()

    bot = TTUtilities(cookiefile=args.cookiefile)
    messages = load_messages("messages.txt")
    message_thread = threading.Thread(target=bot.send_broadcast_messages_at_intervals, args=(messages, bot.bot_config["random_message_interval"]))
    message_thread.start()

    while True:
        try:
            bot.runEventLoop()
        except Exception as e:
            logging.exception(f"An error occured: {e}")