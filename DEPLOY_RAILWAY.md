# Deploying Bridging Brain to Railway

## Quick Start (5 minutes)

### Step 1: Create Railway Account
1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub (recommended) or email

### Step 2: Deploy from GitHub
1. Push this folder to a GitHub repository
2. In Railway dashboard, click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose your repository

### Step 3: Set Environment Variables
In Railway dashboard → Your project → **Variables** tab:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### Step 4: Get Your URL
1. Go to **Settings** → **Networking**
2. Click **"Generate Domain"**
3. Your app will be live at `https://your-app.up.railway.app`

---

## Alternative: Deploy via Railway CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Set environment variable
railway variables set ANTHROPIC_API_KEY=sk-ant-your-key-here

# Deploy
railway up
```

---

## Files Included for Railway

| File | Purpose |
|------|---------|
| `Procfile` | Tells Railway how to start the app |
| `requirements.txt` | Python dependencies |
| `railway.json` | Railway-specific config |
| `.env.example` | Template for environment variables |

---

## Database Persistence

The `lenders.db` SQLite file is included in the deployment. For production with frequent updates, consider:

1. **Railway Volumes** (recommended for SQLite)
   - In Railway dashboard → Add Volume
   - Mount path: `/app/data`
   - Update code to use `/app/data/lenders.db`

2. **PostgreSQL** (for multi-instance scaling)
   - Railway offers one-click Postgres
   - Would require schema migration

For beta testing, the included SQLite file works fine.

---

## Costs

Railway offers:
- **Free tier**: $5/month credit (enough for beta testing)
- **Hobby**: $5/month
- **Pro**: $20/month (for production)

---

## Troubleshooting

### "Application failed to respond"
- Check Variables tab for `ANTHROPIC_API_KEY`
- Check Deployments → View Logs

### "Module not found"
- Ensure `requirements.txt` is in root directory
- Check for typos in package names

### Database not updating
- You'll need to redeploy to update `lenders.db`
- Or set up a volume for persistent storage

---

## After Deployment

Your Bridging Brain will be live at:
```
https://your-app-name.up.railway.app
```

Share this URL with beta testers!
