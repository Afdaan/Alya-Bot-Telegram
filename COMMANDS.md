# Alya-chan Command Reference

## Basic Commands
- `/start` - Start Alya-chan and show menu
- `/help` - Show command help
- `/mode` - Change chat/image mode
- `/reset` - Clear chat history
- `/ping` - Check bot status

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
- `/stats` - Show bot statistics
- `/debug` - Toggle debug mode
- `/shell` - Execute shell commands
- `/logs` - View error logs

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
```
