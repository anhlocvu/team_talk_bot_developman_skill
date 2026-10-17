# TeamTalk 5 Python API Reference (`TeamTalkPy`)

This document provides a comprehensive, exhaustive reference for all classes, structures, enums, methods, and event callbacks in the `TeamTalkPy` wrapper for the TeamTalk 5 Client SDK DLL (`TeamTalk5.dll`).

---

## 1. Architecture Overview

`TeamTalkPy` (`TeamTalk5.py`) is an object-oriented Python wrapper built over `ctypes` that interfaces directly with the native C/C++ TeamTalk 5 Client library (`TeamTalk5.dll` on Windows, `libTeamTalk5.so` on Linux, `libTeamTalk5.dylib` on macOS).

> [!IMPORTANT]
> **Zero Modification Principle on `TeamTalk5.py`**:
> `TeamTalk5.py` is the official SDK wrapper distributed by BearWare.dk. **NEVER modify, patch, or edit `TeamTalk5.py`**. Keep it 100% stock. All DLL loading configurations, path resolutions, and custom wrappers must be implemented strictly within your bot's entrypoint or application code.

> [!TIP]
> **Dynamic SDK Discovery Rule**:
> While this document catalogs known APIs, BearWare periodically releases new SDK versions with additional flags, events, or methods. Whenever you develop a bot, diagnose an issue, or upgrade the SDK, **ALWAYS inspect `TeamTalk5.py` directly** in `teamtalkpy/TeamTalk5.py` or `resources/teamtalkpy/TeamTalk5.py`. Section 6 below details how to parse it.

### Key Execution Models
There are two primary paradigms for using `TeamTalk`:
1. **Event Callback Model (`runEventLoop`)** - *Recommended*: Subclass `TeamTalk` and override `on*` callback methods (e.g. `onConnectSuccess`, `onCmdUserTextMessage`). Call `bot.runEventLoop(timeout_ms)` in your main loop.
2. **Polling Model (`getMessage`)**: Call `msg = client.getMessage(timeout_ms)` and inspect `msg.nClientEvent` directly.

---

## 2. Core String & Encoding Rules (`ttstr`)

TeamTalk uses wide characters (UTF-16) on Windows and UTF-8 on Linux/macOS.

### Helper Function: `ttstr(val)`
- **Windows**: Returns native string as-is (passed to `c_wchar_p`).
- **Linux/macOS**: Automatically encodes Python `str` to UTF-8 bytes and decodes bytes back to `str`.
- **Rule**: Whenever passing string parameters into TeamTalk functions (or reading string fields like `msg.szMessage`, `user.szNickname`), ALWAYS wrap them with `ttstr(...)`.

### Message Length Limits (`TT_STRLEN = 512`)
- A single `TextMessage.szMessage` field is limited to 512 characters.
- For longer messages, use the bundled helpers:
  - `buildTextMessage(content, nMsgType, szFromUsername, nChannelID, nToUserID) -> list[TextMessage]`
  - `rebuildTextMessage(msgs: list[TextMessage]) -> str`

---

## 3. Enumerations & Constants

### 3.1 `ClientEvent` (Event IDs)
Events dispatched by the TeamTalk engine via `getMessage()` and handled in `runEventLoop()`:

| Event Identifier | Callback Method | Description |
|---|---|---|
| `CLIENTEVENT_CON_SUCCESS` | `onConnectSuccess()` | Successfully connected to server |
| `CLIENTEVENT_CON_FAILED` | `onConnectFailed()` | TCP/UDP connection attempt failed |
| `CLIENTEVENT_CON_LOST` | `onConnectionLost()` | Connection to server was dropped |
| `CLIENTEVENT_CON_CRYPT_ERROR` | `onConnectCryptError(clienterrormsg)` | Encryption / SSL handshake error |
| `CLIENTEVENT_CMD_PROCESSING` | `onCmdProcessing(cmdId, complete)` | Asynchronous command in progress |
| `CLIENTEVENT_CMD_ERROR` | `onCmdError(cmdId, clienterrormsg)` | Command failed with error from server |
| `CLIENTEVENT_CMD_SUCCESS` | `onCmdSuccess(cmdId)` | Command completed successfully |
| `CLIENTEVENT_CMD_MYSELF_LOGGEDIN` | `onCmdMyselfLoggedIn(userid, useraccount)` | Bot successfully authenticated |
| `CLIENTEVENT_CMD_MYSELF_LOGGEDOUT` | `onCmdMyselfLoggedOut()` | Bot logged out |
| `CLIENTEVENT_CMD_MYSELF_KICKED` | `onCmdMyselfKickedFromChannel(channelid, user)` | Bot kicked from channel |
| `CLIENTEVENT_CMD_USER_LOGGEDIN` | `onCmdUserLoggedIn(user)` | Another user logged into server |
| `CLIENTEVENT_CMD_USER_LOGGEDOUT` | `onCmdUserLoggedOut(user)` | Another user logged out |
| `CLIENTEVENT_CMD_USER_UPDATE` | `onCmdUserUpdate(user)` | User details/status/subscriptions updated |
| `CLIENTEVENT_CMD_USER_JOINED` | `onCmdUserJoinedChannel(user)` | User entered a channel |
| `CLIENTEVENT_CMD_USER_LEFT` | `onCmdUserLeftChannel(channelid, user)` | User exited a channel |
| `CLIENTEVENT_CMD_USER_TEXTMSG` | `onCmdUserTextMessage(textmessage)` | Text message received (channel, PM, broadcast) |
| `CLIENTEVENT_CMD_CHANNEL_NEW` | `onCmdChannelNew(channel)` | New channel created on server |
| `CLIENTEVENT_CMD_CHANNEL_UPDATE` | `onCmdChannelUpdate(channel)` | Channel topic, codec, or properties updated |
| `CLIENTEVENT_CMD_CHANNEL_REMOVE` | `onCmdChannelRemove(channel)` | Channel deleted |
| `CLIENTEVENT_CMD_SERVER_UPDATE` | `onCmdServerUpdate(serverproperties)` | Server MOTD or configuration changed |
| `CLIENTEVENT_CMD_FILE_NEW` | `onCmdFileNew(remotefile)` | File uploaded to channel |
| `CLIENTEVENT_CMD_FILE_REMOVE` | `onCmdFileRemove(remotefile)` | File removed from channel |
| `CLIENTEVENT_USER_RECORD_MEDIAFILE`| `onUserRecordMediaFile(userid, mediafileinfo)` | User started recording media |
| `CLIENTEVENT_CMD_USERACCOUNT_NEW` | `onUserAccountNew(useraccount)` | User account created |
| `CLIENTEVENT_CMD_USERACCOUNT_REMOVE`| `onUserAccountRemove(useraccount)` | User account deleted |
| `CLIENTEVENT_USER_STATECHANGE` | `onUserStateChange(user)` | User voice state, mute, or video toggled |
| `CLIENTEVENT_USER_AUDIOBLOCK` | `onUserAudioBlock(userid, streamtype)` | Audio block received for user |
| `CLIENTEVENT_STREAM_MEDIAFILE` | `onStreamMediaFile(mediafileinfo)` | Channel media streaming status updated |
| `CLIENTEVENT_CMD_USERACCOUNT` | `onUserAccount(useraccount)` | Account details returned from query |
| `CLIENTEVENT_CMD_BANNEDUSER` | `onBannedUser(banneduser)` | Ban entry returned from ban query |
| `CLIENTEVENT_CMD_SERVERSTATISTICS` | `onServerStatistics(serverstatistics)` | Server statistics returned from query |
| `CLIENTEVENT_INTERNAL_ERROR` | `onInternalError(clienterrormsg)` | Internal client engine error |
| `CLIENTEVENT_SOUNDDEVICE_ADDED` | `onSoundDeviceAdded(sounddevice)` | Audio device plugged in |
| `CLIENTEVENT_SOUNDDEVICE_REMOVED` | `onSoundDeviceRemoved(sounddevice)` | Audio device removed |
| `CLIENTEVENT_SOUNDDEVICE_UNPLUGGED` | `onSoundDeviceUnplugged(sounddevice)` | Active audio device disconnected |
| `CLIENTEVENT_SOUNDDEVICE_NEW_DEFAULT_INPUT` | `onSoundDeviceNewDefaultInput(...)` | OS changed default mic |
| `CLIENTEVENT_SOUNDDEVICE_NEW_DEFAULT_OUTPUT`| `onSoundDeviceNewDefaultOutput(...)` | OS changed default speaker |

### 3.2 `TextMsgType` (Message Targets)
- `MSGTYPE_NONE = 0`: Invalid
- `MSGTYPE_USER = 1`: Private direct message to specific `nToUserID`
- `MSGTYPE_CHANNEL = 2`: Message to current or target `nChannelID`
- `MSGTYPE_BROADCAST = 3`: Broadcast message to all users on the server (requires `USERRIGHT_TEXTMESSAGE_BROADCAST`)
- `MSGTYPE_CUSTOM = 4`: Custom application binary/text payload

### 3.3 `UserRight` (Permission Flags)
Bitmask flags in `UserAccount.uUserRights`:
- `USERRIGHT_NONE = 0x00000000`
- `USERRIGHT_MULTI_LOGIN = 0x00000001`: Allow multiple logins with same account
- `USERRIGHT_VIEW_ALL_USERS = 0x00000002`: View users in all channels
- `USERRIGHT_CREATE_TEMPORARY_CHANNEL = 0x00000004`: Create temporary channels
- `USERRIGHT_MODIFY_CHANNELS = 0x00000008`: Create, modify, delete permanent channels
- `USERRIGHT_TEXTMESSAGE_BROADCAST = 0x00000010`: Send broadcast messages
- `USERRIGHT_KICK_USERS = 0x00000020`: Kick users from channels or server
- `USERRIGHT_BAN_USERS = 0x00000040`: Ban users from channels or server
- `USERRIGHT_MOVE_USERS = 0x00000080`: Move users between channels
- `USERRIGHT_OPERATOR_ENABLE = 0x00000100`: Grant/revoke channel operator rights
- `USERRIGHT_UPLOAD_FILES = 0x00000200`: Upload files
- `USERRIGHT_DOWNLOAD_FILES = 0x00000400`: Download files
- `USERRIGHT_UPDATE_SERVERPROPERTIES = 0x00000800`: Update server configuration
- `USERRIGHT_TRANSMIT_VOICE = 0x00001000`: Transmit microphone audio
- `USERRIGHT_TRANSMIT_VIDEOCAPTURE = 0x00002000`: Transmit webcam video
- `USERRIGHT_TRANSMIT_DESKTOP = 0x00004000`: Share desktop screen
- `USERRIGHT_TRANSMIT_MEDIAFILE_AUDIO = 0x00010000`: Stream audio media files
- `USERRIGHT_TRANSMIT_MEDIAFILE_VIDEO = 0x00020000`: Stream video media files
- `USERRIGHT_TEXTMESSAGE_USER = 0x00400000`: Send private text messages
- `USERRIGHT_TEXTMESSAGE_CHANNEL = 0x00800000`: Send channel text messages

### 3.4 `Subscription` (Media Stream Subscriptions)
Used with `doSubscribe(nUserID, uSubscriptions)`:
- `SUBSCRIBE_NONE = 0x00000000`
- `SUBSCRIBE_USER_MSG = 0x00000001`: Private messages from user
- `SUBSCRIBE_CHANNEL_MSG = 0x00000002`: Channel messages
- `SUBSCRIBE_BROADCAST_MSG = 0x00000004`: Broadcast messages
- `SUBSCRIBE_VOICE = 0x00000010`: Voice audio from user
- `SUBSCRIBE_VIDEOCAPTURE = 0x00000020`: Webcam stream from user
- `SUBSCRIBE_DESKTOP = 0x00000040`: Desktop stream from user
- `SUBSCRIBE_MEDIAFILE = 0x00000100`: Channel media file stream

### 3.5 `StreamType` (Audio & Media Stream Types)
- `STREAMTYPE_NONE = 0x00000000`
- `STREAMTYPE_VOICE = 0x00000001`: Standard microphone voice stream
- `STREAMTYPE_VIDEOCAPTURE = 0x00000002`: Web camera stream
- `STREAMTYPE_MEDIAFILE_AUDIO = 0x00000004`: Audio streamed from file
- `STREAMTYPE_MEDIAFILE_VIDEO = 0x00000008`: Video streamed from file
- `STREAMTYPE_DESKTOP = 0x00000010`: Shared desktop stream

### 3.6 `ChannelType` (Channel Attributes)
- `CHANNEL_DEFAULT = 0x00000000`: Permanent channel
- `CHANNEL_PERMANENT = 0x00000001`: Saved to server database
- `CHANNEL_SOLITARY = 0x00000002`: Users cannot hear other channels
- `CHANNEL_CLASSROOM = 0x00000004`: Only operators can transmit voice/video
- `CHANNEL_OPERATOR_RECVONLY = 0x00000008`: Non-operators can only transmit to operators
- `CHANNEL_NO_VOICE = 0x00000010`: Voice transmission disabled
- `CHANNEL_NO_VIDEOCAPTURE = 0x00000020`: Video transmission disabled
- `CHANNEL_NO_DESKTOP = 0x00000040`: Desktop sharing disabled

---

## 4. Key Data Structures (`ctypes.Structure`)

### 4.1 `TextMessage`
Represents an incoming or outgoing text message:
```python
class TextMessage(Structure):
    nMsgType: INT32          # TextMsgType (1: User, 2: Channel, 3: Broadcast)
    nFromUserID: INT32       # UserID of sender (0 if system or outbound)
    szFromUsername: TTCHAR   # Username of sender (use ttstr)
    nToUserID: INT32         # Destination UserID (if nMsgType == MSGTYPE_USER)
    nChannelID: INT32        # Destination ChannelID (if nMsgType == MSGTYPE_CHANNEL)
    szMessage: TTCHAR        # Message body (capped at TT_STRLEN=512)
    bMore: BOOL              # True if message is continued in subsequent packet
```

### 4.2 `User`
Information about a user connected to the server:
```python
class User(Structure):
    nUserID: INT32
    szUsername: TTCHAR
    nUserData: INT32
    uUserType: UINT32        # UserType.USERTYPE_DEFAULT or ADMIN
    szIPAddress: TTCHAR
    nChannelID: INT32        # Currently joined channel
    uLocalSubscriptions: UINT32
    szNickname: TTCHAR       # Display name
    nStatusMode: INT32       # STATUSMODE_AVAILABLE, AWAY, etc.
    szStatusMsg: TTCHAR      # Status text
    uUserState: UINT32       # USERSTATE_VOICE, MUTE_VOICE, etc.
```

### 4.3 `Channel`
Information about a TeamTalk channel:
```python
class Channel(Structure):
    nChannelID: INT32
    nParentID: INT32         # 0 if subchannel of root
    szName: TTCHAR           # Channel name
    szTopic: TTCHAR          # Channel description/topic
    szPassword: TTCHAR       # Password (empty string if open)
    uChannelType: UINT32     # ChannelType bitmask
    nMaxUsers: INT32         # Max concurrent users
    audiocodec: AudioCodec   # Opus/Speex codec configuration
```

### 4.4 `ServerProperties`
Information and configuration of the TeamTalk server:
```python
class ServerProperties(Structure):
    szServerName: TTCHAR
    szMOTD: TTCHAR           # Message of the Day
    nMaxUsers: INT32
    nTcpPort: INT32
    nUdpPort: INT32
    nUserTimeout: INT32
    szServerVersion: TTCHAR
    szServerProtocolVersion: TTCHAR
```

---

## 5. `TeamTalk` Class Complete Method Reference

### 5.1 Connection & Lifecycle
- `__init__()`: Initializes the internal polling instance (`TT_InitTeamTalkPoll`). Raises `TeamTalkError` on failure.
- `closeTeamTalk() -> bool`: Releases the native client instance.
- `connect(szHostAddress, nTcpPort: int, nUdpPort: int, nLocalTcpPort: int = 0, nLocalUdpPort: int = 0, bEncrypted: bool = False) -> bool`:
  Initiates connection to the server. Returns `True` if connection process started.
- `disconnect() -> bool`: Disconnects from current server.
- `doPing() -> int`: Sends a ping to measure latency. Returns command ID.
- `doQuit() -> int`: Cleanly notifies server of quitting. Returns command ID.
- `getFlags() -> int`: Returns current `ClientFlags` (e.g. `CLIENT_CONNECTED`, `CLIENT_AUTHORIZED`).

### 5.2 Authentication & User State
- `doLogin(szNickname, szUsername, szPassword, szClientname) -> int`:
  Logs into the server with credentials. Returns command ID. Dispatches `CLIENTEVENT_CMD_MYSELF_LOGGEDIN` on success.
- `doLogout() -> int`: Logs out current session.
- `doChangeNickname(szNewNick) -> int`: Changes display nickname on server.
- `doChangeStatus(nStatusMode: int, szStatusMessage) -> int`: Updates status mode (Available, Away) and status message.
- `getMyUserID() -> int`: Returns the bot's own `UserID`.
- `getMyUserAccount() -> UserAccount`: Returns the bot's `UserAccount` details and rights.
- `getUser(nUserID: int) -> User`: Retrieves user details by ID.
- `getUserByUsername(szUsername) -> User`: Retrieves user details by username.
- `getServerUsers() -> list[User]`: Returns an array of all connected users on the server.

### 5.3 Channels
- `getRootChannelID() -> int`: Returns the ID of the root channel (typically 1).
- `getMyChannelID() -> int`: Returns the ID of the channel the bot is currently in.
- `getChannel(nChannelID: int) -> Channel`: Retrieves channel properties by ID.
- `getChannelPath(nChannelID: int) -> str`: Returns channel path string (e.g. `/Lobby/Music`).
- `getChannelIDFromPath(szChannelPath) -> int`: Resolves a channel path string to its ID.
- `getChannelUsers(nChannelID: int) -> list[User]`: Returns users in the specified channel.
- `getServerChannels() -> list[Channel]`: Returns array of all channels on the server.
- `doJoinChannel(channel: Channel) -> int`: Joins a channel using a `Channel` struct.
- `doJoinChannelByID(nChannelID: int, szPassword) -> int`: Joins channel by ID and password.
- `doLeaveChannel() -> int`: Leaves the current channel.
- `doMakeChannel(lpChannel: Channel) -> int`: Creates a new channel.
- `doUpdateChannel(lpChannel: Channel) -> int`: Updates channel name, topic, or properties.
- `doRemoveChannel(nChannelID: int) -> int`: Deletes a channel.

### 5.4 Text Messaging
- `doTextMessage(msg: TextMessage) -> int`: Sends a text message (user, channel, or broadcast).
- `buildTextMessage(...)`: Splits a large string into chunks compliant with `TT_STRLEN`.
- `rebuildTextMessage(...)`: Reassembles chunks into full string.

### 5.5 Media Streaming & Audio Transmission
- `enableVoiceTransmission(bEnable: bool) -> bool`: Enables or disables microphone transmission.
- `startStreamingMediaFileToChannel(szMediaFilePath, lpVideoCodec: VideoCodec) -> bool`:
  Streams a media file (MP3, WAV, OGG, WebM) directly into the bot's channel. Pass `None` for `lpVideoCodec` for audio-only files.
- `stopStreamingMediaFileToChannel() -> bool`: Stops current channel media file stream.
- `getMediaFileInfo(szMediaFilePath) -> MediaFileInfo`: Reads metadata (duration, bitrate, channels) of a media file.
- `initLocalPlayback(szMediaFilePath, lpMediaFilePlayback: MediaFilePlayback) -> int`: Plays a media file locally.
- `stopLocalPlayback(nPlaybackSessionID: int) -> bool`: Stops local playback.

### 5.6 Raw Audio Blocks (PCM)
- `enableAudioBlockEvent(nUserID: int, uStreamTypes: int, bEnable: bool) -> bool`: Enables audio block event interception.
- `enableAudioBlockEventEx(nUserID: int, uStreamTypes: int, lpAudioFormat: AudioFormat, bEnable: bool) -> bool`: Enables audio block interception with custom resampling.
- `insertAudioBlock(lpAudioBlock: AudioBlock) -> bool`: Inserts raw PCM audio blocks into the transmission stream.
- `acquireUserAudioBlock(uStreamTypes: StreamType, nUserID: int) -> POINTER(AudioBlock)`: Retrieves incoming audio block.
- `releaseUserAudioBlock(lpAudioBlock: POINTER(AudioBlock)) -> bool`: Releases acquired audio block.

### 5.7 Sound Devices
- `getSoundDevices() -> list[SoundDevice]`: Lists all host audio input/output devices.
- `getDefaultSoundDevices() -> tuple(int, int)`: Returns default input and output device IDs.
- `initSoundInputDevice(indev: int) -> bool`: Activates input sound device (mic).
- `initSoundOutputDevice(outdev: int) -> bool`: Activates output sound device (speakers).

### 5.8 Server Administration & Moderation
- `doKickUser(nUserID: int, nChannelID: int) -> int`: Kicks user from channel (or server if `nChannelID=0`).
- `doBanUser(nUserID: int, nChannelID: int) -> int`: Bans user from channel.
- `doBanUserEx(nUserID: int, uBanTypes: BanType) -> int`: Bans user by IP or username.
- `doUnBanUser(szIPAddress, nChannelID: int) -> int`: Removes IP ban.
- `doMoveUser(nUserID: int, nChannelID: int) -> int`: Moves user to a different channel.
- `doChannelOp(nUserID: int, nChannelID: int, bMakeOperator: bool) -> int`: Grants/revokes channel operator status.
- `doQueryServerStats() -> int`: Queries server traffic and user count statistics.
- `getServerProperties() -> ServerProperties`: Retrieves server properties.
- `doUpdateServer(lpServerProperties: ServerProperties) -> int`: Updates server configuration.
- `doSaveConfig() -> int`: Saves current server state to server config file.
- `doListUserAccounts(nIndex: int, nCount: int) -> int`: Lists server user accounts.
- `doNewUserAccount(lpUserAccount: UserAccount) -> int`: Creates/updates server account.
- `doDeleteUserAccount(szUsername) -> int`: Deletes user account from server.
- `doListBans(nChannelID: int, nIndex: int, nCount: int) -> int`: Queries server ban list.

---

## 6. Dynamic SDK Discovery: Reading `TeamTalk5.py` Directly

When developing a new bot or adapting to a newly released TeamTalk SDK version, always inspect `TeamTalk5.py` directly. The file is structured cleanly into predictable sections:

### 6.1 Finding Events and Their Respective Callback Methods
1. Locate `class ClientEvent` to inspect all event integer constants:
   ```python
   # Search for: class ClientEvent
   CLIENTEVENT_CON_SUCCESS = 1
   CLIENTEVENT_USER_TEXTMESSAGE = 17
   ...
   ```
2. Locate `def runEventLoop(self, nTimeoutMS)` inside `class TeamTalk`:
   Examine the `if/elif` cascade inside `runEventLoop()`. It maps every `msg.nClientEvent` directly to its corresponding callback name:
   ```python
   # If msg.nClientEvent == ClientEvent.CLIENTEVENT_USER_TEXTMESSAGE:
   #     self.onCmdUserTextMessage(textmessage)
   ```
   This gives you the exact callback method signature and parameter names to override in your bot class.

### 6.2 Finding Server Actions (`do*`) and State Queries (`get*`)
1. Search for `def do` inside `class TeamTalk`:
   Shows all commands that transmit packets to the server (`doLogin`, `doJoinChannelByID`, `doTextMessage`, `doKickUser`, `doBanUser`, `doChangeStatus`, etc.). Check argument types and default values.
2. Search for `def get` inside `class TeamTalk`:
   Shows all local cache lookups and queries (`getUser`, `getChannel`, `getChannelUsers`, `getMyUserID`, `getMyUserRights`, `getServerProperties`, etc.).
3. Search for `def init` or `def set`:
   Shows hardware and license initializers (`initSoundInputDevice`, `initSoundOutputDevice`, `setLicense`).

### 6.3 Inspecting Struct Field Definitions (`_fields_`)
All data structures in `TeamTalk5.py` inherit from `ctypes.Structure`. To discover available attributes on an object (e.g., `user`, `channel`, `msg`):
1. Search for `class <StructName>(Structure):` (e.g. `class User(Structure):`, `class TextMessage(Structure):`).
2. Read the `_fields_ = [...]` tuple list. For example, in `class User`:
   ```python
   _fields_ = [
       ("nUserID", INT32),
       ("szNickname", TTCHAR * TT_STRLEN),
       ("uUserState", UINT32),
       ("uUserRights", UINT32),
       ("nChannelID", INT32),
       ...
   ]
   ```
   This tells you the exact field name, whether it is an integer or string (`szNickname`), and whether it needs `ttstr()` unpacking.

### 6.4 Inspecting User Rights, States, and Error Codes
- **Permissions**: Search for `class UserRight:` to inspect all bitwise permission flags (e.g., `USERRIGHT_TRANSMIT_VOICE`, `USERRIGHT_MODIFY_CHANNELS`, `USERRIGHT_KICK_USERS`).
- **User States**: Search for `class UserState:` (e.g., `USERSTATE_VOICE`, `USERSTATE_MUTE_VOICE`, `USERSTATE_STREAM_MEDIAFILE`).
- **Client Errors**: Search for `class ClientError:` to decode command failure codes returned in `onCmdError(cmdId, clienterrormsg)`.

