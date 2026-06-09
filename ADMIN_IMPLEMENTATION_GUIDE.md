# Admin Implementation Guide — Multi-Artist Social Media Scraper

Integrate the social media scraper into directr admin to collect and analyze social data for all touring artists. Each artist's data is automatically separated and analyzable within the platform.

## Architecture Overview

```
directr admin
    ↓
    ├─ Artist management (handle + social links)
    ├─ Schedule scraper for each artist
    └─ Display social intelligence dashboard
         ↓
GitHub Actions (daily @ 2 AM UTC)
    ├─ Fetch artist list from directr admin API
    ├─ For each artist:
    │   ├─ Scrape Instagram posts
    │   ├─ Scrape TikTok posts
    │   └─ Store in Supabase (artist_id → posts → comments)
    └─ Log completion status
         ↓
Supabase (isolated database)
    ├─ artists table (artist_id, handles, created_at)
    ├─ posts table (artist_id FK, platform, engagement metrics)
    └─ comments table (post_id FK, sentiment, audience type)
         ↓
directr admin REST API
    └─ GET /api/social-intelligence?artist_id=xxx&platform=instagram
         ↓
directr UI
    └─ Display:
        • Top posts by engagement
        • Sentiment trends
        • Audience composition
        • Recommended content hooks
```

---

## Step 1: Add Artist Social Handles to directr Admin

### Database Changes

Add columns to your `artists` or `artist_profiles` table:

```sql
-- In your directr database
ALTER TABLE artists ADD COLUMN IF NOT EXISTS instagram_handle VARCHAR(255);
ALTER TABLE artists ADD COLUMN IF NOT EXISTS tiktok_handle VARCHAR(255);
ALTER TABLE artists ADD COLUMN IF NOT EXISTS youtube_handle VARCHAR(255);
ALTER TABLE artists ADD COLUMN IF NOT EXISTS scrape_enabled BOOLEAN DEFAULT false;

-- Index for scraper queries
CREATE INDEX idx_artists_scrape_enabled ON artists(scrape_enabled) WHERE scrape_enabled = true;
```

### Admin UI Form

Add fields to the artist edit page:

```tsx
// directr admin: pages/artists/[id]/edit.tsx (or equivalent)

import { useState } from 'react';

export default function ArtistEdit({ artist }) {
  const [formData, setFormData] = useState({
    name: artist.name,
    instagram_handle: artist.instagram_handle || '',
    tiktok_handle: artist.tiktok_handle || '',
    youtube_handle: artist.youtube_handle || '',
    scrape_enabled: artist.scrape_enabled || false,
  });

  const handleSave = async () => {
    await fetch(`/api/artists/${artist.id}`, {
      method: 'PUT',
      body: JSON.stringify(formData),
    });
  };

  return (
    <div>
      <h2>Social Media Handles</h2>
      
      <label>
        Instagram Handle
        <input
          type="text"
          placeholder="@annabelgutherz"
          value={formData.instagram_handle}
          onChange={(e) => setFormData({
            ...formData,
            instagram_handle: e.target.value
          })}
        />
      </label>

      <label>
        TikTok Handle
        <input
          type="text"
          placeholder="@annabelgutherz"
          value={formData.tiktok_handle}
          onChange={(e) => setFormData({
            ...formData,
            tiktok_handle: e.target.value
          })}
        />
      </label>

      <label>
        YouTube Handle
        <input
          type="text"
          placeholder="@drewznth"
          value={formData.youtube_handle}
          onChange={(e) => setFormData({
            ...formData,
            youtube_handle: e.target.value
          })}
        />
      </label>

      <label>
        <input
          type="checkbox"
          checked={formData.scrape_enabled}
          onChange={(e) => setFormData({
            ...formData,
            scrape_enabled: e.target.checked
          })}
        />
        Enable Social Scraping
      </label>

      <button onClick={handleSave}>Save</button>
    </div>
  );
}
```

### API Endpoint

Add route to save artist social handles:

```typescript
// directr backend: routes/api/artists/[id].ts (or equivalent)

export async function PUT(req, res) {
  const { id } = req.query;
  const { instagram_handle, tiktok_handle, youtube_handle, scrape_enabled } = req.body;

  // Update your database (Prisma example)
  const artist = await prisma.artists.update({
    where: { id },
    data: {
      instagram_handle,
      tiktok_handle,
      youtube_handle,
      scrape_enabled,
    },
  });

  res.status(200).json(artist);
}
```

---

## Step 2: Sync Artists to Supabase

Create an endpoint in directr admin that the scraper can call to fetch all artists needing scraping.

### API Endpoint: Get Artists for Scraping

```typescript
// directr backend: routes/api/scraper/artists.ts

export async function GET(req, res) {
  // Fetch all artists with scrape_enabled=true
  const artists = await prisma.artists.findMany({
    where: {
      scrape_enabled: true,
    },
    select: {
      id: true,
      directr_artist_id: true, // If you have this
      name: true,
      instagram_handle: true,
      tiktok_handle: true,
      youtube_handle: true,
    },
  });

  res.status(200).json(artists);
}
```

### Scraper: Fetch & Sync Artists

Update `src/config.py` in the scraper to fetch artist list dynamically:

```python
# directr-social-scraper/src/config.py

import os
import requests

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

DIRECTR_ADMIN_URL = os.getenv("DIRECTR_ADMIN_URL", "https://directr-admin.vercel.app")
DIRECTR_ADMIN_API_KEY = os.getenv("DIRECTR_ADMIN_API_KEY", "")  # Set in GitHub Secrets

POSTS_TO_FETCH = 20
COMMENT_SAMPLE_SIZE = 3

FAMILY_KEYWORDS = {
    "mom", "dad", "sister", "brother", "family",
    "love you", "mum", "papa", "family friend"
}

BOT_KEYWORDS = {
    "follow", "check out", "link in bio", "dm for",
    "tag us", "shop link", "use code", "promo"
}


def get_artists_to_scrape():
    """Fetch list of artists from directr admin"""
    try:
        url = f"{DIRECTR_ADMIN_URL}/api/scraper/artists"
        headers = {"Authorization": f"Bearer {DIRECTR_ADMIN_API_KEY}"} if DIRECTR_ADMIN_API_KEY else {}
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        artists = response.json()
        return artists
    
    except Exception as e:
        print(f"Error fetching artists: {e}")
        return []
```

### GitHub Secrets: Add directr Admin Credentials

```bash
# In GitHub repo settings, add:
DIRECTR_ADMIN_URL=https://directr-admin.vercel.app
DIRECTR_ADMIN_API_KEY=your-api-key-here
```

---

## Step 3: Update Scraper for Multi-Artist Support

Modify the scraper to iterate through all artists and collect data separately.

### Updated Scraper Entry Point

```python
# directr-social-scraper/src/scraper.py

import asyncio
import logging
from typing import List, Dict

from .config import get_artists_to_scrape
from .supabase_client import SupabaseClient
from .comment_analyzer import CommentAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SocialMediaScraper:
    def __init__(self):
        self.db = SupabaseClient()
        self.analyzer = CommentAnalyzer()

    async def scrape_instagram(self, artist: Dict, artist_id: str) -> List[Dict]:
        """Scrape Instagram posts for a specific artist"""
        instagram_handle = artist.get("instagram_handle")
        
        if not instagram_handle:
            logger.info(f"No Instagram handle for artist {artist['name']}")
            return []

        try:
            logger.info(f"Scraping Instagram for @{instagram_handle} (artist: {artist['name']})")
            
            # Placeholder: Add real scraping logic here
            # For now, returns empty to allow infrastructure to work
            posts = []
            
            return posts

        except Exception as e:
            logger.error(f"Instagram scraping failed for {artist['name']}: {e}")
            return []

    async def scrape_tiktok(self, artist: Dict, artist_id: str) -> List[Dict]:
        """Scrape TikTok posts for a specific artist"""
        tiktok_handle = artist.get("tiktok_handle")
        
        if not tiktok_handle:
            logger.info(f"No TikTok handle for artist {artist['name']}")
            return []

        try:
            logger.info(f"Scraping TikTok for @{tiktok_handle} (artist: {artist['name']})")
            
            # Placeholder: Add real scraping logic here
            posts = []
            
            return posts

        except Exception as e:
            logger.error(f"TikTok scraping failed for {artist['name']}: {e}")
            return []

    async def scrape_artist(self, artist: Dict) -> None:
        """Scrape all platforms for a single artist"""
        artist_id = artist["id"]  # Use directr artist ID
        artist_name = artist["name"]
        
        logger.info(f"Starting scrape for {artist_name}")
        
        # Ensure artist record in Supabase
        self.db.ensure_artist_exists(
            directr_id=artist_id,
            instagram_handle=artist.get("instagram_handle", ""),
            tiktok_handle=artist.get("tiktok_handle", ""),
        )

        # Scrape Instagram
        ig_posts = await self.scrape_instagram(artist, artist_id)
        if ig_posts:
            self.db.insert_posts(artist_id, "instagram", ig_posts)
            logger.info(f"Inserted {len(ig_posts)} Instagram posts for {artist_name}")

        # Scrape TikTok
        tt_posts = await self.scrape_tiktok(artist, artist_id)
        if tt_posts:
            self.db.insert_posts(artist_id, "tiktok", tt_posts)
            logger.info(f"Inserted {len(tt_posts)} TikTok posts for {artist_name}")

        logger.info(f"Completed scrape for {artist_name}")

    async def run(self) -> None:
        """Execute full scraping pipeline for all artists"""
        logger.info("=" * 70)
        logger.info("Starting multi-artist social media scrape")
        logger.info("=" * 70)

        try:
            # Fetch artists from directr admin
            artists = get_artists_to_scrape()
            
            if not artists:
                logger.warning("No artists found to scrape")
                return

            logger.info(f"Found {len(artists)} artists to scrape")

            # Scrape each artist sequentially (or use asyncio.gather for parallel)
            for artist in artists:
                try:
                    await self.scrape_artist(artist)
                except Exception as e:
                    logger.error(f"Error scraping artist {artist['name']}: {e}")
                    continue

            logger.info("Scraping pipeline completed successfully")

        except Exception as e:
            logger.error(f"Scraping pipeline failed: {e}")
            raise


async def main():
    """Entry point for scraper"""
    scraper = SocialMediaScraper()
    await scraper.run()


if __name__ == "__main__":
    asyncio.run(main())
```

### Updated Supabase Client

```python
# directr-social-scraper/src/supabase_client.py

import logging
import json
from supabase import create_client, Client
from .config import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger(__name__)


class SupabaseClient:
    def __init__(self):
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY required")
        
        self.client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    def ensure_artist_exists(self, directr_id: str, instagram_handle: str = "", tiktok_handle: str = "") -> str:
        """Create or update artist record in Supabase, return local artist_id"""
        try:
            # Check if artist exists
            response = self.client.table("social_media_artists").select("id").eq(
                "directr_artist_id", directr_id
            ).execute()

            if response.data:
                artist_id = response.data[0]["id"]
                
                # Update handles if changed
                self.client.table("social_media_artists").update({
                    "instagram_handle": instagram_handle,
                    "tiktok_handle": tiktok_handle,
                }).eq("directr_artist_id", directr_id).execute()
                
                return artist_id

            # Create new artist record
            response = self.client.table("social_media_artists").insert({
                "directr_artist_id": directr_id,
                "instagram_handle": instagram_handle,
                "tiktok_handle": tiktok_handle,
            }).execute()

            artist_id = response.data[0]["id"]
            logger.info(f"Created artist record: {artist_id}")
            return artist_id

        except Exception as e:
            logger.error(f"Error ensuring artist exists: {e}")
            raise

    def insert_posts(self, directr_artist_id: str, platform: str, posts: list) -> int:
        """Upsert posts for an artist"""
        if not posts:
            return 0

        try:
            # Get local artist_id
            response = self.client.table("social_media_artists").select("id").eq(
                "directr_artist_id", directr_artist_id
            ).execute()

            if not response.data:
                logger.error(f"Artist {directr_artist_id} not found in Supabase")
                return 0

            artist_id = response.data[0]["id"]
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

                response = self.client.table("social_media_posts").upsert(
                    post_data,
                    on_conflict="artist_id,platform,post_id"
                ).execute()

                inserted += len(response.data) if response.data else 0

            logger.info(f"Inserted {inserted} {platform} posts for artist {directr_artist_id}")
            return inserted

        except Exception as e:
            logger.error(f"Error inserting posts: {e}")
            raise

    def get_artist_posts(self, directr_artist_id: str, platform: str = None, limit: int = 20):
        """Fetch posts for an artist"""
        try:
            # Get local artist_id
            response = self.client.table("social_media_artists").select("id").eq(
                "directr_artist_id", directr_artist_id
            ).execute()

            if not response.data:
                return []

            artist_id = response.data[0]["id"]

            # Build query
            query = self.client.table("social_media_posts").select("*").eq(
                "artist_id", artist_id
            )

            if platform:
                query = query.eq("platform", platform)

            query = query.order("post_date", desc=True).limit(limit)
            
            response = query.execute()
            return response.data if response.data else []

        except Exception as e:
            logger.error(f"Error fetching posts: {e}")
            return []
```

---

## Step 4: Add directr Admin API Integration

Create endpoints to expose social intelligence to the directr UI.

### API Endpoint: Get Social Intelligence

```typescript
// directr backend: routes/api/social-intelligence.ts

import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_KEY
);

export async function GET(req, res) {
  const { artist_id, platform } = req.query;

  if (!artist_id) {
    return res.status(400).json({ error: "artist_id required" });
  }

  try {
    // Get posts for artist
    let query = supabase
      .from('social_media_posts')
      .select('*')
      .eq('directr_artist_id', artist_id);

    if (platform) {
      query = query.eq('platform', platform);
    }

    const { data: posts } = await query
      .order('engagement_rate', { ascending: false })
      .limit(20);

    // Get sentiment analysis
    const { data: sentiment } = await supabase
      .from('sentiment_analysis')
      .select('*')
      .eq('artist_id', artist_id);

    // Compute statistics
    const stats = {
      total_posts: posts.length,
      avg_engagement: posts.length > 0 
        ? (posts.reduce((sum, p) => sum + p.engagement_rate, 0) / posts.length).toFixed(2)
        : 0,
      top_posts: posts.slice(0, 5),
      sentiment_breakdown: sentiment,
      last_updated: new Date(),
    };

    res.status(200).json(stats);

  } catch (error) {
    console.error("Error:", error);
    res.status(500).json({ error: "Failed to fetch social intelligence" });
  }
}
```

### directr Admin UI Component

```tsx
// directr admin: components/SocialIntelligence.tsx

import { useEffect, useState } from 'react';

export function SocialIntelligence({ artistId }) {
  const [intelligence, setIntelligence] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchIntelligence = async () => {
      const res = await fetch(
        `/api/social-intelligence?artist_id=${artistId}`
      );
      const data = await res.json();
      setIntelligence(data);
      setLoading(false);
    };

    fetchIntelligence();
  }, [artistId]);

  if (loading) return <div>Loading...</div>;
  if (!intelligence) return <div>No data</div>;

  return (
    <div>
      <h2>Social Media Intelligence</h2>
      
      <div className="stats">
        <div>Total Posts: {intelligence.total_posts}</div>
        <div>Avg Engagement: {intelligence.avg_engagement}%</div>
        <div>Last Updated: {new Date(intelligence.last_updated).toLocaleString()}</div>
      </div>

      <h3>Top Performing Posts</h3>
      <ul>
        {intelligence.top_posts.map(post => (
          <li key={post.id}>
            <a href={post.post_url} target="_blank">
              {post.platform} - {post.engagement_rate}% engagement
            </a>
            <p>{post.caption}</p>
          </li>
        ))}
      </ul>

      <h3>Sentiment Breakdown</h3>
      <ul>
        {intelligence.sentiment_breakdown.map(s => (
          <li key={`${s.platform}-${s.sentiment}`}>
            {s.platform} - {s.sentiment}: {s.count} comments
          </li>
        ))}
      </ul>
    </div>
  );
}
```

---

## Step 5: Update GitHub Actions Workflow

Add environment variables for directr admin credentials:

```yaml
# .github/workflows/daily-scrape.yml

name: Daily Social Media Scrape

on:
  schedule:
    - cron: '0 2 * * *'
  workflow_dispatch:

jobs:
  scrape:
    runs-on: ubuntu-latest
    timeout-minutes: 30

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run scraper
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
          DIRECTR_ADMIN_URL: ${{ secrets.DIRECTR_ADMIN_URL }}
          DIRECTR_ADMIN_API_KEY: ${{ secrets.DIRECTR_ADMIN_API_KEY }}
        run: |
          python -m src.scraper

      - name: Upload logs on failure
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: scraper-logs
          path: logs/
          retention-days: 7
```

Add secrets to GitHub:

```bash
gh secret set DIRECTR_ADMIN_URL --body "https://directr-admin.vercel.app"
gh secret set DIRECTR_ADMIN_API_KEY --body "your-api-key-here"
```

---

## Step 6: Authentication & Security

### API Key Generation

In your directr admin, create a system for generating scraper API keys:

```typescript
// directr backend: routes/api/scraper/api-keys.ts

import crypto from 'crypto';

export async function POST(req, res) {
  const { name } = req.body;

  const apiKey = `directr_${crypto.randomBytes(32).toString('hex')}`;
  const keyHash = crypto.createHash('sha256').update(apiKey).digest('hex');

  // Store keyHash in database
  await prisma.scraperApiKeys.create({
    data: {
      name,
      keyHash,
      createdAt: new Date(),
    },
  });

  // Return key (shown only once)
  res.json({ apiKey });
}
```

### Verify API Key in Scraper

```python
# directr-social-scraper/src/config.py

def verify_api_key(api_key: str) -> bool:
    """Verify API key with directr admin"""
    try:
        url = f"{DIRECTR_ADMIN_URL}/api/scraper/verify-key"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        response = requests.post(url, headers=headers, timeout=5)
        return response.status_code == 200
    
    except Exception as e:
        logger.error(f"Failed to verify API key: {e}")
        return False
```

---

## Step 7: Monitoring & Logging

### Log Scraper Runs

```python
# directr-social-scraper/src/scraper.py

def log_scrape_run(artists_scraped: int, posts_collected: int, errors: int):
    """Log scrape run to directr admin"""
    try:
        url = f"{DIRECTR_ADMIN_URL}/api/scraper/log"
        
        payload = {
            "artists_scraped": artists_scraped,
            "posts_collected": posts_collected,
            "errors": errors,
            "timestamp": datetime.now().isoformat(),
        }
        
        response = requests.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {DIRECTR_ADMIN_API_KEY}"},
            timeout=10
        )
        
        logger.info(f"Logged scrape run: {response.status_code}")
    
    except Exception as e:
        logger.error(f"Failed to log scrape run: {e}")
```

### Scraper Status Dashboard

Add a status page in directr admin:

```tsx
// directr admin: pages/admin/scraper-status.tsx

import { useEffect, useState } from 'react';

export default function ScraperStatus() {
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    const fetchLogs = async () => {
      const res = await fetch('/api/scraper/logs?limit=10');
      const data = await res.json();
      setLogs(data);
    };

    fetchLogs();
    const interval = setInterval(fetchLogs, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      <h1>Scraper Status</h1>
      
      <table>
        <thead>
          <tr>
            <th>Time</th>
            <th>Artists</th>
            <th>Posts</th>
            <th>Errors</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {logs.map(log => (
            <tr key={log.id}>
              <td>{new Date(log.timestamp).toLocaleString()}</td>
              <td>{log.artists_scraped}</td>
              <td>{log.posts_collected}</td>
              <td>{log.errors}</td>
              <td>{log.errors === 0 ? '✅ Success' : '⚠️ Partial'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

---

## Step 8: Real Instagram/TikTok Scraping (Future)

Once infrastructure is verified, implement real scraping:

### Option A: Instagram Graph API
- Requires Meta business account + app approval
- Reliable, rate-limited, official
- Recommended for production

### Option B: Session-Based Scraping
- Use browser automation (Playwright/Selenium)
- More fragile, can be blocked
- Good for MVP

### Option C: Third-Party API
- Services like Apify, ScraperAPI
- Paid but reliable
- Best for scale

Update scraper methods as needed:

```python
async def scrape_instagram(self, artist: Dict, artist_id: str) -> List[Dict]:
    """Scrape Instagram using Graph API"""
    # TODO: Implement real scraping
    # For now, returning placeholder
    posts = []
    return posts
```

---

## Deployment Checklist

- [ ] Add social handle fields to directr admin artists table
- [ ] Create admin UI form for handles + scrape_enabled toggle
- [ ] Add API endpoint GET `/api/scraper/artists`
- [ ] Update scraper to fetch artists dynamically
- [ ] Update Supabase client for multi-artist support
- [ ] Add directr admin credentials to GitHub Secrets
- [ ] Create API endpoint GET `/api/social-intelligence?artist_id=xxx`
- [ ] Add SocialIntelligence component to artist dashboard
- [ ] Deploy updated scraper to GitHub repo
- [ ] Test with 2-3 artists
- [ ] Add scraper status monitoring dashboard
- [ ] Set up alerts for failed scrapes

---

## Data Flow Example

**When you add Annabel Gutherz to directr:**

1. Go to Artist Edit page
2. Enter:
   - Instagram: `@annabelgutherz`
   - TikTok: `@annabelgutherz`
   - Enable Scraping: ✓
3. Click Save
4. Tomorrow at 2 AM UTC:
   - Scraper fetches all enabled artists from your API
   - Scraper finds Annabel in the list
   - Scraper checks Supabase for existing artist record
   - Scraper attempts to scrape @annabelgutherz (Instagram + TikTok)
   - Scraper stores posts, comments, sentiment in Supabase
5. You view **Artist Dashboard**:
   - "Social Intelligence" panel shows:
     - Top 5 posts by engagement
     - Sentiment trend (45% positive, 30% neutral, 25% negative)
     - Audience breakdown (repeat fans: 35%, new: 40%, etc.)
6. Data persists independently for each artist

---

## API Reference

### GET /api/scraper/artists
Returns list of artists with scraping enabled.

**Response:**
```json
[
  {
    "id": "abc123",
    "name": "Annabel Gutherz",
    "instagram_handle": "@annabelgutherz",
    "tiktok_handle": "@annabelgutherz",
    "youtube_handle": null
  }
]
```

### GET /api/social-intelligence?artist_id=xxx&platform=instagram
Returns social intelligence for an artist.

**Response:**
```json
{
  "total_posts": 42,
  "avg_engagement": 5.23,
  "top_posts": [...],
  "sentiment_breakdown": [...],
  "last_updated": "2026-06-09T17:40:06Z"
}
```

### POST /api/scraper/log
Log a scraper run (called by GitHub Actions).

**Payload:**
```json
{
  "artists_scraped": 5,
  "posts_collected": 98,
  "errors": 1,
  "timestamp": "2026-06-09T02:00:00Z"
}
```

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Scraper can't find artists | API endpoint not working | Verify DIRECTR_ADMIN_URL + API_KEY in secrets |
| "Artist not found in Supabase" | Artist record not synced | Call `ensure_artist_exists()` with correct directr_id |
| No posts inserted | Scraper not implemented yet | Add real scraping logic to `scrape_instagram()` / `scrape_tiktok()` |
| Data not separated by artist | Wrong artist_id used | Verify artist_id comes from directr, not hardcoded |
| API returns empty | No posts in Supabase yet | Run scraper manually or wait for next scheduled run |

---

## Next Steps

1. **Implement real scraping** for Instagram + TikTok (see Step 8)
2. **Add real-time scraping** trigger when you add a new artist (optional)
3. **Build content recommendations** using engagement data
4. **Add competitor benchmarking** (compare artists' metrics)
5. **Create audience analysis** (who comments, sentiment trends)
