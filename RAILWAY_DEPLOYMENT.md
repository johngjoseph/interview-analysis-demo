# Railway Deployment Guide

## Prerequisites

1. Railway account (sign up at https://railway.app)
2. GitHub repository with your code
3. Google OAuth credentials

## Environment Variables

Set these in Railway's dashboard under your project → Variables:

### Required:
- `FLASK_SECRET` - A random secret key for Flask sessions (generate with: `python -c "import secrets; print(secrets.token_hex(32))"`)
- `GOOGLE_CLIENT_ID` - Your Google OAuth Client ID
- `GOOGLE_CLIENT_SECRET` - Your Google OAuth Client Secret
- `OPENAI_API_KEY` - Your OpenAI API key (for AI scraping)

### Optional:
- `JINA_API_KEY` - Jina Reader API key (for faster scraping, 200 req/min vs 20 req/min)
- `DATABASE_URL` - Automatically set by Railway when you add a PostgreSQL database

## Deployment Steps

1. **Connect Repository**
   - In Railway, click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository

2. **Add PostgreSQL Database**
   - In Railway dashboard, click "+ New" → "Database" → "Add PostgreSQL"
   - Railway will automatically set `DATABASE_URL`

3. **Set Environment Variables**
   - Go to your service → Variables tab
   - Add all required environment variables listed above

4. **Deploy**
   - Railway will automatically detect the `Procfile` and deploy
   - The app will be available at your Railway-provided URL

5. **Update Google OAuth Redirect URI**
   - Go to Google Cloud Console → APIs & Services → Credentials
   - Add your Railway URL to authorized redirect URIs:
     - `https://your-app-name.up.railway.app/auth/callback`

## Post-Deployment

1. **Initialize Database**
   - The database tables are created automatically on first deploy
   - Visit `/settings` to add target companies
   - Visit `/` (Admin section) to seed mock data or run scraper

2. **Test Authentication**
   - Try logging in with Google OAuth
   - If it fails, check the redirect URI matches exactly

## Troubleshooting

- **Database connection errors**: Check that PostgreSQL is added and `DATABASE_URL` is set
- **OAuth errors**: Verify redirect URI matches exactly (including https://)
- **Port binding errors**: Railway sets `$PORT` automatically, Procfile handles this
- **Import errors**: Check `requirements.txt` includes all dependencies

## Files Included

- `Procfile` - Tells Railway how to run the app
- `requirements.txt` - Python dependencies (Railway auto-detects Python version from this)
- `.gitignore` - Excludes local files from git

