"""
SauceNAO API Handler for Alya Telegram Bot.

This module provides reverse image searching capabilities using SauceNAO API,
specifically targeted at anime, manga, and related artwork.
"""

import logging
import aiohttp
import re
import asyncio  # Tambahkan import asyncio yang hilang
from typing import Dict, List, Any, Optional
import traceback
import random

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config.settings import SAUCENAO_API_KEY

logger = logging.getLogger(__name__)

def escape_markdown_v2(text: str) -> str:
    """Escape special characters for Markdown V2."""
    if not isinstance(text, str):
        text = str(text)
    # Escape backslash first
    text = text.replace('\\', '\\\\')
    # Escape all special characters (including dot) for MarkdownV2
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        # Avoid double escaping
        text = re.sub(rf'(?<!\\){re.escape(char)}', f'\\{char}', text)
    return text

# Tambahkan fungsi HTML formatter untuk mengganti escape_markdown_v2
def format_html_safe(text):
    """Convert text to safe HTML format for Telegram."""
    if not isinstance(text, str):
        text = str(text)
    
    # Replace HTML special chars
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    return text

async def search_with_saucenao(message, image_path):
    """
    Search image source using SauceNAO API directly.
    
    Args:
        message: Telegram Message object to update with results
        image_path: Path to the image file to search
    """
    try:
        # Define retry settings
        max_retries = 2
        retry_delay = 2  # seconds between retries
        
        # Setup API parameters for comprehensive search
        params = {
            'api_key': SAUCENAO_API_KEY,    # SauceNAO API key
            'output_type': 2,               # JSON output
            'numres': 8,                    # Increased for more results
            'dedupe': 1,                    # Remove duplicates
            'db': 999                       # All databases
        }
        
        for retry_count in range(max_retries + 1):  # +1 for initial attempt
            try:
                # Send request with image file
                async with aiohttp.ClientSession() as session:
                    await message.edit_text("Sending request to SauceNAO... ожидание (waiting).")
                    
                    with open(image_path, 'rb') as img_file:
                        # Create form data with image
                        form_data = aiohttp.FormData()
                        form_data.add_field('file', img_file, 
                                           filename='image.jpg',
                                           content_type='image/jpeg')
                        
                        # Add all parameters to form data
                        for key, value in params.items():
                            form_data.add_field(key, str(value))
                        
                        # Send POST request
                        async with session.post('https://saucenao.com/search.php', data=form_data) as response:
                            # Detailed error handling based on status code
                            if response.status != 200:
                                # If not the final retry, try again
                                if retry_count < max_retries:
                                    retry_message = f"SauceNAO API returned status {response.status}, retrying... ({retry_count+1}/{max_retries})"
                                    await message.edit_text(retry_message)
                                    await asyncio.sleep(retry_delay)
                                    continue
                                    
                                # Provide specific error messages based on status
                                if response.status == 502:
                                    await message.edit_text(
                                        "📶 *SauceNAO Server Connection Issue*\n\n"
                                        "SauceNAO servers are currently experiencing technical difficulties (502 Bad Gateway).\n\n"
                                        "This is a temporary server issue on SauceNAO's side. Please try:\n"
                                        "• Wait a few minutes and try again\n"
                                        "• Try using !search as an alternative\n"
                                        "• Try again during off-peak hours",
                                        parse_mode='Markdown'
                                    )
                                elif response.status == 429:
                                    await message.edit_text(
                                        "⚠️ *Rate Limit Reached*\n\n"
                                        "We've hit SauceNAO's rate limit (429 Too Many Requests).\n\n"
                                        "Please try again later or use !search as an alternative.",
                                        parse_mode='Markdown'
                                    )
                                else:
                                    await message.edit_text(
                                        f"Gomennasai! API SauceNAO error with status {response.status}... 🥺\n"
                                        "Try again later or use !search as an alternative."
                                    )
                                return
                            
                            # Parse JSON response
                            data = await response.json()
                    
                # Successfully got response, break out of retry loop
                break
                    
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                # Network-related errors
                if retry_count < max_retries:
                    # Log the error and retry
                    logger.warning(f"Network error with SauceNAO, retrying ({retry_count+1}/{max_retries}): {e}")
                    await message.edit_text(f"Network issue connecting to SauceNAO, retrying... ({retry_count+1}/{max_retries})")
                    await asyncio.sleep(retry_delay)
                    continue
                
                # If all retries failed
                logger.error(f"Failed to connect to SauceNAO after {max_retries} retries: {e}")
                await message.edit_text(
                    "🌐 *Network Connection Issue*\n\n"
                    "Alya couldn't connect to SauceNAO servers after multiple attempts.\n\n"
                    "This could be due to:\n"
                    "• SauceNAO service being down\n"
                    "• Internet connectivity issues\n"
                    "• Firewall blocking the connection\n\n"
                    "Please try again later or use !search as an alternative.",
                    parse_mode='Markdown'
                )
                return
            except Exception as e:
                # Other exceptions
                logger.error(f"Error connecting to SauceNAO: {e}\n{traceback.format_exc()}")
                await message.edit_text(
                    f"Unexpected error with SauceNAO API: {str(e)[:100]}...\n"
                    "Try again later or use !search as an alternative."
                )
                return
                
        # Process API response for no results
        if not data or 'results' not in data or not data['results']:
            no_results = [
                "Nyet. No results found. Алья не виновата, понятно? (Alya is not at fault, understand?)",
                "Нет результатов. Alya searched thoroughly. Result: Nothing.",
                "Hmph. Source not found. В следующий раз выбери изображение получше. (Choose a better image next time.)"
            ]
            await message.edit_text(f"{random.choice(no_results)}\n\nTry using !search as an alternative.")
            return
        
        # Get user information
        try:
            user_mention = message.chat.first_name if hasattr(message.chat, 'first_name') else "Senpai"
        except:
            user_mention = "Senpai"
        
        # Get all results and limits info
        results = data['results']
        header = data.get('header', {})
        
        # Format limits info
        short_remaining = header.get('short_remaining', 'N/A')
        long_remaining = header.get('long_remaining', 'N/A')
        
        # --- DETERMINE RESULTS TO DISPLAY ---
        # Maximum results to show - increased from 3 to 4 for more comprehensive results
        max_results = min(4, len(results))
        display_results = results[:max_results]
        
        # Get first result for initial similarity-based intro
        first_result = display_results[0]
        similarity = float(first_result.get('header', {}).get('similarity', 0))
        
        # Format message dengan HTML yang lebih baik
        message_text = "<b>🔎 SOURCE ANALYSIS RESULTS 🔍</b>\n\n"
        
        # Intro berdasarkan similarity dengan format yang lebih baik
        if similarity >= 80:
            message_text += f"<b>✅ Found!</b> <i>{similarity:.1f}%</i> accurate. Alya found {max_results} results.\n\n"
        elif similarity >= 50:
            message_text += f"<b>🤔 Perhaps!</b> <i>{similarity:.1f}%</i> similar. Alya found {max_results} possible matches.\n\n"
        else:
            message_text += f"<b>❓ Doubtful!</b> Only <i>{similarity:.1f}%</i> match. Alya will show {max_results} results.\n\n"
        
        # Loop untuk menampilkan hasil dengan formatting yang lebih baik
        for i, result in enumerate(display_results):
            result_sim = float(result.get('header', {}).get('similarity', 0))
            result_data = result.get('data', {})
            
            # Add result header dengan styling yang lebih rapi
            message_text += f"<b>⟨ Result #{i+1} • {result_sim:.1f}% ⟩</b>\n"
            
            # Add title if available
            title = result_data.get('title', 'Unknown')
            if title and title != "Unknown":
                safe_title = format_html_safe(title)
                message_text += f"📄 <b>Title:</b> {safe_title}\n"
            
            # Add author if available
            author = None
            if 'member_name' in result_data:
                author = format_html_safe(result_data.get('member_name', ''))
            elif 'author_name' in result_data:
                author = format_html_safe(result_data.get('author_name', ''))
            elif 'creator' in result_data:
                author = format_html_safe(result_data.get('creator', ''))
                
            if author:
                message_text += f"👤 <b>Creator:</b> {author}\n"
            
            # Add source info
            if 'source' in result_data and result_data['source']:
                source = format_html_safe(str(result_data['source']))
                message_text += f"📚 <b>Source:</b> {source}\n"
                
            # Add other relevant info
            for field, emoji, label in [
                ('part', '📖', 'Chapter/Part'), 
                ('year', '📅', 'Year'),
                ('material', '🎭', 'From'),
                ('est_time', '⏰', 'Est. Time'),
                ('characters', '👪', 'Characters'),
                ('artist', '🎨', 'Artist')
            ]:
                if field in result_data and result_data[field]:
                    value = format_html_safe(str(result_data[field]))
                    message_text += f"{emoji} <b>{label}:</b> {value}\n"
            
            # Add separator between results - membuat lebih rapi
            message_text += "\n"
        
        # Add API status info dengan format yang lebih baik
        message_text += f"📊 <b>API Status:</b> Short: {short_remaining}/30sec • Long: {long_remaining}/day\n"
        
        # Warning for low similarity
        if similarity < 50:
            message_text += "\n⚠️ <b>Warning!</b> Low similarity. Alya is not responsible for accuracy."
        
        # Add ending
        endings = [
            "~Alya has provided the information. Not because {user_mention} is special or anything~",
            "к сведению... this information may not be 100% accurate.",
            "(That's all) Alya has completed the analysis. No thanks necessary.",
            "Don't forget, efficiency is priority. Just like this search.",
            "Alya always completes her work. Whether you appreciate it or not."
        ]
        ending = random.choice(endings).replace("{user_mention}", format_html_safe(user_mention))
        message_text += f"\n\n<i>{ending}</i>"

        # --- IMPROVED URL BUTTON CREATION ---
        # Prioritize popular sites and show more sources
        keyboard = []
        
        # Collect all URLs from all results
        all_urls = []
        for result in display_results:
            result_data = result.get('data', {})
            if 'ext_urls' in result_data and result_data['ext_urls']:
                all_urls.extend(result_data['ext_urls'])
        
        # Define priority domains for better organization
        priority_domains = {
            'pixiv': 'Pixiv', 
            'twitter': 'Twitter',
            'deviantart': 'DeviantArt',
            'danbooru': 'Danbooru', 
            'gelbooru': 'Gelbooru',
            'sankaku': 'Sankaku',
            'yande': 'Yande.re',
            'konachan': 'Konachan',
            'anime-pictures': 'Anime-Pictures',
            'zerochan': 'Zerochan',
            'nijie': 'Nijie',
            'pawoo': 'Pawoo',
            'seiga': 'Seiga',
            'fanbox': 'Fanbox',
            'artstation': 'ArtStation'
        }
        
        # Create buttons for unique URLs, prioritizing popular sites
        unique_urls = []
        priority_url_buttons = []
        other_url_buttons = []
        
        for url in all_urls:
            if url not in unique_urls:
                unique_urls.append(url)
                
                # Create button with domain name
                try:
                    domain = re.search(r"^(?:https?:\/\/)?(?:[^@\n]+@)?(?:www\.)?([^:\/\n?]+)", url).group(1)
                    
                    # Check if this is a priority domain
                    priority_match = False
                    for key, label in priority_domains.items():
                        if key in domain:
                            priority_url_buttons.append(InlineKeyboardButton(f"🔗 {label}", url=url))
                            priority_match = True
                            break
                            
                    # If not a priority domain, add to other buttons
                    if not priority_match:
                        # Extract a meaningful name from domain
                        domain_parts = domain.split('.')
                        if len(domain_parts) >= 2:
                            if domain_parts[-2] in ['co', 'com', 'net', 'org'] and len(domain_parts) >= 3:
                                domain_name = domain_parts[-3].capitalize()
                            else:
                                domain_name = domain_parts[-2].capitalize()
                        else:
                            domain_name = domain
                        
                        other_url_buttons.append(InlineKeyboardButton(f"🔗 {domain_name}", url=url))
                except:
                    other_url_buttons.append(InlineKeyboardButton(f"🔗 Source", url=url))
        
        # First add priority buttons
        if priority_url_buttons:
            # Group into rows of two
            for i in range(0, len(priority_url_buttons), 2):
                if i + 1 < len(priority_url_buttons):
                    keyboard.append([priority_url_buttons[i], priority_url_buttons[i+1]])
                else:
                    keyboard.append([priority_url_buttons[i]])
        
        # Then add other buttons
        if other_url_buttons:
            # Group into rows of two
            for i in range(0, len(other_url_buttons), 2):
                if i + 1 < len(other_url_buttons):
                    keyboard.append([other_url_buttons[i], other_url_buttons[i+1]])
                else:
                    keyboard.append([other_url_buttons[i]])
        
        # Tambahkan tombol untuk mencari dengan !search sebagai alternatif
        keyboard.append([InlineKeyboardButton("🔄 Try with !search", callback_data="try_search")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Semua bagian message_text sudah di-escape per field, tapi gabungan string bisa saja masih ada karakter spesial
        # Solusi: Escape seluruh message_text sebelum dikirim ke Telegram

        # --- setelah message_text selesai dibangun ---
        await message.edit_text(
            message_text,
            parse_mode='HTML',
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.error(f"SauceNAO error: {e}\n{traceback.format_exc()}")
        
        error_responses = [
            "Ошибка системы. (System error.) SauceNAO failed. Not Alya's responsibility.",
            "Search interrupted by technical error. Hmph, technology is always imperfect.",
            "неудача. Alya cannot continue the search due to server issues. Try again later."
        ]
        
        await message.edit_text(
            f"{random.choice(error_responses)}\n\nUse !search as an alternative."
        )
