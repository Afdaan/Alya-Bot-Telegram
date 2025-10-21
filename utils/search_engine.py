"""
Web search engine integration using Google Custom Search Engine.
Provides clean search API with key rotation for availability.
"""
import json
import logging
import os
import random
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Union, Literal

import aiohttp
from urllib.parse import urlparse, quote_plus

from config.settings import DEFAULT_LANGUAGE

logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    title: str
    link: str
    snippet: Optional[str] = None
    image_url: Optional[str] = None
    thumbnail: Optional[str] = None
    displayed_link: Optional[str] = None
    result_type: Optional[str] = None
    source: Optional[str] = None

class SearchError(Exception):
    pass

async def search_web(
    query: str, 
    max_results: int = 8,
    safe_search: str = "off",
    search_type: Optional[Literal["profile", "news", "image", "general"]] = None,
    language: str = DEFAULT_LANGUAGE,
    exact_terms: Optional[str] = None,
    site_restrict: Optional[str] = None
) -> List[SearchResult]:
    api_keys_str = os.getenv("GOOGLE_API_KEYS", "")
    cse_id = os.getenv("GOOGLE_CSE_ID")
    if not api_keys_str or not cse_id:
        logger.error("Missing Google API keys or CSE ID")
        raise SearchError("Google Search API configuration is missing")
    api_keys = [key.strip() for key in api_keys_str.split(",") if key.strip()]
    random.shuffle(api_keys)
    if not api_keys:
        raise SearchError("No valid Google API keys found")
    enhanced_query, search_params = _prepare_query_by_type(query, search_type, site_restrict, exact_terms)
    errors = []
    for api_key in api_keys:
        try:
            results = await _execute_search(
                query=enhanced_query,
                api_key=api_key,
                cse_id=cse_id,
                max_results=max_results,
                safe_search=safe_search,
                language=language,
                search_type=search_type,
                extra_params=search_params
            )
            processed_results = _enrich_search_results(results, search_type)
            if search_type == "profile" and not _has_quality_profile_results(processed_results):
                logger.debug(f"Primary profile search yielded poor results for '{query}', trying alternatives")
                alt_strategies = _get_profile_fallback_strategies(query, site_restrict)
                for strategy_name, (alt_query, alt_params) in alt_strategies.items():
                    logger.debug(f"Trying profile search strategy: {strategy_name}")
                    try:
                        alt_results = await _execute_search(
                            query=alt_query,
                            api_key=api_key,
                            cse_id=cse_id,
                            max_results=max_results,
                            safe_search=safe_search,
                            language=language, 
                            search_type=search_type,
                            extra_params=alt_params
                        )
                        alt_processed = _enrich_search_results(alt_results, search_type)
                        if len(alt_processed) > len(processed_results):
                            logger.debug(f"Strategy '{strategy_name}' found better results: {len(alt_processed)} vs {len(processed_results)}")
                            processed_results = alt_processed
                            if _has_quality_profile_results(alt_processed):
                                break
                    except Exception as e:
                        logger.debug(f"Profile strategy '{strategy_name}' failed: {e}")
                        continue
            if processed_results:
                return processed_results
            if search_type == "profile" and "@" in query and not processed_results:
                clean_query = query.replace("@", "")
                last_chance_results = await search_web(
                    query=clean_query,
                    max_results=max_results,
                    safe_search=safe_search,
                    search_type=search_type,
                    language=language
                )
                if last_chance_results:
                    return last_chance_results
            return processed_results
        except Exception as e:
            errors.append(f"{type(e).__name__}: {str(e)}")
            logger.warning(f"Search failed with API key {api_key[:5]}...: {e}")
            continue
    error_details = "; ".join(errors) if errors else "Unknown error"
    logger.error(f"All API keys failed for search query '{query}': {error_details}")
    raise SearchError(f"Search failed after trying {len(api_keys)} API keys")

def _prepare_query_by_type(
    query: str, 
    search_type: Optional[str],
    site_restrict: Optional[str],
    exact_terms: Optional[str]
) -> tuple[str, dict]:
    enhanced_query = query
    search_params = {}
    if exact_terms:
        search_params["exactTerms"] = exact_terms
    if search_type == "profile":
        professional_sites = ["linkedin.com", "github.com", "gitlab.com", "dev.to", "medium.com"]
        social_sites = [
            "twitter.com", "x.com", "facebook.com", "instagram.com", "threads.net", 
            "reddit.com", "pinterest.com", "tiktok.com", "youtube.com",
            "twitch.tv", "osu.ppy.sh", "myanimelist.net", "last.fm"
        ]
        gaming_sites = ["steamcommunity.com", "discordapp.com", "discord.com"]
        niche_sites = ["osu.ppy.sh", "myanimelist.net", "anilist.co", "kitsu.io"]
        all_sites = professional_sites + social_sites + gaming_sites
        is_handle = query.strip().startswith("@") or " " not in query.strip()
        clean_query = query.strip().lstrip("@")
        has_gaming_terms = any(term in query.lower() for term in ["game", "gaming", "steam", "discord", "player", "osu"])
        has_anime_terms = any(term in query.lower() for term in ["anime", "manga", "weeb", "otaku", "mal", "myanimelist"])
        if is_handle:
            if has_gaming_terms or has_anime_terms:
                target_sites = professional_sites[:1] + gaming_sites + niche_sites
                if has_anime_terms:
                    target_sites = niche_sites + gaming_sites + professional_sites[:1]
                site_parts = []
                for i, site in enumerate(target_sites[:3]):
                    if i == 0:
                        site_parts.append(f"{clean_query} site:{site}")
                    else:
                        site_parts.append(f"site:{site}")
                enhanced_query = " OR ".join(site_parts)
                search_params["siteSearch"] = ",".join(target_sites)
            else:
                main_query = clean_query
                specific_sites = professional_sites[:2] + social_sites[:3]
                site_parts = [f"site:{site}" for site in specific_sites[:3]]
                enhanced_query = f"{main_query} {' OR '.join(site_parts)}"
                search_params["siteSearch"] = ",".join(all_sites)
        else:
            enhanced_query = f"{query} profile"
            search_params["siteSearch"] = ",".join(professional_sites + social_sites[:5])
    elif search_type == "news":
        search_params["sort"] = "date"
        enhanced_query = f"{query} berita terbaru"
        if "sort" not in search_params:
            search_params["sort"] = "date"
    elif search_type == "image":
        search_params["searchType"] = "image"
        enhanced_query = f"{query} high quality"
    if site_restrict:
        search_params["siteSearch"] = site_restrict
    return enhanced_query, search_params

def _get_profile_fallback_strategies(query: str, site_restrict: Optional[str]) -> Dict[str, tuple]:
    clean_query = query.strip().lstrip("@")
    strategies = {}
    strategies["google_dork"] = (
        f'"{clean_query}" OR "profile" OR "user" OR "account"',
        {
            "siteSearch": "twitter.com,github.com,linkedin.com,instagram.com,facebook.com"
        }
    )
    platforms = {
        "twitter": f"{clean_query} (twitter.com OR x.com)",
        "github": f"{clean_query} github.com",
        "linkedin": f"{clean_query} linkedin.com",
        "instagram": f"{clean_query} instagram.com",
        "facebook": f"{clean_query} facebook.com"
    }
    gaming_anime_terms = ["game", "gaming", "anime", "osu", "steam", "discord", "player"]
    has_gaming_terms = any(term in query.lower() for term in gaming_anime_terms)
    if has_gaming_terms:
        platforms.update({
            "osu": f"{clean_query} osu.ppy.sh",
            "steam": f"{clean_query} steamcommunity.com",
            "discord": f"{clean_query} discord",
            "mal": f"{clean_query} myanimelist.net"
        })
    for platform, platform_query in platforms.items():
        strategies[f"platform_{platform}"] = (
            platform_query,
            {}
        )
    strategies["exact_match"] = (
        f'"{clean_query}"', 
        {
            "exactTerms": clean_query
        }
    )
    strategies["social_profile_broad"] = (
        f"{clean_query} profile OR username OR account OR social media",
        {}
    )
    if " " in clean_query:
        parts = clean_query.split()
        if len(parts) > 1:
            components_query = " OR ".join(parts)
            strategies["component_parts"] = (
                f"{components_query} profile username account",
                {}
            )
    return strategies

def _has_quality_profile_results(results: List[SearchResult]) -> bool:
    if not results:
        return False
    profile_domains = [
        "linkedin.com", "github.com", "gitlab.com", "dev.to", "medium.com",
        "twitter.com", "x.com", "facebook.com", "instagram.com", "threads.net", 
        "tiktok.com", "pinterest.com", "youtube.com", "reddit.com",
        "twitch.tv", "steamcommunity.com", "discord.com", "discord.gg",
        "osu.ppy.sh", "myanimelist.net", "anilist.co", "kitsu.io"
    ]
    profile_hits = 0
    for result in results:
        if result.source and any(domain in result.source for domain in profile_domains):
            profile_hits += 1
        title_lower = result.title.lower() if result.title else ""
        snippet_lower = result.snippet.lower() if result.snippet else ""
        profile_signals = ["profile", "account", "user", "@"]
        if any(signal in title_lower or signal in snippet_lower for signal in profile_signals):
            profile_hits += 0.5
    return profile_hits >= 1.5

async def _execute_search(
    query: str,
    api_key: str,
    cse_id: str,
    max_results: int = 8,
    safe_search: str = "off",
    language: str = DEFAULT_LANGUAGE,
    search_type: Optional[str] = None,
    extra_params: Dict[str, Any] = None
) -> List[SearchResult]:
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "q": query,
        "key": api_key,
        "cx": cse_id,
        "num": min(max_results, 10),
        "safe": safe_search,
        "hl": language,
        "gl": language,
        "lr": f"lang_{language}",
        "filter": "0",
    }
    if extra_params:
        params.update(extra_params)
    sanitized_params = {k: v for k, v in params.items() if k != "key"}
    logger.debug(f"Search query params: {sanitized_params}")
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, timeout=15) as response:
            if response.status != 200:
                error_text = await response.text()
                logger.error(f"Google CSE API error: {response.status} - {error_text}")
                response.raise_for_status()
            data = await response.json()
            search_info = data.get("searchInformation", {})
            total_results = search_info.get("totalResults", "0")
            search_time = search_info.get("searchTime", 0)
            logger.debug(f"Search returned {total_results} results in {search_time} seconds")
            items = data.get("items", [])
            if not items:
                return []
            results = []
            for item in items:
                result = SearchResult(
                    title=item.get("title", ""),
                    link=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    displayed_link=item.get("displayLink", ""),
                    source=item.get("displayLink", "")
                )
                if "pagemap" in item:
                    pagemap = item["pagemap"]
                    result = _extract_pagemap_data(result, pagemap, search_type)
                if result.link:
                    try:
                        result.source = urlparse(result.link).netloc
                    except:
                        pass
                results.append(result)
            return results

def _extract_pagemap_data(
    result: SearchResult, 
    pagemap: Dict[str, Any], 
    search_type: Optional[str]
) -> SearchResult:
    if "cse_thumbnail" in pagemap and pagemap["cse_thumbnail"]:
        thumbnail = pagemap["cse_thumbnail"][0]
        result.thumbnail = thumbnail.get("src")
    elif "cse_image" in pagemap and pagemap["cse_image"]:
        image = pagemap["cse_image"][0]
        result.image_url = image.get("src")
        result.thumbnail = image.get("src")
    if "metatags" in pagemap and pagemap["metatags"]:
        metatags = pagemap["metatags"][0]
        if result.snippet and len(result.snippet) < 50:
            description = metatags.get("og:description") or metatags.get("description")
            if description and len(description) > len(result.snippet):
                result.snippet = description
    if search_type == "profile" or "person" in pagemap:
        result.result_type = "profile"
    elif "article" in pagemap or search_type == "news":
        result.result_type = "news"
    elif "imageobject" in pagemap or search_type == "image":
        result.result_type = "image"
    return result

def _enrich_search_results(results: List[SearchResult], search_type: Optional[str]) -> List[SearchResult]:
    if not results:
        return []
    for result in results:
        if result.link:
            try:
                domain = urlparse(result.link).netloc
                result.source = domain
                if not result.result_type:
                    if any(site in domain for site in ["linkedin.com", "github.com", "twitter.com", 
                                                     "facebook.com", "instagram.com"]):
                        result.result_type = "profile"
                    elif any(site in domain for site in ["news", "berita", "artikel", "kompas", 
                                                       "detik", "tempo", "cnn", "bbc", "cnbc"]):
                        result.result_type = "news"
                    elif search_type:
                        result.result_type = search_type
            except Exception as e:
                logger.debug(f"Failed to extract domain: {e}")
        if search_type == "profile" and not result.result_type:
            result.result_type = "profile"
    return results

async def search_profile(
    query: str, 
    max_results: int = 8,
    site_restrict: Optional[str] = None
) -> List[SearchResult]:
    return await search_web(
        query=query,
        max_results=max_results,
        search_type="profile",
        safe_search="off",
        site_restrict=site_restrict
    )

async def search_news(
    query: str, 
    max_results: int = 8
) -> List[SearchResult]:
    return await search_web(
        query=query,
        max_results=max_results,
        search_type="news",
        safe_search="off"
    )

async def search_images(
    query: str, 
    max_results: int = 8
) -> List[SearchResult]:
    return await search_web(
        query=query,
        max_results=max_results,
        search_type="image",
        safe_search="off"
    )

def get_google_search_url(query: str) -> str:
    encoded_query = quote_plus(query)
    return f"https://www.google.com/search?q={encoded_query}"