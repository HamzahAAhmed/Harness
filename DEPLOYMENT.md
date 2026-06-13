# Journey Deployment Guide

This guide provides detailed instructions for deploying the Journey harness application to Render and other platforms.

## Table of Contents

1. [Render Deployment (Recommended)](#render-deployment-recommended)
2. [Environment Variables](#environment-variables)
3. [Deployment Verification](#deployment-verification)
4. [Troubleshooting](#troubleshooting)
5. [Alternative Platforms](#alternative-platforms)

## Render Deployment (Recommended)

Render is the recommended platform for deploying Journey because:

- Free tier available
- Automatic HTTPS
- Simple environment variable management
- Git-based deployments
- No credit card required for free tier

### Method 1: Blueprint Deployment (Easiest)

This method uses the included `render.yaml` file for automatic configuration.

1. **Prepare Your Repository**
   ```bash
   git add .
   git commit -m "Prepare for Render deployment"
   git push origin main
   ```

2. **Create Render Account**
   - Go to [https://render.com](https://render.com)
   - Sign up with GitHub (recommended) or email

3. **Deploy Using Blueprint**
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click **New** → **Blueprint**
   - Select your GitHub repository
   - Render will detect `render.yaml` automatically
   - Review the configuration:
     - Service name: `journey-harness`
     - Runtime: Python 3.11
     - Plan: Free
     - Environment variables: Pre-configured defaults
   - Click **Apply**

4. **Monitor Deployment**
   - Render will show build logs in real-time
   - Build typically takes 2-3 minutes
   - Wait for "Your service is live" message

5. **Access Your Application**
   - Your app will be available at: `https://journey-harness.onrender.com`
   - Or the custom URL shown in your Render dashboard

### Method 2: Manual Web Service Deployment

If you prefer manual configuration:

1. **Create New Web Service**
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click **New** → **Web Service**
   - Connect your GitHub repository
   - Select the Journey repository

2. **Configure Service**
   - **Name:** `journey-harness` (or your preferred name)
   - **Region:** Choose closest to your users
   - **Branch:** `main`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:server --bind 0.0.0.0:$PORT`

3. **Set Environment Variables**
   
   Add these in the "Environment" section:
   
   | Key | Value | Required |
   |-----|-------|----------|
   | `PYTHON_VERSION` | `3.11.0` | Yes |
   | `JOURNEY_WORKER` | `deterministic` | Yes |
   | `MAX_REPAIR_ATTEMPTS` | `1` | Yes |
   | `MAX_REFINEMENT_TURNS` | `3` | Yes |
   | `MAX_CANDIDATE_PLACES` | `12` | Yes |
   | `MAX_TRIP_DAYS` | `3` | Yes |
   | `OPENAI_MODEL` | `gpt-4o-mini` | No* |
   | `OPENAI_API_KEY` | `sk-...` | No* |
   
   *Required only if using OpenAI worker

4. **Deploy**
   - Click **Create Web Service**
   - Wait for deployment to complete

## Environment Variables

### Required Variables

These variables must be set for the application to function:

```env
JOURNEY_WORKER=deterministic
MAX_REPAIR_ATTEMPTS=1
MAX_REFINEMENT_TURNS=3
MAX_CANDIDATE_PLACES=12
MAX_TRIP_DAYS=3
```

### Optional Variables (OpenAI Integration)

To enable the OpenAI worker:

```env
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4o-mini
```

**Security Note:** Never commit your OpenAI API key to version control. Always set it through Render's environment variable interface.

### Updating Environment Variables on Render

1. Go to your service dashboard
2. Click **Environment** in the left sidebar
3. Add or modify variables
4. Click **Save Changes**
5. Render will automatically redeploy with new variables

## Deployment Verification

After deployment, verify your application is working correctly:

### 1. Check Service Health

- Visit your Render service URL
- You should see the Journey interface load
- Check browser console for errors (F12)

### 2. Test Deterministic Worker

1. Fill in trip details:
   - Destination: Austin, Texas
   - Dates: Any 1-3 day range
   - Travelers: 2
   - Budget: $500
   - Interests: Select 2-3 categories
   - Pace: Balanced

2. Select **Deterministic Journey Worker**

3. Click **Generate Itinerary**

4. Verify:
   - Itinerary appears with activities
   - Map shows markers
   - Diagnostics panel shows materials, guardrails, checkpoints
   - No errors in browser console

### 3. Test OpenAI Worker (If Configured)

1. Select **OpenAI Journey Worker**
2. Generate an itinerary
3. Verify OpenAI-generated content appears
4. Check diagnostics for worker activity

### 4. Test Refinement

1. After generating an itinerary
2. Enter refinement text: "Add more outdoor activities"
3. Click **Refine Itinerary**
4. Verify updated itinerary appears

### 5. Test Persistence

1. Generate and accept an itinerary
2. Click **Accept and Save**
3. Refresh the page
4. Verify saved trip appears in browser storage

## Troubleshooting

### Build Failures

**Problem:** Build fails with "No module named 'X'"

**Solution:**
- Verify `requirements.txt` includes all dependencies
- Check Python version is 3.11 or newer
- Review build logs for specific missing packages

**Problem:** Build fails with "Python version not found"

**Solution:**
- Add `PYTHON_VERSION=3.11.0` environment variable
- Or specify in `render.yaml`

### Runtime Errors

**Problem:** Application crashes on startup

**Solution:**
1. Check Render logs (Dashboard → Logs)
2. Verify all required environment variables are set
3. Ensure `app.py` exposes `server` object:
   ```python
   server = app.server
   ```

**Problem:** "Internal Server Error" when accessing app

**Solution:**
1. Check Render logs for Python tracebacks
2. Verify gunicorn is starting correctly
3. Test locally with same environment variables:
   ```bash
   gunicorn app:server --bind 0.0.0.0:8050
   ```

### OpenAI Integration Issues

**Problem:** OpenAI worker fails with authentication error

**Solution:**
- Verify `OPENAI_API_KEY` is set correctly in Render environment
- Check API key has not expired
- Ensure key starts with `sk-`
- Verify you have API credits available

**Problem:** OpenAI worker times out

**Solution:**
- Check OpenAI API status: [https://status.openai.com](https://status.openai.com)
- Try switching to `gpt-4o-mini` model (faster, cheaper)
- Increase timeout in Render settings if available

### Map Not Displaying

**Problem:** MapLibre map doesn't render

**Solution:**
1. Check browser console for JavaScript errors
2. Verify `assets/` directory is included in deployment
3. Ensure `00-maplibre-gl.js` and `00-maplibre-gl.css` are present
4. Check that GeoJSON data is being generated

### Performance Issues

**Problem:** Application is slow on Render free tier

**Solution:**
- Free tier instances sleep after 15 minutes of inactivity
- First request after sleep takes 30-60 seconds (cold start)
- Consider upgrading to paid tier for always-on instances
- Use deterministic worker for faster responses

## Alternative Platforms

Journey can be deployed to any platform supporting Python WSGI applications.

### Heroku

```bash
# Procfile already included
git push heroku main
```

Set environment variables:
```bash
heroku config:set JOURNEY_WORKER=deterministic
heroku config:set MAX_REPAIR_ATTEMPTS=1
# ... other variables
```

### Railway

1. Connect GitHub repository
2. Railway auto-detects Python
3. Set environment variables in dashboard
4. Deploy

### Google Cloud Run

```bash
# Create Dockerfile
gcloud run deploy journey-harness \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### AWS Elastic Beanstalk

1. Create `application.py`:
   ```python
   from app import server as application
   ```

2. Deploy:
   ```bash
   eb init -p python-3.11 journey-harness
   eb create journey-env
   eb deploy
   ```

### DigitalOcean App Platform

1. Connect repository
2. Configure:
   - Type: Web Service
   - Build Command: `pip install -r requirements.txt`
   - Run Command: `gunicorn app:server --bind 0.0.0.0:$PORT`
3. Set environment variables
4. Deploy

## Production Considerations

### Security

- ✅ Never commit API keys to version control
- ✅ Use environment variables for all secrets
- ✅ Enable HTTPS (automatic on Render)
- ✅ Review Render security settings
- ✅ Regularly rotate API keys

### Monitoring

- Monitor Render logs for errors
- Set up Render alerts for service downtime
- Track OpenAI API usage and costs
- Monitor application performance metrics

### Scaling

- Free tier: 512 MB RAM, shared CPU
- Paid tiers: More RAM, dedicated CPU, faster cold starts
- Consider upgrading if serving multiple concurrent users

### Cost Management

- Render free tier: $0/month (with limitations)
- OpenAI API: Pay per token usage
- Monitor OpenAI usage in dashboard
- Set usage limits to prevent unexpected charges

## Support

For deployment issues:

1. Check Render documentation: [https://render.com/docs](https://render.com/docs)
2. Review application logs in Render dashboard
3. Test locally with same configuration
4. Check GitHub repository issues
5. Review `HARNESS.md` for architecture details

## Quick Reference

### Render Dashboard URLs

- Dashboard: [https://dashboard.render.com](https://dashboard.render.com)
- Docs: [https://render.com/docs](https://render.com/docs)
- Status: [https://status.render.com](https://status.render.com)

### Essential Commands

```bash
# Local testing
python app.py

# Production testing
gunicorn app:server --bind 0.0.0.0:8050

# Run tests
pytest

# Check code quality
ruff check .

# Git deployment
git add .
git commit -m "Deploy to Render"
git push origin main
```

### Default Configuration

```yaml
Service: journey-harness
Runtime: Python 3.11
Plan: Free
Build: pip install -r requirements.txt
Start: gunicorn app:server --bind 0.0.0.0:$PORT
Worker: deterministic (no API key needed)
```
