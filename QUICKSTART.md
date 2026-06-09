# Quick Start — 30 Minutes to Live Data

Get the scraper running in under 30 minutes.

## 1. Create Supabase Project (5 min)

→ [supabase.com](https://supabase.com) → **New Project** → Name it, save password → Wait for setup

Save your **Project URL** and **anon public API key** (Settings → API)

## 2. Initialize Database (5 min)

In Supabase **SQL Editor**:
1. Copy all of `supabase-schema.sql`
2. Paste and click **Run**
3. Verify 3 tables created: `social_media_artists`, `social_media_posts`, `social_media_comments`

## 3. Add Artist Record (1 min)

In Supabase **SQL Editor**, run:
```sql
INSERT INTO public.social_media_artists (
  directr_artist_id, instagram_handle, tiktok_handle
) VALUES (
  'e9b87f0d-9956-4a45-9267-a0705858d41c',
  'annabelgutherz',
  'annabelgutherz'
);
```

## 4. Create GitHub Repo (3 min)

Create a new repo on GitHub, clone it, copy all files from this directory, push:
```bash
git clone https://github.com/YOUR_USERNAME/directr-social-scraper.git
cd directr-social-scraper
# Copy all files here
git add . && git commit -m "Initial commit" && git push
```

## 5. Add GitHub Secrets (5 min)

In your GitHub repo:
**Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add two secrets:
- `SUPABASE_URL` = your Supabase Project URL (from Step 1)
- `SUPABASE_KEY` = your Supabase anon public key (from Step 1)

## 6. Trigger Manual Run (2 min)

**Actions** → **Daily Social Media Scrape** → **Run workflow** → **Run workflow**

Monitor: Should complete in 2-5 minutes. Look for green ✅ next to "Run scraper"

## 7. Verify Data (2 min)

Go to Supabase → **Table Editor** → **social_media_posts**

You should see posts with:
- `platform` = "instagram" or "tiktok"
- `post_url` = valid URL
- `likes`, `comments`, `views` = numbers > 0
- `engagement_rate` = auto-calculated

**Done!** ✅ Data collection is live.

---

## Daily Data Flow

- **Every day at 2 AM UTC**: Scraper runs automatically (or you can manually trigger anytime)
- **Data lands in Supabase**: Posts, comments, sentiment, audience breakdown
- **Next step**: Query data and feed into directr strategy

## Common Queries

```sql
-- All Instagram posts, newest first
SELECT post_url, caption, engagement_rate, post_date 
FROM social_media_posts 
WHERE platform = 'instagram' 
ORDER BY post_date DESC LIMIT 20;

-- Top performing posts
SELECT post_url, engagement_rate, likes, comments 
FROM social_media_posts 
ORDER BY engagement_rate DESC LIMIT 10;

-- Sentiment breakdown
SELECT sentiment, COUNT(*) as count 
FROM social_media_comments 
GROUP BY sentiment;

-- Audience composition
SELECT audience_type, COUNT(*) as count 
FROM social_media_comments 
GROUP BY audience_type 
ORDER BY count DESC;
```

## Troubleshooting

**Workflow failed?**
- Click the failed run in GitHub Actions
- Click "Run scraper" step
- Read the error and scroll for context

**No data in database?**
- Check Supabase credentials in GitHub Secrets (Settings → Secrets)
- Verify `SUPABASE_URL` and `SUPABASE_KEY` are correct
- Run workflow again (Actions → Run workflow)

**Instagram posts showing 0?**
- Handle might be wrong (check `src/config.py`)
- Account might not be public
- Instagram might be rate-limiting (wait and retry)

**TikTok showing 0 metrics?**
- Expected — TikTok blocks automation
- Scraper continues, just returns 0 for now

---

## Next Steps

1. **Query data**: Use SQL queries above to explore patterns
2. **Dashboard**: Build visualization in directr admin
3. **Insights**: Extract viral hooks, sentiment trends, posting patterns
4. **Strategy**: Feed findings into Annabel's content strategy

---

## Files

- `SETUP.md` → Full step-by-step instructions
- `README.md` → Technical reference
- `IMPLEMENTATION_SUMMARY.md` → Architecture & design decisions

Done? Start with Step 1 above. 30 minutes from now, you'll have live data. ✨
