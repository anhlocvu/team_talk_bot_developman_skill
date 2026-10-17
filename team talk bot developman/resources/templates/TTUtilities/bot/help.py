import configparser
from bot.config_handler import ConfigHandler
import gettext


class HelpCommands():
    """Contains all commands when using /help"""
    config_handler = ConfigHandler()
    def __init__(self):
        self.bot_config = self.config_handler.get_bot_config()
        self.language=self.bot_config.get("language")

        # translation
        gettext.bindtextdomain("messages", "locales")
        gettext.textdomain("messages")
  
        try:
            translation = gettext.translation("messages", "locales", [self.language])
            translation.install()
            self._ = translation.gettext
        except FileNotFoundError:
            print(f"Language '{self.language}' not found, defaulting to English.")
            translation = gettext.translation("messages", "locales", ["en"])
            translation.install()
            self._ = gettext.gettext

        self.commands = {
            self._("/weather"): self._("Get the current weather for your location or a specified user. Usage: /weather optional:nickname"),
            self._("/reboot"): self._("Reboots the server (requires authorization)"),
            self._("/exec"): self._("Executes a command on the server via SSH (requires authorization). Usage: /exec [command]"),
            self._("/search"): self._("Search Wikipedia and get a summary. Usage: /search your query"),
            self._("/file"): self._("Download a Wikipedia page as an HTML file. Usage: /file your query"),
            self._("/say"): self._("Make the bot speak the given text. Usage: /say text"),
            self._("Note"): self._("You can also use '  <text> for tts, it's the same as /say, just for ease of use"),
            self._("/t"): self._("Enable or disable auto-translation for channel messages. Usage: /t <source_lang> <target_lang>"),
            self._("/pt"): self._("Enable or disable private translate mode. Usage: /pt <source_lang> <target_lang>"),
            self._("/voice voiceName"): self._("Set the voice name for text to speech."),
            self._("/rate value"): self._("Set the voice rate, value from -100 to 100."),
            self._("/pitch value"): self._("Set the voice pitch, value from -100 to 100."),
            self._("/volume value"): self._("Set the voice volume, value from 0.1 to 1.0."),
            self._("/get_voices langcode"): self._("Get all voices for a specified language, if provided, if not: Get all available voices for all languages."),
            self._("/ld"): self._("Enable or disable language detection."),
            self._("/db name duration"): self._("Admins only: Bans someone by IP address for a specified period."),
            self._("/udb name duration"): self._("Admins only: Bans a username for a specified period."),
            self._("/dk name duration"): self._("Admins only: Kicks someone for a specified period."),
            self._("/clear argument"): self._("Admins only: Clears the duration ban or kick for a specified user. If sent without arguments: Clears all duration ban and kick."),
            self._("/s"): self._("Admins only: Stop streaming a speech file."),
            self._("/b message"): self._("Admins only: Sends a broadcast message to the server."),
            self._("/jail <name>"): self._("For authorized users only, Adds someone to the jails list and move them to the jail channel. This adds the username to the list and not the nickname."),
            self._("/unjail <name>"): self._("For authorized users. Removes someone from the jails list and moves them back to the root channel"),
            self._("/jails"): self._("Admins only: Gets the list of users who are in the jails list"),
            self._("/cn <new name"): self._("Admins only: Changes the bot's name."),
            self._("/cs <status>"): self._("Admins only: Changes the status message"),
            self._("/cg mode"): self._("Admins only: Changes the bot's gender. Available modes: m for male, f for female, n for neutral."),
            self._("/private <name>"): self._("Moves you and another one to a private hidden channel where no one can see it. This channel is only limited to 2 users only and will be deleted after both users log out of the server."),
            self._("/save"): self._("Admins only: Saves the configuration in case you changed the bot's name and want to save it."),
            self._("/help"): self._("Show this help message.")
        }
