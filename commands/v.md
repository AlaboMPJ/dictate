---
description: Speak a prompt (local Whisper, nothing leaves the machine)
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/dictate:*)
---
The user dictated this prompt by voice. It went through Whisper, so a word may be misheard; read it for what they meant, and if a misheard word changes the meaning, say which reading you took.

!`${CLAUDE_PLUGIN_ROOT}/dictate`
