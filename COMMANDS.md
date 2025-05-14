# Alya-chan Bot Commands 💕

## Chat Commands

- `!ai <message>` - Chat with Alya-chan in her kawaii tsundere mode
- `!roast <@username> [keywords]` - Get brutally roasted by Alya in toxic mode
- `!search <query>` - Search the web with Alya's help
- `!sauce <image>` - Find anime/image source
- `!trace <image>` - Analyze image contents

## New Expression Features

Alya now uses Russian expressions in certain situations:
- When flustered: "п-привет!"
- When agreeing reluctantly: "д-да..."
- When thanking: "спасибо"
- When being tsundere: "хорошо"

## Personality Modes

1. **Normal Mode (Default)**
   - Tsundere responses with Russian phrases
   - Mix of professional and cute reactions
   - Context-aware conversations

2. **Toxic Mode (!roast)**
   - Super savage roasts with creative insults
   - Specialized GitHub roasts for developers
   - Keyword-based targeted roasting

## Basic Commands
- `/start` - Start Alya-chan and show menu
- `/help` - Show command help
- `/reset` - Clear chat history
- `/ping` - Check bot status
- `/lang` - Change default language

## Smart Conversation Features
- **Context Awareness**: Alya remembers previous conversation
- **Follow-up Questions**: Ask questions without repeating context
- **Example Usage**:
  ```
  You: What causes eye infection?
  Alya: *explains about eye infections*
  You: Any recommended treatments?
  Alya: *provides treatments for eye infections* (understands you're still talking about eye infections)
  You: How long does recovery take?
  Alya: *explains recovery time* (still maintains context of eye infections)
  ```
- Works great for complex topics requiring multiple questions
- Remembers information from previous exchanges

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
- `/update [branch]` - Pull updates & restart
  - Manual update: `/update main` or `/update dev`
  - Default branch: `main` if no branch specified
  - Examples:
    ```
    /update         # Updates from main branch
    /update dev     # Updates from dev branch
    /update stable  # Updates from stable branch
    ```
  - Shows git pull output and restart status
  - Automatically restarts bot after successful update
- `/stats` - Show bot statistics
- `/debug` - Toggle debug mode
- `/shell` - Execute shell commands

## Search Commands (ENHANCED!)
### Web Search
- `!search <query>` - Search for information on the internet using natural language
- `!search -d <query>` - Detailed search with more results
- Example: `!search jadwal kereta api dari Jakarta ke Bandung besok`

### Social Media Profile Search (NEW!)
- `!search profile github username Afdaan` - Find GitHub profile
- `!search akun instagram dari user selena_gomez` - Find Instagram profile
- `!search carikan profil twitter elon musk` - Find Twitter profile
- Note: Works with GitHub, Instagram, Twitter, Facebook, TikTok, LinkedIn, YouTube

### Image Search Modes (NEW!)
- **With Reply to Image**:
  - `!search describe` - Analyze image content with AI
  - `!search source` - Find image source/similar images
  - Or simply use `!search` when replying to an image to see options

### Smart Search Intent Detection (NEW!)
Bot automatically understands various search intents:
- Images: `!search gambar gunung bromo sunrise`
- Definitions: `!search apa itu machine learning`
- Locations: `!search dimana lokasi monas jakarta`
- Schedules: `!search jadwal buka mall grand indonesia`
- News: `!search berita terbaru tentang teknologi ai`

## Enhanced Search Features (UPDATED!)

### Global Web Search
- `!search <query>` - Cari informasi di seluruh web dengan bahasa natural
- `!search -d <query>` - Pencarian detail dengan lebih banyak hasil
- Contoh: `!search jadwal kereta api dari Jakarta ke Bandung besok`

### Image Search with Fallbacks
- Pencarian gambar kini lebih andal dengan sistem fallback otomatis
- Jika gambar gagal dimuat, akan muncul link preview yang dapat diklik
- Hasil gambar tetap ditampilkan meski sumber asli bermasalah

### Advanced Search Intent Detection
Bot secara otomatis mengenali berbagai jenis pencarian:
- **Produk**: `!search beli laptop gaming murah`
- **Lowongan**: `!search lowongan kerja IT di Jakarta`
- **Lokasi Lokal**: `!search tempat wisata di sekitar Bandung`
- **Ulasan**: `!search review smartphone terbaru 2023`

## Enhanced Search Features

### Global Web Search
- `!search <query>` - Search for information across the entire web using natural language
- `!search -d <query>` - Detailed search with more comprehensive results
- Example: `!search train schedule from Jakarta to Bandung tomorrow`

### Image Search with Automatic Fallbacks
- Image search is now more reliable with automatic fallback system
- If images fail to load, clickable preview links will appear
- Results are displayed even if the original source has issues
- Example: `!search pictures of Mount Bromo sunrise`

### Social Media Profile Search
- `!search profile github username Afdaan` - Find GitHub profile
- `!search instagram account selena_gomez` - Find Instagram profile
- `!search twitter profile elon musk` - Find Twitter profile
- Note: Works with GitHub, Instagram, Twitter, Facebook, TikTok, LinkedIn, YouTube

### Smart Intent Detection
The bot automatically recognizes various search intents:
- **Products**: `!search buy gaming laptop cheap`
- **Jobs**: `!search IT job vacancies in Jakarta`
- **Local Places**: `!search tourist spots around Bandung`
- **Reviews**: `!search reviews of latest 2023 smartphones`
- **Travel**: `!search route to Borobudur temple`
- **Weather**: `!search weather in Bali today`
- **News**: `!search latest news about AI technology`

### Image Search Modes
- **With Reply to Image**:
  - `!search describe` - Analyze image content with AI
  - `!search source` - Find image source/similar images
  - Or simply use `!search` when replying to an image to see options

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
