# 🧹 Refactor YAML Structure - Alya Bot Project

## Objective:
You are helping Afdaan refactor and simplify a complex YAML folder structure used in a Telegram AI bot project. The goal is to:
- Flatten unnecessary nested folders
- Merge similar YAML files into consolidated ones
- Use top-level keys inside files instead of multiple small files
- Improve readability and reduce overhead in loading logic

---

## Current Structure (Problem):
config/
├── fallbacks/roasts.yaml
├── moods/persona/roast.yaml
├── personas/alya.yaml, toxic.yaml, waifu.yaml
├── prompts/roast/github.yaml, personal.yaml
├── prompts/templates/chat.yaml, memory.yaml
├── responses/roasts/general.yaml, github.yaml
├── responses/templates/errors.yaml, roleplay.yaml, memory.yaml, etc

This structure is too fragmented. Many YAMLs only contain a few lines and can be combined using keys.

---

## Target Refactored Structure:

config/
├── personas/
│   ├── alya.yaml
│   ├── toxic.yaml
│   └── waifu.yaml
│
├── moods.yaml
├── roasts.yaml
├── prompts/
│   ├── chat.yaml
│   ├── memory.yaml
│   ├── roast.yaml
│   └── templates.yaml
│
├── responses/
│   ├── general.yaml
│   ├── roleplay.yaml
│   ├── errors.yaml
│   └── fallbacks.yaml

---

## Example: Merge Files

### Before (`prompts/roast/github.yaml`)
```yaml
prompt: |
  Roast target GitHub user {username}...
