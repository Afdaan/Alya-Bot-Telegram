# Alya-chan Bot Commands 💕

This guide covers all available commands and features for Alya Bot. Commands are organized by category for easy reference.

## Table of Contents
- [Basic Commands](#basic-commands)
- [Chat & Conversation](#chat--conversation)
- [Search Commands](#search-commands)
- [Media Analysis](#media-analysis)
- [Roasting Commands](#roasting-commands)
- [Admin Commands](#admin-commands)
- [Usage Examples](#usage-examples)

---

## Basic Commands

### Core Bot Commands
| Command | Description | Usage |
|---------|-------------|--------|
| `/start` | Initialize bot and show welcome menu | `/start` |
| `/help` | Display help information and command list | `/help` |
| `/ping` | Check bot response time and status | `/ping` |
| `/reset` | Clear conversation history and start fresh | `/reset` |
| `/stats` | View your relationship statistics with Alya | `/stats` |

### Language & Settings
| Command | Description | Usage |
|---------|-------------|--------|
| `/lang` | Change default language (currently id/en) | `/lang id` or `/lang en` |

---

## Chat & Conversation

### Private Chat
- **Direct messaging**: Send any message directly to chat with Alya
- **Context awareness**: Alya remembers previous conversations
- **Follow-up questions**: Ask related questions without repeating context

### Group Chat
- **Command prefix**: Use `!ai` prefix for all commands
- **Reply to bot**: Reply to Alya's messages for direct interaction
- **Examples**:
  ```
  !ai Hello Alya-chan!
  !ai How are you today?
  ```

### Conversation Features

#### Context Awareness
Alya maintains conversation context across multiple messages:

```
You: What causes common cold?
Alya: *explains about cold causes*
You: Any prevention methods?
Alya: *provides prevention tips* (understands you're still talking about colds)
You: How long does recovery take?
Alya: *explains recovery time* (maintains context)
```

#### Personality Modes

1. **Normal Mode (Default)**
   - Tsundere responses with caring undertones
   - Russian expressions when emotional
   - Context-aware conversations
   - Relationship-based interactions

2. **Roast Mode**
   - Savage roasting with creative insults
   - Keyword-based targeted roasting
   - GitHub profile roasting
   - Playful toxic responses

#### Relationship System
Alya's personality evolves based on your interaction:
- **Stranger** (Level 0): Formal, cold, tsundere
- **Acquaintance** (Level 1): Slightly warmer, still defensive
- **Friend** (Level 2): Comfortable, more dere than tsundere
- **Close Friend** (Level 3): Very caring, open, still tsundere charm

---

## Search Commands

### Web Search
| Command | Description | Example |
|---------|-------------|---------|
| `/search <query>` | General web search | `/search latest AI technology` |
| `/search -p <name>` | Profile/social media search | `/search -p github afdaan` |
| `/search -n <topic>` | News search (latest) | `/search -n artificial intelligence` |
| `/search -i <description>` | Image search | `/search -i mount fuji sunrise` |

### Search Features

#### Profile Search
Find social media profiles across platforms:
```bash
/search -p github username      # GitHub profiles
/search -p instagram username   # Instagram accounts  
/search -p twitter username     # Twitter/X profiles
/search -p linkedin name        # LinkedIn profiles
```

**Supported platforms**: GitHub, Instagram, Twitter/X, LinkedIn, Facebook, TikTok, YouTube, Discord, Steam, MyAnimeList, osu!

#### News Search
Get latest news and articles:
```bash
/search -n technology trends    # Latest tech news
/search -n indonesia politics   # Indonesian political news
/search -n global economy      # Economic updates
```

#### Image Search
Find high-quality images:
```bash
/search -i anime wallpaper     # Anime wallpapers
/search -i nature photography  # Nature photos
/search -i logo design         # Logo designs
```

### Smart Search Features

#### Intent Detection
Bot automatically understands search intent:
- **Products**: `laptop gaming murah` → Product search
- **Locations**: `tempat wisata bandung` → Location search  
- **Definitions**: `apa itu machine learning` → Definition search
- **Schedules**: `jadwal kereta jakarta bandung` → Schedule search

#### Advanced Options
- **Fallback system**: Automatic retry with different strategies
- **Multiple results**: Up to 8 relevant results per search
- **Safe search**: Configurable content filtering
- **Global results**: Searches across entire web, not just regional

---

## Media Analysis

### Image Source Search
| Command | Description | Usage |
|---------|-------------|--------|
| `!sauce` | Find anime/manga source using SauceNAO | Reply to image with `!sauce` |
| `!sauce` | Search image source | Send image with `!sauce` caption |

#### SauceNAO Features
- **Anime/manga focus**: Best for anime, manga, and fan art
- **Similarity scoring**: Shows accuracy percentage
- **Multiple sources**: Displays various possible sources
- **Detailed info**: Title, artist, series information

### Image Analysis
| Command | Description | Usage |
|---------|-------------|--------|
| `!trace` | Analyze image content with AI | Reply to image with `!trace` |
| `!trace` | Analyze uploaded image | Send image with `!trace` caption |

#### Analysis Capabilities
- **Object detection**: Identify objects, people, animals
- **Scene description**: Describe image content and context
- **Text extraction**: Read text within images
- **Color analysis**: Dominant colors and composition
- **Style recognition**: Art style, photography type

---

## Roasting Commands

### Personal Roasting
| Command | Description | Example |
|---------|-------------|---------|
| `!roast @username` | Basic roasting | `!roast @someone` |
| `!roast @username wibu` | Keyword-based roast | `!roast @user weeb` |
| `!gitroast username` | GitHub profile roast | `!gitroast afdaan` |

### Available Keywords
Customize roasts with specific themes:
- `wibu/weeb` - Anime/manga enthusiast roasts
- `nolep/nolife` - Lifestyle roasts  
- `jomblo/single` - Relationship status roasts
- `gaming` - Gaming-related roasts
- `coding` - Programming/developer roasts

### GitHub Roasting
Special roasting mode for developers:
```bash
!gitroast username          # Roast based on GitHub profile
!gitroast username/repo     # Roast specific repository
```

**Analyzes**:
- Repository quality and naming
- Code activity and consistency  
- Profile completeness
- Project creativity
- Commit message quality

---

## Admin Commands

*These commands are restricted to authorized administrators only.*

### System Management
| Command | Description | Usage |
|---------|-------------|--------|
| `/statsall` | View comprehensive bot statistics | `/statsall` |
| `/spek` | Show system specifications and health | `/spek` |
| `/cleanup` | Clean up database and temporary files | `/cleanup` |

### User Management  
| Command | Description | Usage |
|---------|-------------|--------|
| `/addadmin <user_id>` | Grant admin privileges | `/addadmin 123456789` |
| `/removeadmin <user_id>` | Remove admin privileges | `/removeadmin 123456789` |
| `/broadcast <message>` | Send message to all users | `/broadcast Important update!` |

### Deployment & Updates
| Command | Description | Usage |
|---------|-------------|--------|
| `/update [branch]` | Pull updates and restart bot | `/update` or `/update dev` |
| `/status` | Check deployment status | `/status` |
| `/restart` | Restart bot service | `/restart` |

#### Update Command Features
- **Automatic branch detection**: Defaults to `main` branch
- **Multiple branch support**: Specify branch name
- **Git integration**: Shows commit log and changes
- **Safe restart**: Graceful bot restart process
- **Rollback support**: Can revert problematic updates

**Examples**:
```bash
/update              # Update from main branch
/update dev          # Update from dev branch  
/update stable       # Update from stable branch
```

---

## Usage Examples

### Basic Conversation
```bash
# Private chat - direct messaging
Hello Alya, how are you?

# Group chat - with prefix
!ai What's the weather like today?

# Follow-up question
What about tomorrow?
```

### Search Examples
```bash
# Web search
/search latest iPhone release date
/search recipe for chocolate cake

# Profile search  
/search -p github torvalds
/search -p instagram cristiano

# News search
/search -n climate change
/search -n cryptocurrency

# Image search
/search -i sunset over mountains
/search -i cute anime characters
```

### Media Analysis
```bash
# Find anime source (reply to image)
!sauce

# Analyze image content (reply to image)  
!trace

# Or send image with caption
[Upload image with caption: !sauce]
[Upload image with caption: !trace What's in this image?]
```

### Roasting Examples
```bash
# Basic roast
!roast @username

# Themed roast
!roast @user weeb
!roast @someone nolife

# GitHub roast
!gitroast afdaan
!gitroast facebook/react
```

### Admin Examples
```bash
# Check bot stats
/statsall

# System information
/spek

# Update bot
/update dev

# Broadcast message
/broadcast Bot will be down for maintenance in 10 minutes
```

---

## Tips & Best Practices

### For Users
1. **Be specific** in search queries for better results
2. **Use context** - ask follow-up questions naturally
3. **Try different keywords** if roasts aren't hitting right
4. **Check image quality** for better SauceNAO results

### For Admins  
1. **Monitor stats** regularly with `/statsall`
2. **Test updates** on dev branch before main
3. **Schedule maintenance** during low-activity hours
4. **Keep backups** before major updates

### Search Optimization
1. **Use natural language** - bot understands context
2. **Be specific** for profile searches (include platform)
3. **Try multiple approaches** if first search doesn't work
4. **Use quotation marks** for exact phrase matching

---

## Troubleshooting

### Common Issues

**Bot not responding in groups?**
- Use `!ai` prefix or reply to bot messages
- Check if bot has proper permissions

**Search not working?**
- API keys might be rate limited (automatic rotation will handle this)
- Try different search terms or flags

**SauceNAO not finding sources?**
- Image might not be anime/manga related
- Try higher quality images
- Some sources might not be in SauceNAO database

**Roasts too mild?**
- Try specific keywords like `weeb`, `nolife`
- GitHub roasts work better with active profiles

### Getting Help

1. Use `/help` command for quick reference
2. Check this documentation for detailed usage
3. Contact administrators if persistent issues
4. Report bugs via GitHub issues

---

*Alya-chan is always ready to help! Don't be shy to ask questions or try new commands~ 💕*