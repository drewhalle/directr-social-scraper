-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- social_media_artists table
CREATE TABLE public.social_media_artists (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  directr_artist_id UUID NOT NULL UNIQUE,
  instagram_handle TEXT NOT NULL,
  tiktok_handle TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- social_media_posts table
CREATE TABLE public.social_media_posts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  artist_id UUID NOT NULL REFERENCES public.social_media_artists(id) ON DELETE CASCADE,
  platform TEXT NOT NULL CHECK (platform IN ('instagram', 'tiktok', 'youtube')),
  post_id TEXT NOT NULL,
  post_url TEXT NOT NULL,
  post_date TIMESTAMP WITH TIME ZONE NOT NULL,
  caption TEXT,
  views INTEGER DEFAULT 0,
  likes INTEGER DEFAULT 0,
  comments INTEGER DEFAULT 0,
  shares INTEGER DEFAULT 0,
  saves INTEGER DEFAULT 0,
  engagement_rate NUMERIC GENERATED ALWAYS AS (
    CASE WHEN views > 0
      THEN ROUND(((likes + comments + saves) * 100.0 / views)::NUMERIC, 2)
      ELSE 0
    END
  ) STORED,
  top_comments JSONB DEFAULT '[]'::jsonb,
  audience_classification JSONB DEFAULT '{}'::jsonb,
  sentiment_summary TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(artist_id, platform, post_id)
);

-- social_media_comments table
CREATE TABLE public.social_media_comments (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  post_id UUID NOT NULL REFERENCES public.social_media_posts(id) ON DELETE CASCADE,
  author TEXT NOT NULL,
  text TEXT NOT NULL,
  sentiment TEXT CHECK (sentiment IN ('positive', 'neutral', 'negative')),
  audience_type TEXT CHECK (audience_type IN ('repeat_fan', 'new_audience', 'family_friend', 'bot', 'unknown')),
  is_repeat_commenter BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_social_media_posts_artist_date
  ON public.social_media_posts(artist_id, post_date DESC);

CREATE INDEX idx_social_media_posts_platform
  ON public.social_media_posts(platform);

CREATE INDEX idx_social_media_posts_engagement
  ON public.social_media_posts(engagement_rate DESC);

CREATE INDEX idx_social_media_comments_post_id
  ON public.social_media_comments(post_id);

CREATE INDEX idx_social_media_comments_sentiment
  ON public.social_media_comments(sentiment);

CREATE INDEX idx_social_media_comments_audience_type
  ON public.social_media_comments(audience_type);

-- Enable Row Level Security
ALTER TABLE public.social_media_artists ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.social_media_posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.social_media_comments ENABLE ROW LEVEL SECURITY;

-- RLS Policies: Allow all for now (can be restricted later)
CREATE POLICY "Allow all on social_media_artists"
  ON public.social_media_artists FOR ALL
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Allow all on social_media_posts"
  ON public.social_media_posts FOR ALL
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Allow all on social_media_comments"
  ON public.social_media_comments FOR ALL
  USING (true)
  WITH CHECK (true);

-- Create a view for analytics
CREATE VIEW public.post_analytics AS
SELECT
  a.directr_artist_id,
  a.instagram_handle,
  a.tiktok_handle,
  p.platform,
  COUNT(*) as total_posts,
  AVG(p.engagement_rate)::NUMERIC(5, 2) as avg_engagement_rate,
  MAX(p.engagement_rate)::NUMERIC(5, 2) as max_engagement_rate,
  AVG(p.likes) as avg_likes,
  AVG(p.comments) as avg_comments,
  SUM(p.views) as total_views,
  MAX(p.post_date) as last_post_date
FROM public.social_media_posts p
JOIN public.social_media_artists a ON p.artist_id = a.id
GROUP BY a.id, a.directr_artist_id, a.instagram_handle, a.tiktok_handle, p.platform;

-- Create a view for comment sentiment analysis
CREATE VIEW public.sentiment_analysis AS
SELECT
  p.artist_id,
  p.platform,
  c.sentiment,
  COUNT(*) as count,
  ROUND((COUNT(*) * 100.0 /
    (SELECT COUNT(*) FROM public.social_media_comments WHERE post_id = p.id))::NUMERIC, 2) as percentage
FROM public.social_media_comments c
JOIN public.social_media_posts p ON c.post_id = p.id
GROUP BY p.artist_id, p.platform, c.sentiment;
