import logging
import json
from datetime import datetime
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY, ANNABEL_ARTIST_ID

logger = logging.getLogger(__name__)


class SupabaseClient:
    def __init__(self):
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables required")

        self.client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.artist_id = None

    def ensure_artist_exists(self) -> str:
        """Create artist record if missing, return local artist_id"""
        try:
            # Check if artist exists
            response = self.client.table("social_media_artists").select("id").eq(
                "directr_artist_id", ANNABEL_ARTIST_ID
            ).execute()

            if response.data:
                self.artist_id = response.data[0]["id"]
                logger.info(f"Artist record found: {self.artist_id}")
                return self.artist_id

            # Create artist record
            response = self.client.table("social_media_artists").insert({
                "directr_artist_id": ANNABEL_ARTIST_ID,
                "instagram_handle": "annabelgutherz",
                "tiktok_handle": "annabelgutherz"
            }).execute()

            self.artist_id = response.data[0]["id"]
            logger.info(f"Artist record created: {self.artist_id}")
            return self.artist_id

        except Exception as e:
            logger.error(f"Error ensuring artist exists: {e}")
            raise

    def get_artist_id(self) -> str:
        """Get local Supabase artist ID"""
        if not self.artist_id:
            self.ensure_artist_exists()
        return self.artist_id

    def insert_posts(self, platform: str, posts: list) -> int:
        """Upsert posts into social_media_posts table"""
        if not posts:
            return 0

        try:
            artist_id = self.get_artist_id()
            inserted = 0

            for post in posts:
                post_data = {
                    "artist_id": artist_id,
                    "platform": platform,
                    "post_id": post.get("post_id"),
                    "post_url": post.get("post_url"),
                    "post_date": post.get("post_date"),
                    "caption": post.get("caption", ""),
                    "views": post.get("views", 0),
                    "likes": post.get("likes", 0),
                    "comments": post.get("comments", 0),
                    "shares": post.get("shares", 0),
                    "saves": post.get("saves", 0),
                    "top_comments": json.dumps(post.get("top_comments", [])),
                    "audience_classification": json.dumps(post.get("audience_classification", {})),
                    "sentiment_summary": post.get("sentiment_summary", "neutral"),
                }

                # Upsert (insert or update)
                response = self.client.table("social_media_posts").upsert(
                    post_data,
                    on_conflict="artist_id,platform,post_id"
                ).execute()

                inserted += len(response.data) if response.data else 0

            logger.info(f"Inserted {inserted} {platform} posts")
            return inserted

        except Exception as e:
            logger.error(f"Error inserting posts: {e}")
            raise

    def insert_comments(self, post_id: str, comments: list) -> int:
        """Insert comments into social_media_comments table"""
        if not comments:
            return 0

        try:
            inserted = 0

            for comment in comments:
                comment_data = {
                    "post_id": post_id,
                    "author": comment.get("author"),
                    "text": comment.get("text"),
                    "sentiment": comment.get("sentiment"),
                    "audience_type": comment.get("audience_type"),
                    "is_repeat_commenter": comment.get("is_repeat", False),
                }

                response = self.client.table("social_media_comments").insert(
                    comment_data
                ).execute()

                inserted += len(response.data) if response.data else 0

            logger.info(f"Inserted {inserted} comments for post {post_id}")
            return inserted

        except Exception as e:
            logger.error(f"Error inserting comments: {e}")
            raise

    def get_recent_posts(self, platform: str, limit: int = 20) -> list:
        """Fetch recent posts from database"""
        try:
            artist_id = self.get_artist_id()

            response = self.client.table("social_media_posts").select("*").eq(
                "artist_id", artist_id
            ).eq("platform", platform).order(
                "post_date", desc=True
            ).limit(limit).execute()

            return response.data if response.data else []

        except Exception as e:
            logger.error(f"Error fetching posts: {e}")
            return []
