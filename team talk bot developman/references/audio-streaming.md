# TeamTalk 5 Audio & Media Streaming Guide

This guide details how to work with audio playback, microphone transmission, media file streaming, and raw PCM audio blocks in TeamTalk 5 using Python.

---

## 1. Supported Audio Architectures & Codecs

TeamTalk 5 supports industry-standard VoIP audio codecs:
- **Opus**: High fidelity, low latency, modern standard for voice and music.
- **Speex**: Legacy low-bitrate speech codec.
- **No Audio**: Used for data-only or silent bots.

### Channel Audio Codecs
A bot transmitting voice or audio into a channel encodes audio matching the channel's configured codec. You can inspect a channel's audio codec settings via `channel.audiocodec`.

---

## 2. Media File Streaming (MP3, WAV, OGG)

The easiest and highest quality way to play sound effects, music, or recorded voice into a TeamTalk channel is using **Media File Streaming**.

### API Methods
- `startStreamingMediaFileToChannel(szMediaFilePath, lpVideoCodec: VideoCodec) -> bool`
- `stopStreamingMediaFileToChannel() -> bool`
- `getMediaFileInfo(szMediaFilePath) -> MediaFileInfo`

### Basic Example: Playing an MP3 / WAV into Channel
```python
from TeamTalk5 import TeamTalk, ttstr

class MusicBot(TeamTalk):
    def play_track(self, file_path: str):
        # Pass None for lpVideoCodec when streaming audio only
        success = self.startStreamingMediaFileToChannel(ttstr(file_path), None)
        if success:
            print(f"Streaming {file_path} into channel...")
        else:
            print("Failed to start media file streaming.")

    def stop_track(self):
        self.stopStreamingMediaFileToChannel()
        print("Media stream stopped.")
```

### Monitoring Playback State
When streaming media files, the engine triggers `onStreamMediaFile(mediafileinfo)`:
```python
def onStreamMediaFile(self, info: MediaFileInfo):
    print(f"Media duration: {info.nDurationMSec} ms, stream status: {info.uStatus}")
```

---

## 3. Microphone & Voice Transmission

To enable or disable continuous voice transmission:
```python
# Enable transmission (like holding down Push-to-Talk)
self.enableVoiceTransmission(True)

# Disable transmission (release Push-to-Talk)
self.enableVoiceTransmission(False)
```

### Voice Activation (VAD)
Instead of continuous transmission, enable Voice Activation Detection:
```python
self.enableVoiceActivation(True)
self.setVoiceActivationLevel(20)  # Sensitivity threshold (0 to 100)
self.setVoiceActivationStopDelay(500)  # Delay in ms before stopping transmission
```

---

## 4. Raw PCM Audio Injection (`AudioBlock`)

For custom audio synthesis (such as dynamic Text-to-Speech (TTS), procedural audio, or custom DSP filters), inject raw PCM audio blocks directly into the transmission stream using `insertAudioBlock`.

### `AudioFormat` Structure
```python
from TeamTalk5 import AudioFormat, AudioBlock, c_char

fmt = AudioFormat()
fmt.nSampleRate = 48000   # 48 kHz standard for Opus
fmt.nChannels = 1         # 1 for mono, 2 for stereo
```

### Generating & Inserting an AudioBlock
```python
def send_pcm_chunk(self, raw_pcm_bytes: bytes, sample_rate=48000, channels=1):
    block = AudioBlock()
    block.nSampleRate = sample_rate
    block.nChannels = channels
    block.nSamples = len(raw_pcm_bytes) // (2 * channels)  # 16-bit PCM = 2 bytes per sample
    
    # Copy raw PCM data into block.lpRawAudio
    # lpRawAudio is an array of signed 16-bit integers
    ctypes.memmove(block.lpRawAudio, raw_pcm_bytes, len(raw_pcm_bytes))
    
    self.insertAudioBlock(block)
```

---

## 5. Integrating Text-to-Speech (TTS)

You can easily generate TTS speech and stream it into a channel:

### Using `gTTS` or `pyttsx3` + Streaming
```python
import tempfile
import os
from gtts import gTTS

def speak_to_channel(bot: TeamTalk, text: str, lang="en"):
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name
    
    tts = gTTS(text=text, lang=lang)
    tts.save(tmp_path)
    
    # Stream the generated speech directly into the channel
    bot.startStreamingMediaFileToChannel(ttstr(tmp_path), None)
```

---

## 6. Sound Devices & Headless Server Best Practices

1. **Query Available Devices**:
   ```python
   devices = bot.getSoundDevices()
   for d in devices:
       print(f"ID {d.nDeviceID}: {ttstr(d.szDeviceName)} (Input: {d.nMaxInputChannels > 0})")
   ```
2. **Headless Linux VPS**:
   - For a bot that only streams files or interacts via text commands, you do **not** need to call `initSoundInputDevice()` or `initSoundOutputDevice()`.
   - The media streaming API (`startStreamingMediaFileToChannel`) encodes and transmits directly to the server's network stream without passing through local speaker hardware.
