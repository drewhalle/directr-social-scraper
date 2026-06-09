# Setup Instructions

Complete these steps to get the social media scraper running automatically.

## Step 1: Create Supabase Project (5 min)

1. Go to [supabase.com](https://supabase.com)
2. Click **New Project**
3. Choose a project name (e.g., "annabel-social-data")
4. Choose a password (save this)
5. Select region (closer to Canada is better: N. Virginia or similar)
6. Click **Create new project** and wait for initialization

## Step 2: Initialize Database Schema (5 min)

1. In Supabase, go to **SQL Editor** (left sidebar)
2. Click **New Query**
3. Copy the entire contents of `supabase-schema.sql` from this repo
4. Paste into the SQL editor
5. Click **Run**
6. You should see "Success" for all statements

**Verify**: Go to **Table Editor** and confirm you see 3 tables:
- `social_media_artists`
- `social_media_posts`
- `social_media_comments`

## Step 3: Get Supabase Credentials (2 min)

1. In Supabase, go to **Settings** (gear icon, bottom-left)
2. Click **API**
3. Copy your **Project URL** (starts with `https://`)
4. Under **Project API Keys**, find and copy the **`anon` public** key (NOT the `service_role` key)

**Important**: Never commit these to git. They go in GitHub Secrets, not `.env` in the repo.

## Step 4: Initialize Artist Record (2 min)

Run one-time initialization to create Annabel's artist record:

1. In Supabase SQL Editor, run:

```sql
INSERT INTO public.social_media_artists (
  directr_artist_id,
  instagram_handle,
  tiktok_handle
) VALUES (
  'e9b87f0d-9956-4a45-9267-a0705858d41c',
  'annabelgutherz',
  'annabelgutherz'
);
```

2. Check **Table Editor** → **social_media_artists** to confirm the row was added.

## Step 5: Create GitHub Repo (3 min)

1. Create a new repository on GitHub (e.g., `directr-social-scraper`)
2. Clone it locally:
   ```bash
   git clone https://github.com/your-username/directr-social-scraper.git
   cd directr-social-scraper
   ```
3. Copy all files from this directory into your repo
4. Commit and push:
   ```bash
   git add .
   git commit -m "Initial commit: social media scraper"
   git push
   ```

## Step 6: Add GitHub Secrets (5 min)

1. Go to your GitHub repo
2. Click **Settings** (top navigation)
3. On the left sidebar, click **Secrets and variables** → **Actions**
4. Click **New repository secret** (green button)

**Add two secrets:**

### Secret 1: SUPABASE_URL
- **Name**: `SUPABASE_URL`
- **Value**: Paste your Supabase Project URL from Step 3
- Click **Add secret**

### Secret 2: SUPABASE_KEY
- **Name**: `SUPABASE_KEY`
- **Value**: Paste your Supabase anon public key from Step 3
- Click **Add secret**

**Verify**: You should now see both secrets listed (values hidden with dots).

## Step 7: Test the Workflow (2 min)

1. Go to **Actions** (top navigation in GitHub)
2. Click **Daily Social Media Scrape** (on the left)
3. Click **Run workflow** button (top-right)
4. Select the **Branch** (main) and click **Run workflow**

**Monitor the run:**
- The workflow will start immediately
- Click the in-progress run to see logs
- Check **Run scraper** step for progress
- Should take 2-5 minutes depending on platform response

**Check for success:**
- If green ✅ checkmark appears next to "Run scraper", it succeeded
- If red ❌, click it to see error logs

## Step 8: Verify Data in Supabase (2 min)

1. Go back to Supabase
2. Click **Table Editor** (left sidebar)
3. Click **social_media_posts**
4. You should see posts populated with data

**Spot-check fields:**
- `platform` should be "instagram" or "tiktok"
- `post_url` should be a valid URL
- `likes`, `comments`, `views` should have numbers > 0
- `engagement_rate` should auto-calculate

## Step 9: Enable Automatic Daily Runs (1 min)

The workflow is already configured to run daily at **2 AM UTC**. No action needed.

To verify:
1. Go to **Actions** → **Daily Social Media Scrape**
2. Scroll down to **Workflow runs**
3. You'll see the manual test run you just did
4. Tomorrow morning, a new automatic run will appear at 2 AM UTC (10 PM ET / 7 PM PT previous day)

## Troubleshooting

### "Runner registration error"
Usually a temporary GitHub Actions issue. Wait 5 min and re-run.

### "No module named 'instagriffe'"
The workflow has a cache issue. Go to **Settings** → **Actions** → **General** → **Caches** and delete all caches, then re-run.

### "Supabase connection failed"
1. Double-check your secrets (Settings → Secrets)
2. Verify `SUPABASE_URL` starts with `https://`
3. Verify `SUPABASE_KEY` is the **anon public** key, not `service_role`
4. Check your Supabase project is active (not paused)

### "No Instagram posts found"
1. Check `@annabelgutherz` is the correct public handle
2. Verify the account exists and is public
3. instagriffe may have rate limits; wait an hour and retry

### "TikTok metrics showing 0"
Expected. TikTok blocks automated scraping. The scraper will continue improving, but for now expects 0 metrics.

## Monitoring & Maintenance

### Weekly Check
- Go to **Actions** tab
- Look for any failed runs (red ❌)
- If a run failed, click it to see the error

### Monthly Review
- Go to Supabase **SQL Editor**
- Run query to check total posts:
  ```sql
  SELECT platform, COUNT(*) FROM social_media_posts GROUP BY platform;
  ```
- Verify data is accumulating

### Troubleshooting Failed Runs
1. Click the failed run
2. Click **Run scraper** step
3. Read the error message and scroll up for context
4. Common fixes:
   - Instagram blocked the IP → wait and retry
   - TikTok timeout → normal, scraper continues
   - Supabase auth error → check secrets again

## What Happens Next

Once data is flowing into Supabase, you can:

1. **Query data directly** via Supabase SQL or REST API
2. **Build a dashboard** in directr to visualize trends
3. **Feed insights** into the strategy (highest-engagement hooks, audience sentiment, posting patterns)
4. **Iterate strategy** based on real data, not guessing

## Files Reference

- `.github/workflows/daily-scrape.yml` — Automation trigger
- `src/scraper.py` — Instagram + TikTok scraping logic
- `src/config.py` — Configuration (handles, post limits)
- `src/supabase_client.py` — Database operations
- `src/comment_analyzer.py` — Sentiment + audience classification
- `supabase-schema.sql` — Database initialization
- `requirements.txt` — Python dependencies

## Questions?

Check the **README.md** for technical details or review the workflow logs in GitHub Actions for specific error messages.
