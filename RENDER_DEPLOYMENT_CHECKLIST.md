# Render Deployment Checklist

Use this checklist to deploy Journey to Render quickly and correctly.

## Pre-Deployment Checklist

- [ ] All code is committed to Git
- [ ] Repository is pushed to GitHub
- [ ] `.env` file is NOT committed (check `.gitignore`)
- [ ] `render.yaml` exists in repository root
- [ ] `Procfile` exists with correct gunicorn command
- [ ] `requirements.txt` includes all dependencies
- [ ] `app.py` exposes `server` object

## Deployment Steps

### Option A: Blueprint Deployment (Recommended)

- [ ] Go to [Render Dashboard](https://dashboard.render.com/)
- [ ] Click **New** → **Blueprint**
- [ ] Connect your GitHub account (if not already connected)
- [ ] Select the Journey repository
- [ ] Verify Render detects `render.yaml`
- [ ] Review auto-configured settings:
  - [ ] Service name: `journey-harness`
  - [ ] Runtime: Python 3.11
  - [ ] Build command: `pip install -r requirements.txt`
  - [ ] Start command: `gunicorn app:server --bind 0.0.0.0:$PORT`
  - [ ] Environment variables are pre-configured
- [ ] Click **Apply** to deploy
- [ ] Wait for build to complete (2-3 minutes)
- [ ] Note your service URL (e.g., `https://journey-harness.onrender.com`)

### Option B: Manual Web Service Deployment

- [ ] Go to [Render Dashboard](https://dashboard.render.com/)
- [ ] Click **New** → **Web Service**
- [ ] Connect GitHub repository
- [ ] Configure service:
  - [ ] Name: `journey-harness`
  - [ ] Region: (choose closest to you)
  - [ ] Branch: `main`
  - [ ] Runtime: Python 3
  - [ ] Build Command: `pip install -r requirements.txt`
  - [ ] Start Command: `gunicorn app:server --bind 0.0.0.0:$PORT`
- [ ] Add environment variables:
  - [ ] `PYTHON_VERSION` = `3.11.0`
  - [ ] `JOURNEY_WORKER` = `deterministic`
  - [ ] `MAX_REPAIR_ATTEMPTS` = `1`
  - [ ] `MAX_REFINEMENT_TURNS` = `3`
  - [ ] `MAX_CANDIDATE_PLACES` = `12`
  - [ ] `MAX_TRIP_DAYS` = `3`
  - [ ] `OPENAI_MODEL` = `gpt-4o-mini` (optional)
  - [ ] `OPENAI_API_KEY` = `sk-...` (optional, for OpenAI worker)
- [ ] Click **Create Web Service**
- [ ] Wait for deployment to complete

## Post-Deployment Verification

### Basic Health Check

- [ ] Visit your Render service URL
- [ ] Page loads without errors
- [ ] Journey interface is visible
- [ ] No errors in browser console (F12)

### Functional Testing

- [ ] Test Deterministic Worker:
  - [ ] Fill in trip form (Austin, Texas, 1-3 days)
  - [ ] Select "Deterministic Journey Worker"
  - [ ] Click "Generate Itinerary"
  - [ ] Itinerary appears with activities
  - [ ] Map displays with markers
  - [ ] Diagnostics panel shows data

- [ ] Test Refinement:
  - [ ] Enter refinement text
  - [ ] Click "Refine Itinerary"
  - [ ] Updated itinerary appears

- [ ] Test Persistence:
  - [ ] Click "Accept and Save"
  - [ ] Refresh page
  - [ ] Saved trip persists

- [ ] Test OpenAI Worker (if API key configured):
  - [ ] Select "OpenAI Journey Worker"
  - [ ] Generate itinerary
  - [ ] Verify AI-generated content

### Diagnostics Check

- [ ] Expand diagnostics panel
- [ ] Verify sections visible:
  - [ ] Materials
  - [ ] Guardrails
  - [ ] Checkpoints
  - [ ] Alarms
  - [ ] Worker Activity
  - [ ] Trace Events

## Troubleshooting

If deployment fails, check:

- [ ] Render build logs for errors
- [ ] All environment variables are set correctly
- [ ] Python version is 3.11 or newer
- [ ] `requirements.txt` has all dependencies
- [ ] `app.py` exposes `server` object
- [ ] No syntax errors in code

If application crashes:

- [ ] Check Render logs (Dashboard → Logs)
- [ ] Verify environment variables
- [ ] Test locally with: `gunicorn app:server --bind 0.0.0.0:8050`

If OpenAI worker fails:

- [ ] Verify `OPENAI_API_KEY` is set in Render (not in code)
- [ ] Check API key is valid and has credits
- [ ] Verify key starts with `sk-`

## Optional: Enable OpenAI Worker

To use the OpenAI worker after initial deployment:

- [ ] Go to Render service dashboard
- [ ] Click **Environment** in sidebar
- [ ] Add/update variables:
  - [ ] `OPENAI_API_KEY` = `sk-proj-...` (your actual key)
  - [ ] `OPENAI_MODEL` = `gpt-4o-mini`
- [ ] Click **Save Changes**
- [ ] Wait for automatic redeployment
- [ ] Test OpenAI worker in application

## Success Criteria

Your deployment is successful when:

- ✅ Service is live and accessible via HTTPS
- ✅ Deterministic worker generates valid itineraries
- ✅ Map displays activity markers correctly
- ✅ Diagnostics show harness pillars (materials, guardrails, checkpoints, alarms)
- ✅ Refinement updates itineraries
- ✅ Persistence works across page refreshes
- ✅ No errors in browser console or Render logs
- ✅ (Optional) OpenAI worker generates itineraries when configured

## Quick Links

- **Render Dashboard**: https://dashboard.render.com/
- **Render Docs**: https://render.com/docs
- **Render Status**: https://status.render.com/
- **OpenAI Status**: https://status.openai.com/
- **Full Deployment Guide**: See `DEPLOYMENT.md`
- **Architecture Details**: See `HARNESS.md`

## Estimated Timeline

- Blueprint deployment: 3-5 minutes
- Manual deployment: 5-10 minutes
- Build time: 2-3 minutes
- First cold start: 30-60 seconds
- Subsequent requests: < 1 second

## Cost

- **Render Free Tier**: $0/month
  - 512 MB RAM
  - Shared CPU
  - Sleeps after 15 min inactivity
  - 750 hours/month free

- **OpenAI API** (if used):
  - gpt-4o-mini: ~$0.15 per 1M input tokens
  - Pay per use
  - Set usage limits in OpenAI dashboard

## Next Steps After Deployment

- [ ] Share your deployment URL
- [ ] Monitor Render logs for any issues
- [ ] Set up Render alerts (optional)
- [ ] Monitor OpenAI usage (if applicable)
- [ ] Consider upgrading to paid tier for production use
- [ ] Review security settings
- [ ] Set up custom domain (optional, paid feature)

---

**Need Help?**

- See `DEPLOYMENT.md` for detailed troubleshooting
- Check Render documentation
- Review application logs
- Test locally first
