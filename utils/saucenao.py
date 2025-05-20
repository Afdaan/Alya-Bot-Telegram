"""
SauceNAO API Handler for Alya Bot.

This module provides reverse image searching capabilities using SauceNAO API,
specifically targeted at anime, manga, and related artwork.
"""

import logging
import aiohttp
import re
import asyncio
import traceback
import random
from typing import Dict, List, Any, Optional, Tuple, Union
import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message
from config.settings import SAUCENAO_API_KEY

logger = logging.getLogger(__name__)

# Constants
MAX_RETRIES = 2
RETRY_DELAY = 2  # seconds
MAX_RESULTS = 8

class SauceNAOSearcher:
    """
    Handler for SauceNAO reverse image search API.
    
    This class manages communication with the SauceNAO API, handles
    error cases, and formats the results for Telegram presentation.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize SauceNAO searcher.
        
        Args:
            api_key: SauceNAO API key (defaults to settings)
        """
        self.api_key = api_key or SAUCENAO_API_KEY
        self.base_url = "https://saucenao.com/search.php"
        
    async def search_image(self, image_path: str) -> Dict[str, Any]:
        """
        Search for an image using SauceNAO API.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Dictionary of SauceNAO API response
            
        Raises:
            aiohttp.ClientError: On network issues
            ValueError: On API error responses
        """
        # Setup API parameters
        params = {
            'api_key': self.api_key,
            'output_type': 2,        # JSON output
            'numres': 8,             # More results for better filtering
            'dedupe': 1,             # Remove duplicates
            'db': 999                # All databases
        }
        
        # Send request with retry logic
        for retry in range(MAX_RETRIES + 1):
            try:
                async with aiohttp.ClientSession() as session:
                    with open(image_path, 'rb') as img_file:
                        # Create form data
                        form_data = aiohttp.FormData()
                        form_data.add_field('file', img_file, 
                                           filename='image.jpg',
                                           content_type='image/jpeg')
                        
                        # Add parameters to form data
                        for key, value in params.items():
                            form_data.add_field(key, str(value))
                        
                        # Send request
                        async with session.post(self.base_url, data=form_data) as response:
                            # Handle non-200 responses
                            if response.status != 200:
                                if retry < MAX_RETRIES:
                                    # Try again after delay
                                    await asyncio.sleep(RETRY_DELAY)
                                    continue
                                
                                # All retries failed
                                error_message = f"API returned status code {response.status}"
                                raise ValueError(error_message)
                            
                            # Parse JSON response
                            data = await response.json()
                            return data
                            
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                # Network errors - retry if possible
                if retry < MAX_RETRIES:
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                    
                # All retries failed
                raise
                
        # This shouldn't happen but just in case
        raise ValueError("Failed to make request to SauceNAO API after retries")
    
    def format_html_safe(self, text: str) -> str:
        """
        Convert text to safe HTML format for Telegram.
        
        Args:
            text: Text to format
            
        Returns:
            HTML-safe text
        """
        if not isinstance(text, str):
            text = str(text)
        
        # Replace HTML special chars
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        return text
        
    def create_result_message(self, results: List[Dict[str, Any]], 
                             header: Dict[str, Any], user_mention: str) -> Tuple[str, List[List[InlineKeyboardButton]]]:
        """
        Create formatted message and buttons from results.
        
        Args:
            results: SauceNAO result list
            header: SauceNAO response header
            user_mention: User's name for personalization
            
        Returns:
            Tuple of (formatted message text, keyboard button rows)
        """
        # Limit results to display
        max_results = min(MAX_RESULTS, len(results))
        display_results = results[:max_results]
        
        # Get first result for similarity-based intro
        first_result = display_results[0]
        similarity = float(first_result.get('header', {}).get('similarity', 0))
        
        # Format main message
        message_text = "<b>🔎 SOURCE ANALYSIS RESULTS 🔍</b>\n\n"
        
        # Add confidence description based on similarity
        if similarity < 50:
            message_text += f"❓ <b>Doubtful!</b> Only {similarity:.1f}% match. Alya will show {max_results} results.\n\n"
        else:
            message_text += f"✅ <b>Found!</b> {similarity:.1f}% match. Alya will show {max_results} results.\n\n"
        
        # Process each result to match the screenshot format
        for i, result in enumerate(display_results):
            result_sim = float(result.get('header', {}).get('similarity', 0))
            result_data = result.get('data', {})
            
            # Add result header with index and similarity
            message_text += f"⟨ <b>Result #{i+1}</b> • {result_sim:.1f}% ⟩\n"
            
            # Add creator/author info with emoji
            creator = None
            if 'member_name' in result_data:
                creator = result_data.get('member_name')
            elif 'author_name' in result_data:
                creator = result_data.get('author_name')
            elif 'creator' in result_data:
                creator = result_data.get('creator')
                
            if creator:
                creator = self.format_html_safe(creator)
                message_text += f"👤 <b>Creator:</b> {creator}\n"
            
            # Add source info with emoji
            if 'source' in result_data and result_data['source']:
                source = self.format_html_safe(str(result_data['source']))
                message_text += f"📚 <b>Source:</b> {source}\n"
            
            # Add separator between results
            message_text += "\n"
        
        # Add API status info
        short_remaining = header.get('short_remaining', 'N/A')
        long_remaining = header.get('long_remaining', 'N/A')
        message_text += f"📊 <b>API Status:</b> Short: {short_remaining}/30sec • Long: {long_remaining}/day\n"
        
        # Add warning for low similarity
        if similarity < 50:
            message_text += "\n⚠️ <b>Warning!</b> Low similarity. Alya is not responsible for accuracy."
        
        # Add flavorful ending matching screenshot style
        message_text += "\n\n<i>~Alya has provided the information. Not because {user} is special or anything~</i>".format(
            user=self.format_html_safe(user_mention))

        # Create URL buttons for results
        keyboard = self._create_url_buttons(display_results)
        
        # Add alternative search button - no need to duplicate Pixiv button
        keyboard.append([InlineKeyboardButton("🔄 Try with !search", callback_data="try_search")])
        
        return message_text, keyboard
        
    def _create_url_buttons(self, results: List[Dict[str, Any]]) -> List[List[InlineKeyboardButton]]:
        """
        Create URL buttons from results.
        
        Args:
            results: SauceNAO result list
            
        Returns:
            List of button rows
        """
        keyboard = []
        
        # Priority domains for better organization
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
        
        # Collect all URLs from all results
        unique_urls = set()
        priority_url_buttons = []
        other_url_buttons = []
        
        # Track domains we've already added to avoid duplicates
        added_domains = set()
        
        for result in results:
            result_data = result.get('data', {})
            if 'ext_urls' in result_data and result_data['ext_urls']:
                for url in result_data['ext_urls']:
                    if url in unique_urls:
                        continue
                        
                    unique_urls.add(url)
                    
                    # Extract domain and create appropriate button
                    try:
                        domain = re.search(r"^(?:https?:\/\/)?(?:[^@\n]+@)?(?:www\.)?([^:\/\n?]+)", url).group(1)
                        
                        # Check for priority domains
                        priority_match = False
                        for key, label in priority_domains.items():
                            if key in domain:
                                priority_url_buttons.append(InlineKeyboardButton(f"🔗 {label}", url=url))
                                priority_match = True
                                break
                                
                        # If not priority, add to other buttons
                        if not priority_match:
                            # Extract name from domain
                            domain_parts = domain.split('.')
                            if len(domain_parts) >= 2:
                                if domain_parts[-2] in ['co', 'com', 'net', 'org'] and len(domain_parts) >= 3:
                                    domain_name = domain_parts[-3].capitalize()
                                else:
                                    domain_name = domain_parts[-2].capitalize()
                            else:
                                domain_name = domain
                            
                            other_url_buttons.append(InlineKeyboardButton(f"🔗 {domain_name}", url=url))
                    except Exception:
                        other_url_buttons.append(InlineKeyboardButton("🔗 Source", url=url))
        
        # Add priority buttons first (in rows of two)
        for i in range(0, len(priority_url_buttons), 2):
            current_row = []
            
            # First button in row
            button = priority_url_buttons[i]
            # Extract domain from button text to check for duplicates
            domain_name = button.text.split(' ', 1)[1] if ' ' in button.text else 'Unknown'
            if domain_name not in added_domains:
                added_domains.add(domain_name)
                current_row.append(button)
                
            # Second button in row (if available)
            if i + 1 < len(priority_url_buttons):
                button = priority_url_buttons[i+1]
                domain_name = button.text.split(' ', 1)[1] if ' ' in button.text else 'Unknown'
                if domain_name not in added_domains:
                    added_domains.add(domain_name)
                    current_row.append(button)
                    
            # Only add row if it has buttons
            if current_row:
                keyboard.append(current_row)
        
        # Then add other buttons (in rows of two)
        for i in range(0, len(other_url_buttons), 2):
            current_row = []
            
            # First button in row
            button = other_url_buttons[i]
            domain_name = button.text.split(' ', 1)[1] if ' ' in button.text else 'Unknown'
            if domain_name not in added_domains:
                added_domains.add(domain_name)
                current_row.append(button)
                
            # Second button in row (if available)
            if i + 1 < len(other_url_buttons):
                button = other_url_buttons[i+1]
                domain_name = button.text.split(' ', 1)[1] if ' ' in button.text else 'Unknown'
                if domain_name not in added_domains:
                    added_domains.add(domain_name)
                    current_row.append(button)
                    
            # Only add row if it has buttons
            if current_row:
                keyboard.append(current_row)
                
        return keyboard
    
    def get_error_message(self, error_type: str, status_code: Optional[int] = None) -> str:
        """
        Get appropriate error message for different error conditions.
        
        Args:
            error_type: Type of error (network, rate_limit, api, general)
            status_code: Optional HTTP status code
            
        Returns:
            Formatted error message
        """
        if error_type == "network":
            messages = [
                "🌐 <b>Network Connection Issue</b>\n\n"
                "Alya couldn't connect to SauceNAO servers after multiple attempts.\n\n"
                "This could be due to:\n"
                "• SauceNAO service being down\n"
                "• Internet connectivity issues\n"
                "• Firewall blocking the connection\n\n"
                "Please try again later or use !search as an alternative."
            ]
        elif error_type == "rate_limit":
            messages = [
                "⚠️ <b>Rate Limit Reached</b>\n\n"
                "We've hit SauceNAO's rate limit.\n\n"
                "Please try again later or use !search as an alternative."
            ]
        elif error_type == "no_results":
            messages = [
                "Nyet. No results found. Алья не виновата, понятно? (Alya is not at fault, understand?)",
                "Нет результатов. Alya searched thoroughly. Result: Nothing.",
                "Hmph. Source not found. В следующий раз выбери изображение получше. (Choose a better image next time.)"
            ]
        else:
            # General error
            status_info = f" (Status: {status_code})" if status_code else ""
            messages = [
                f"Ошибка системы{status_info}. (System error.) SauceNAO failed. Not Alya's responsibility.",
                f"Search interrupted by technical error{status_info}. Hmph, technology is always imperfect.",
                f"неудача{status_info}. Alya cannot continue the search due to server issues. Try again later."
            ]
            
        # Select a random message
        message = random.choice(messages)
        
        # Add alternative suggestion
        if "!search" not in message:
            message += "\n\nTry using !search as an alternative."
            
        return message

# Create singleton instance
sauce_searcher = SauceNAOSearcher()

async def search_with_saucenao(message: Message, image_path: str) -> None:
    """
    Search image source using SauceNAO API and update message with results.
    
    Args:
        message: Telegram Message object to update with results
        image_path: Path to the image file to search
    """
    try:
        # Send intermediate status - use plain text without escaping
        await message.edit_text(
            "Sending image to SauceNAO for analysis...\n",
            parse_mode=None
        )
        
        # Get user information for personalization 
        user_mention = message.chat.first_name if hasattr(message.chat, 'first_name') else "Senpai"
        
        # Get search results
        try:
            data = await sauce_searcher.search_image(image_path)
        except aiohttp.ClientError:
            # Network errors
            error_message = sauce_searcher.get_error_message("network")
            await message.edit_text(error_message, parse_mode='HTML')
            return
        except ValueError as e:
            # API errors
            error_type = "general"
            status_code = None
            
            # Check for specific error types
            error_str = str(e).lower()
            if "429" in error_str or "rate" in error_str:
                error_type = "rate_limit"
            elif "status code" in error_str:
                # Extract status code
                status_match = re.search(r"status code (\d+)", error_str)
                if status_match:
                    status_code = int(status_match.group(1))
            
            # Get appropriate error message
            error_message = sauce_searcher.get_error_message(error_type, status_code)
            await message.edit_text(error_message, parse_mode='HTML')
            return
        
        # Check for results
        if not data or 'results' not in data or not data['results']:
            error_message = sauce_searcher.get_error_message("no_results")
            await message.edit_text(error_message, parse_mode='HTML')
            return
        
        # Format results
        message_text, keyboard = sauce_searcher.create_result_message(
            data['results'], 
            data.get('header', {}), 
            user_mention
        )
        
        # Send the formatted results - use HTML parse mode instead of Markdown for simpler formatting
        await message.edit_text(
            message_text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.error(f"SauceNAO error: {e}\n{traceback.format_exc()}")
        
        # Generic error handling - clean text without markdown
        try:
            error_message = sauce_searcher.get_error_message("general")
            await message.edit_text(error_message, parse_mode='HTML')
        except Exception as final_error:
            # Last resort fallback
            logger.error(f"Final error in sauce: {final_error}")
            await message.edit_text("Error searching for image source. Please try again later.")
