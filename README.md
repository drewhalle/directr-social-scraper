# Annabel Gutherz Social Media Intelligence Scraper

Automated daily scraping of Instagram and TikTok social media data for artist content strategy analysis. Data is stored in isolated Supabase database and made available via REST API integration with directr admin.

## Architecture

```
GitHub Actions (daily trigger)
    ↓
Python scraper (Instagram + TikTok)
    ↓
Supabase PostgreSQL (isolated)
    ↓
REST API (consumed by directr admin)
```

## Features

- **Daily automation**: Runs every day at 2 AM UTC via GitHub Actions
- **Instagram scraping**: Fetches last 20 posts with engagement metrics and top comments
- **TikTok scraping**: Fetches last 20 posts with best-effort metrics
- **Comment analysis**: Sentiment analysis (positive/neutral/negative) + audience classification
- **Audience classification**: Repeat fans, new audience, family/friends, bots
- **Data persistence**: Supabase PostgreSQL (free tier eligible)
- **No core modification**: Completely isolated from directr admin app

## Database Schema

### Tables

**social_media_artists**
- `id` (UUID, primary key)
- `directr_artist_id` (UUID)
- `instagram_handle` (text)
- `tiktok_handle` (text)
- `created_at`, `updated_at` (timestamps)

**social_media_posts**
- `id` (UUID, primary key)
- `artist_id` (FK to social_media_artists)
- `platform` (text: 'instagram' or 'tiktok')
- `post_id` (text)
- `post_url` (text)
- `post_date` (timestamp)
- `caption` (text)
- `views`, `likes`, `comments`, `shares`, `saves` (integers)
- `engagement_rate` (numeric, GENERATED ALWAYS)
- `top_comments` (JSONB)
- `audience_classification` (JSONB)
- `sentiment_summary` (text)
- `created_at`, `updated_at` (timestamps)

**social_media_comments**
- `id` (UUID, primary key)
- `post_id` (FK to social_media_posts)
- `author` (text)
- `text` (text)
- `sentiment` (text: 'positive', 'neutral', 'negative')
- `audience_type` (text: 'repeat_fan', 'new_audience', 'family_friend', 'bot', 'unknown')
- `is_repeat_commenter` (boolean)
- `created_at` (timestamp)

## Setup

### 1. Create Supabase Project

1. Go to [supabase.com](https://supabase.com) and create a free project
2. Save your project URL and API key
3. Navigate to SQL Editor and run the schema initialization (see `supabase-schema.sql`)

### 2. Set GitHub Secrets

In your GitHub repo settings (Settings → Secrets and variables → Actions), add:

- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Your Supabase API key (use the `anon` public key, not the service role key)

### 3. Local Setup (Optional - for testing)

```bash
# Clone and install
git clone <repo-url>
cd directr-social-scraper
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
EOF

# Run scraper
python -m src.scraper
```

## Usage

### Automatic Daily Run

The scraper runs automatically every day at 2 AM UTC via GitHub Actions. Check the **Actions** tab in your GitHub repo to see run history and logs.

### Manual Trigger

Go to **Actions** → **Daily Social Media Scrape** → **Run workflow** → **Run workflow**

### Query Data in Supabase

```sql
-- Get all Instagram posts for Annabel
SELECT * FROM social_media_posts 
WHERE platform = 'instagram' 
ORDER BY post_date DESC 
LIMIT 20;

-- Get top engagement posts
SELECT post_url, caption, engagement_rate 
FROM social_media_posts 
ORDER BY engagement_rate DESC 
LIMIT 10;

-- Analyze sentiment distribution
SELECT 
  sentiment_summary,
  COUNT(*) as post_count,
  AVG(engagement_rate) as avg_engagement
FROM social_media_posts
GROUP BY sentiment_summary;

-- Find repeat commenters
SELECT author, COUNT(*) as comment_count
FROM social_media_comments
WHERE is_repeat_commenter = true
GROUP BY author
ORDER BY comment_count DESC;
```

## API Integration with directr

### Endpoint Structure

Once data is scraped, consume via Supabase REST API:

```bash
# Get recent Instagram posts
curl "https://<supabase-url>/rest/v1/social_media_posts?platform=eq.instagram&order=post_date.desc&limit=20" \
  -H "apikey: <supabase-key>"

# Get posts with engagement > 5%
curl "https://<supabase-url>/rest/v1/social_media_posts?engagement_rate=gt.5&order=engagement_rate.desc" \
  -H "apikey: <supabase-key>"
```

### Proposed directr Integration

In directr admin, add an Intelligence Layer that:

1. Queries `/rest/v1/social_media_posts` daily
2. Analyzes engagement patterns per platform
3. Identifies top-performing hooks + comment sentiment
4. Surfaces recommendations: "TikTok videos with [X hook] average 8% engagement" or "Comments on Reels are 45% positive"

This keeps social data completely isolated from directr core while feeding strategic insights.

## Monitoring

### GitHub Actions Logs

- Go to **Actions** tab
- Click most recent run
- Review **Run scraper** step for any errors
- Check **Upload logs on failure** artifact if run failed

### Common Issues

**"User not found"**
- Verify `INSTAGRAM_HANDLE` or `TIKTOK_HANDLE` in `src/config.py`
- Check handles are correct (@annabelgutherz)

**"403 Forbidden" from TikTok**
- TikTok aggressively blocks scraping
- Consider using a dedicated TikTok API partner or proxy service
- For now, data will return 0 metrics (graceful degradation)

**"Supabase connection failed"**
- Check `SUPABASE_URL` and `SUPABASE_KEY` are correct
- Ensure API key has appropriate permissions
- Check Supabase project is active (not paused)

**Instagram comments not fetching**
- instagriffe requires session cookies for private/restricted content
- Public profiles work without authentication

## Limitations & Future Work

### TikTok Scraping

TikTok requires JavaScript rendering and aggressively blocks automated access. Current implementation:

- ✅ Scrapes post URLs from profile
- ⚠️ Metrics extraction is best-effort (may show 0)
- ❌ Comments require headless browser (Playwright/Puppeteer)

**Production upgrade**: Use Playwright for JS rendering + TikTok API if available.

### Instagram

- ✅ Works for public profiles
- ✅ Extracts top comments
- ⚠️ Saves count not exposed by instagriffe (fallback to 0)

### Rate Limiting

- Instagram: ~200 requests/hour per IP
- TikTok: Aggressive blocking, rotates User-Agent headers (still fragile)

**Production upgrade**: Proxy rotation, randomized delays, dedicated scraping service.

## Cost Analysis

| Component | Cost | Notes |
|-----------|------|-------|
| Supabase | Free | 500MB storage, sufficient for 1M+ posts |
| GitHub Actions | Free | 2,000 minutes/month included |
| Total | $0/month | Works fully on free tier |

Estimated usage:
- 2 posts × 2 platforms × 30 days = 120 posts/month
- ~1 KB per post × 120 = 0.12 MB/month
- Supabase quota: 500 MB = 4,166 months of data

## Development

### Project Structure

```
directr-social-scraper/
├── .github/workflows/
│   └── daily-scrape.yml          # GitHub Actions workflow
├── src/
│   ├── __init__.py
│   ├── config.py                 # Configuration constants
│   ├── scraper.py                # Main scraper logic
│   ├── supabase_client.py         # Database operations
│   └── comment_analyzer.py        # Sentiment + audience analysis
├── requirements.txt
├── .gitignore
└── README.md
```

### Adding New Platforms

To add YouTube Shorts:

1. Implement `scrape_youtube()` method in `SocialMediaScraper`
2. Add platform-specific comment extraction
3. Update `config.py` with YouTube handle
4. Create migration to add `youtube` posts to database
5. Update workflow to call `scraper.scrape_youtube()`

## License

MIT
