# Alya-chan Command Reference

## Basic Commands
- `/start` - Start Alya-chan and show menu
- `/help` - Show command help
- `/reset` - Clear chat history
- `/ping` - Check bot status
- `/lang` - Change default language

## Language Features
- **Default Languages**: English (en) or Indonesian (id)
- **Flexible Communication**: Alya can understand and respond in many languages
- **Language Switching**: Ask Alya to speak in any language (e.g., "Can you speak in Javanese?")
- **Change Default**: Use `/lang [code]` to change default language (en/id)

## Chat Commands
### Private Chat
- Send message directly to chat with Alya-chan

### Group Chat
- Use `!ai` prefix for all commands
- Example: `!ai Hello Alya-chan!`

## Analysis Commands
### Image/Document Analysis
- Send media with `!trace` caption
- Example: `!trace Analyze this image please`

### Reverse Image Search
- Send image with `!sauce` caption
- Choose between SauceNAO (anime) or Google Lens
- Example: `!sauce`

## Roasting Commands
### GitHub Roasts
```
!ai roast github <username>
!ai check github <username>
```

### Personal Roasts
```
!ai roast <@username> [keywords]
!ai toxic <@username>
```

Available roast keywords:
- wibu
- nolep
- jomblo
- etc.

## Developer Commands
Restricted to authorized developers:
- `/update` - Pull updates & restart
  - Manual update: Use command directly
  - Auto update: Will trigger automatically on repository changes
  - Restarts bot in TMUX session after update
  - Shows git pull output and restart status
- `/stats` - Show bot statistics
- `/debug` - Toggle debug mode
- `/shell` - Execute shell commands

## Search Commands
### Web Search
- `!search <query>` - Cari informasi di internet
- `!search -d <query>` - Cari informasi detail
- Example: `!search jadwal KRL lempuyangan jogja`

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
!search jadwal kereta jakarta bandung
```
