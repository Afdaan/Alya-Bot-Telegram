"""
SauceNAO API Handler for Alya Bot.

This module provides reverse image searching capabilities using SauceNAO API,
specifically targeted at anime, manga, and related artwork.
It is responsible for fetching and processing data from the API.
The presentation logic is handled separately in the handlers.
"""

import logging
import aiohttp
import asyncio
import traceback
from typing import Dict, List, Any, Optional

from config.settings import SAUCENAO_API_KEY

logger = logging.getLogger(__name__)

# Constants
MAX_RETRIES = 2
RETRY_DELAY = 2  # seconds
DEFAULT_MIN_SIMILARITY = 60.0
MAX_RESULTS = 8


class SauceNAOError(Exception):
    """Custom exception for SauceNAO errors."""
    pass


class SauceNAOSearcher:
    """
    Handler for SauceNAO reverse image search API.

    This class manages communication with the SauceNAO API, handles
    error cases, and processes the results into a structured format.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize SauceNAO searcher.

        Args:
            api_key: SauceNAO API key (defaults to one from settings).
        """
        self.api_key = api_key or SAUCENAO_API_KEY
        if not self.api_key:
            raise ValueError("SauceNAO API key is not configured.")
        self.base_url = "https://saucenao.com/search.php"

    async def search(self, image_path: str) -> Dict[str, Any]:
        """
        Search for an image using the SauceNAO API with retry logic.

        Args:
            image_path: Path to the image file.

        Returns:
            A dictionary containing the processed SauceNAO API response.

        Raises:
            SauceNAOError: On network issues or API error responses.
        """
        params = {
            'api_key': self.api_key,
            'output_type': 2,  # JSON output
            'numres': 16,      # Request more to allow for better filtering
            'db': 999,         # Search all databases
            'hide': 0,         # Show low-similarity results from API
        }

        for attempt in range(MAX_RETRIES + 1):
            try:
                async with aiohttp.ClientSession() as session:
                    with open(image_path, 'rb') as img_file:
                        form_data = aiohttp.FormData()
                        form_data.add_field(
                            'file', img_file,
                            filename='image.jpg',
                            content_type='image/jpeg'
                        )
                        for key, value in params.items():
                            form_data.add_field(key, str(value))

                        async with session.post(self.base_url, data=form_data, timeout=30) as response:
                            if response.status == 200:
                                data = await response.json()
                                return self._process_results(data)
                            
                            # Handle non-200 responses
                            error_text = await response.text()
                            logger.error(
                                f"SauceNAO API error. Status: {response.status}, "
                                f"Response: {error_text}"
                            )
                            if response.status == 429:
                                raise SauceNAOError("Rate limit reached.")
                            
                            # For other errors, retry if possible
                            if attempt >= MAX_RETRIES:
                                raise SauceNAOError(
                                    f"API request failed after multiple retries with "
                                    f"status code {response.status}."
                                )

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.error(f"SauceNAO network error on attempt {attempt + 1}: {e}")
                if attempt >= MAX_RETRIES:
                    raise SauceNAOError(f"Network error: {e}") from e
            
            except Exception as e:
                logger.error(f"An unexpected error occurred during SauceNAO search: {e}\n{traceback.format_exc()}")
                raise SauceNAOError(f"An unexpected error occurred: {e}") from e

            await asyncio.sleep(RETRY_DELAY)
        
        # This should not be reached, but as a fallback
        raise SauceNAOError("Failed to get a response from SauceNAO API.")

    def _process_results(self, api_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filters, sorts, and structures the raw API results.

        Args:
            api_response: The raw JSON response from SauceNAO.

        Returns:
            A dictionary with structured results and metadata.
        """
        header = api_response.get("header", {})
        results = api_response.get("results", [])

        if not results:
            return {"header": header, "results": [], "has_low_similarity_results": False}

        # Filter and sort results
        valid_results = [
            res for res in results
            if 'header' in res and 'similarity' in res['header']
        ]
        
        # Sort by similarity descending
        valid_results.sort(
            key=lambda x: float(x['header']['similarity']),
            reverse=True
        )

        # Separate high and low similarity results
        high_similarity_results = [
            res for res in valid_results 
            if float(res['header']['similarity']) >= DEFAULT_MIN_SIMILARITY
        ]
        
        has_low_similarity_results = len(valid_results) > len(high_similarity_results)

        # Limit to max results
        final_results = high_similarity_results[:MAX_RESULTS]

        return {
            "header": header,
            "results": final_results,
            "has_low_similarity_results": has_low_similarity_results,
        }
