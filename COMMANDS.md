# Alya-chan Bot Commands 💕

## Basic Commands

- `/start` — Start Alya-chan and show menu
- `/help` — Show command help
- `/persona [type]` — Change Alya's personality (tsundere, waifu, informative)
- `/stats` — Show bot statistics
- `/reset` — Clear chat history/context
- `/ping` — Check bot status
- `/lang [code]` — Change default language (en/id)
- `/nickname <name>` — Set your nickname for Alya to use

## Conversation & Memory

- `/remember <fact>` — Make Alya remember something about you
- `/recall [topic]` — Ask Alya to recall information from memory

## Chat Commands

- `!ai <message>` — Chat with Alya-chan in tsundere mode (group: use `!ai`, private: just chat)
- `!roast <@username> [keywords]` — Get roasted by Alya (toxic mode)
- `!ai roast github <username>` — GitHub-specific roast
- `!ai roast <@username> [keywords]` — Personal roast (keywords: wibu, nolep, jomblo, dll)
- `!ai toxic <@username>` — Extra toxic roast

## Search & Utility

- `!search <query>` — Web search (natural language)
- `!search -d <query>` — Detailed search
- `!search profile github username Afdaan` — Find GitHub profile
- `!search akun instagram dari user selena_gomez` — Find Instagram profile
- `!search carikan profil twitter elon musk` — Find Twitter profile
- `!search describe` — Analyze image content (reply to image)
- `!search source` — Find image source (reply to image)
- `/ai <prompt>` — Direct AI query (informative mode)
- `/define <term>` — Get definition of a term

## Media Commands

- `/trace` — Analyze an image (reply to image)
- `/sauce` — Find the source of an image (reply to image)
- `/ocr` — Extract text from an image (reply to image)
- `!trace <image>` — Analyze image contents (group)
- `!sauce <image>` — Find anime/image source (group)

## Admin/Developer Commands

- `/update [branch]` — Pull updates & restart bot (default: main)
- `/debug` — Toggle debug mode
- `/shell` — Execute shell commands
- `/migrate` — Run database migrations
- `/backup` — Create a backup of the database

## Personality Modes

- **Normal Mode** — Tsundere responses, Russian phrases, context-aware
- **Toxic Mode** — Savage roasts, creative insults, GitHub roasts
- **Informative Mode** — Factual, helpful, less tsundere

## New Expression Features

Alya now uses Russian expressions in certain situations:
- When flustered: "п-привет!"
- When agreeing reluctantly: "д-да..."
- When thanking: "спасибо"
- When being tsundere: "хорошо"

## Smart Conversation Features

- **Context Awareness** — Alya remembers previous conversation
- **Follow-up Questions** — No need to repeat context
- **Memory Recall** — Alya can remember facts about you

## Language Features

- **Default Languages**: English (en) or Indonesian (id)
- **Flexible Communication**: Alya can understand/respond in many languages
- **Change Default**: `/lang [code]`

## Usage Examples

```bash
# Regular chat
!ai How are you Alya-chan?

# Image analysis
!trace What's in this image?

# Find anime source
!sauce

# Roasting
!ai roast github afdaan
!ai roast @someone wibu nolep

# Search
!search train schedule jakarta bandung
!search pictures of Mount Bromo
!search profile instagram arianagrande
```

---

> **Note:**  
> - Use `/` prefix in private chat, `!` prefix in group chat.  
> - Most commands also work via natural conversation thanks to intent detection.
> - For media/image commands, reply to the image with the command or send image with caption.
