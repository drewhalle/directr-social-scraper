import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict
from urllib.parse import urljoin
import aiohttp
from bs4 import BeautifulSoup
import instagriffe
from instagriffe import Client as InstaClient

from config import (
    INSTAGRAM_HANDLE,
    TIKTOK_HANDLE,
    POSTS_TO_FETCH,
    COMMENT_SAMPLE_SIZE,
    ANNABEL_ARTIST_ID,
)
from supabase_client import SupabaseClient
from comment_analyzer import CommentAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SocialMediaScraper:
    def __init__(self):
        self.db = SupabaseClient()
        self.analyzer = CommentAnalyzer()
        self.db.ensure_artist_exists()

    async def scrape_instagram(self) -> List[Dict]:
        """Scrape Instagram posts using instagriffe library"""
        try:
            logger.info(f"Scraping Instagram for @{INSTAGRAM_HANDLE}")

            async with InstaClient() as client:
                # Fetch user profile
                user = await client.user_by_username(INSTAGRAM_HANDLE)
                if not user:
                    logger.error(f"User {INSTAGRAM_HANDLE} not found")
                    return []

                # Fetch recent posts
                posts_gen = client.user_medias(user.pk, amount=POSTS_TO_FETCH)
                posts = []

                async for post in posts_gen:
                    try:
                        post_data = {
                            "post_id": str(post.id),
                            "post_url": f"https://www.instagram.com/p/{post.code}/",
                            "post_date": post.taken_at.isoformat() if post.taken_at else datetime.now().isoformat(),
                            "caption": post.caption_text or "",
                            "views": post.like_count or 0,
                            "likes": post.like_count or 0,
                            "comments": post.comment_count or 0,
                            "shares": 0,  # Instagram doesn't expose shares publicly
                            "saves": 0,   # Instagriffe may not expose saves, fallback to 0
                        }

                        # Get comments for this post
                        comments = await self._get_instagram_comments(client, post)
                        if comments:
                            post_data["top_comments"] = comments

                        posts.append(post_data)
                        logger.info(f"Scraped Instagram post {post.code}: {post.like_count} likes, {post.comment_count} comments")

                    except Exception as e:
                        logger.error(f"Error processing Instagram post: {e}")
                        continue

                return posts

        except Exception as e:
            logger.error(f"Instagram scraping failed: {e}")
            return []

    async def _get_instagram_comments(self, client: InstaClient, post) -> List[Dict]:
        """Extract and analyze top comments from Instagram post"""
        try:
            comments = []
            comments_gen = client.post_comments(post.id, amount=COMMENT_SAMPLE_SIZE)

            async for comment in comments_gen:
                sentiment = self.analyzer.analyze_sentiment(comment.text)
                is_repeat = comment.user.username in self.analyzer.repeat_commenters
                audience_type = self.analyzer.classify_audience(
                    comment.user.username,
                    comment.text,
                    is_repeat
                )

                comments.append({
                    "author": comment.user.username,
                    "text": comment.text,
                    "sentiment": sentiment,
                    "audience_type": audience_type,
                    "is_repeat": is_repeat,
                })

                if not is_repeat:
                    self.analyzer.repeat_commenters.add(comment.user.username)

            return comments

        except Exception as e:
            logger.error(f"Error extracting Instagram comments: {e}")
            return []

    async def scrape_tiktok(self) -> List[Dict]:
        """Scrape TikTok posts using public profile scraping"""
        try:
            logger.info(f"Scraping TikTok for @{TIKTOK_HANDLE}")

            posts = []
            base_url = f"https://www.tiktok.com/@{TIKTOK_HANDLE}/video/"

            # Note: TikTok blocks automated scraping aggressively.
            # This method uses a best-effort approach with User-Agent rotation.
            # For production, consider using a TikTok API partner or proxy service.

            async with aiohttp.ClientSession() as session:
                # Fetch user profile page to find video IDs
                profile_url = f"https://www.tiktok.com/@{TIKTOK_HANDLE}"
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }

                try:
                    async with session.get(profile_url, headers=headers, timeout=10) as resp:
                        if resp.status != 200:
                            logger.warning(f"TikTok profile returned {resp.status}. Scraping may be blocked.")
                            return []

                        html = await resp.text()
                        soup = BeautifulSoup(html, "html.parser")

                        # Extract video URLs from page (TikTok structure varies; this is a best-effort approach)
                        video_links = soup.find_all("a", {"href": True})
                        video_ids = []

                        for link in video_links:
                            href = link.get("href", "")
                            if "/video/" in href:
                                # Extract video ID from URL
                                try:
                                    video_id = href.split("/video/")[1].split("?")[0]
                                    if video_id.isdigit() and len(video_id) > 10:
                                        video_ids.append(video_id)
                                except IndexError:
                                    continue

                        video_ids = list(dict.fromkeys(video_ids))[:POSTS_TO_FETCH]  # Unique, limit to POSTS_TO_FETCH

                        if not video_ids:
                            logger.warning(f"No video IDs found for @{TIKTOK_HANDLE}. TikTok may be blocking the request.")
                            return []

                        # Fetch details for each video
                        for video_id in video_ids:
                            try:
                                post_data = await self._get_tiktok_post_data(session, video_id, headers)
                                if post_data:
                                    posts.append(post_data)

                            except Exception as e:
                                logger.error(f"Error fetching TikTok video {video_id}: {e}")
                                continue

                        logger.info(f"Scraped {len(posts)} TikTok posts")
                        return posts

                except asyncio.TimeoutError:
                    logger.error("TikTok profile request timed out")
                    return []

        except Exception as e:
            logger.error(f"TikTok scraping failed: {e}")
            return []

    async def _get_tiktok_post_data(self, session: aiohttp.ClientSession, video_id: str, headers: Dict) -> Dict:
        """Fetch individual TikTok post data"""
        try:
            video_url = f"https://www.tiktok.com/@{TIKTOK_HANDLE}/video/{video_id}"

            async with session.get(video_url, headers=headers, timeout=10) as resp:
                if resp.status != 200:
                    return None

                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")

                # Extract metrics from page (TikTok embeds stats in HTML)
                # These selectors are fragile and may break; consider API alternatives for production

                post_data = {
                    "post_id": video_id,
                    "post_url": video_url,
                    "post_date": datetime.now().isoformat(),
                    "caption": "",
                    "views": 0,
                    "likes": 0,
                    "comments": 0,
                    "shares": 0,
                    "saves": 0,
                }

                # Try to extract caption
                caption_elem = soup.find("meta", {"name": "description"})
                if caption_elem and caption_elem.get("content"):
                    post_data["caption"] = caption_elem.get("content", "")[:500]  # Limit to 500 chars

                # Extract metrics from JSON-LD or structured data (varies by page load)
                try:
                    # Look for stats in common HTML patterns
                    stats_divs = soup.find_all("div", {"class": lambda x: x and "count" in x.lower()})
                    for div in stats_divs:
                        text = div.get_text(strip=True)
                        if "K" in text or "M" in text:
                            # Rough parsing of "123K likes" format
                            if "like" in text.lower():
                                post_data["likes"] = self._parse_metric(text)
                            elif "comment" in text.lower():
                                post_data["comments"] = self._parse_metric(text)
                            elif "share" in text.lower():
                                post_data["shares"] = self._parse_metric(text)
                except:
                    pass

                # Get comments if available
                comments = await self._get_tiktok_comments(session, video_id, headers)
                if comments:
                    post_data["top_comments"] = comments

                return post_data

        except Exception as e:
            logger.error(f"Error extracting TikTok post data: {e}")
            return None

    @staticmethod
    def _parse_metric(text: str) -> int:
        """Parse metric text like '123K' or '1.2M' to integer"""
        try:
            text = text.lower().strip()
            multiplier = 1

            if "m" in text:
                multiplier = 1_000_000
                text = text.replace("m", "").strip()
            elif "k" in text:
                multiplier = 1_000
                text = text.replace("k", "").strip()

            num = float(text.split()[0])
            return int(num * multiplier)
        except:
            return 0

    async def _get_tiktok_comments(self, session: aiohttp.ClientSession, video_id: str, headers: Dict) -> List[Dict]:
        """Extract and analyze top comments from TikTok post"""
        try:
            comments = []

            # TikTok comments require API access or JS rendering; this is best-effort fallback
            # For production, use Playwright or Puppeteer for JS-heavy page rendering

            # Placeholder: Return empty for now. Production would need headless browser.
            logger.info(f"TikTok comments require JS rendering. Returning empty for now.")

            return comments

        except Exception as e:
            logger.error(f"Error extracting TikTok comments: {e}")
            return []

    async def run(self) -> None:
        """Execute full scraping pipeline"""
        logger.info("=" * 50)
        logger.info("Starting social media scrape")
        logger.info("=" * 50)

        try:
            # Scrape Instagram
            ig_posts = await self.scrape_instagram()
            if ig_posts:
                self.db.insert_posts("instagram", ig_posts)
                logger.info(f"Inserted {len(ig_posts)} Instagram posts")

            # Scrape TikTok
            tt_posts = await self.scrape_tiktok()
            if tt_posts:
                self.db.insert_posts("tiktok", tt_posts)
                logger.info(f"Inserted {len(tt_posts)} TikTok posts")

            logger.info("Scraping complete")

        except Exception as e:
            logger.error(f"Scraping pipeline failed: {e}")
            raise


async def main():
    """Entry point for scraper"""
    scraper = SocialMediaScraper()
    await scraper.run()


if __name__ == "__main__":
    asyncio.run(main())
