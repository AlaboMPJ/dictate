# dictate

Speak a prompt to Claude Code. Type `/dictate:v`, talk, stop talking, and what you said arrives as your prompt.

Recording and transcription happen on your machine: Whisper runs locally through faster-whisper, or on a Whisper server you name. No audio goes anywhere else.

## What it does

- Records your microphone through ffmpeg and stops by itself after about 2.5 seconds of quiet, measured against your own room's noise rather than a fixed level, so quiet microphones work.
- Writes every take to disk as it records. A crash or a killed process never loses what you said; `dictate --last` transcribes the newest take.
- Appends every raw transcript to a log, never a cleaned-up version.
- On Windows and WSL, shows a small window with the live waveform: click or Enter to finish, Esc to cancel. Elsewhere it beeps in the terminal.
- Takes a vocabulary file, so Whisper spells your names and jargon right.

## Install

You need Python 3.9+, ffmpeg on your PATH, and faster-whisper:

```
pip install faster-whisper numpy
```

Then, in Claude Code (2.1.275 or later):

```
/plugin install dictate --marketplace AlaboMPJ/dictate
```

Type `/dictate:v` and speak. The plugin runs its own copy of the script, so nothing needs to go on your PATH.

Without the plugin system, install by hand:

```
git clone https://github.com/AlaboMPJ/dictate
ln -s "$PWD/dictate/dictate" ~/.local/bin/dictate
mkdir -p ~/.claude/commands && sed 's#${CLAUDE_PLUGIN_ROOT}/dictate#dictate#g' dictate/commands/v.md > ~/.claude/commands/v.md
```

which gives you `/v`.

On WSL, recording goes through the Windows ffmpeg (`ffmpeg.exe` on the Windows PATH), because the microphone belongs to Windows. The waveform window needs Windows Python with Pillow (`pip install pillow` in Windows).

## Use

```
dictate                 record, stop on quiet, print the transcript
dictate --mics          list microphones (the one in use is starred)
dictate --mic "NAME"    use a microphone for this take
dictate --file x.wav    transcribe a file
dictate --last          transcribe the newest saved take
```

Save a default microphone with `echo "NAME" > ~/.config/dictate/mic`.

## Settings

| setting | default | what it does |
|---|---|---|
| `DICTATE_MODEL` | `small` | faster-whisper model: tiny, base, small, medium, large-v3. Larger is more accurate and slower. |
| `DICTATE_WHISPER_URL` | unset | use a Whisper server instead; it must accept `POST {url}/api/v1/whisper/transcribe` with `{"audio": base64 wav, "initial_prompt": ...}` and return `{"text": ...}` |
| `~/.config/dictate/vocab.txt` | none | words Whisper should expect, passed as its prompt |
| `DICTATE_HOME` | `~/.local/share/dictate` | where takes and `log.jsonl` go |
| `DICTATE_NOGUI` | unset | set to skip the window |

If a GPU driver is present but its CUDA libraries are not, faster-whisper's GPU choice fails; dictate falls back to the CPU and says so.

## Tested

Daily on Windows 11 with WSL2, a USB microphone and an audio interface; transcription through both routes (local faster-whisper on the CPU, and a Whisper server). The macOS (avfoundation) and Linux (PulseAudio) recording paths are written but untested; reports welcome.

## Licence

MIT. faster-whisper and the Whisper weights it downloads are MIT licensed too.
