import os

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Artist Configuration
ANNABEL_ARTIST_ID = "e9b87f0d-9956-4a45-9267-a0705858d41c"
INSTAGRAM_HANDLE = "annabelgutherz"
TIKTOK_HANDLE = "annabelgutherz"

# Scraping Configuration
POSTS_TO_FETCH = 20  # Only fetch last 20 posts per day
COMMENT_SAMPLE_SIZE = 3  # Top 3 comments per post

# Keywords for audience classification
FAMILY_KEYWORDS = {
    "mom", "dad", "sister", "brother", "family",
    "love you", "mum", "papa", "family friend"
}

BOT_KEYWORDS = {
    "follow", "check out", "link in bio", "dm for",
    "tag us", "shop link", "use code", "promo"
}
