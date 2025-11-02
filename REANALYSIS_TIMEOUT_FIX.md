# Fixing Reanalysis Timeout Issues

## Problem

The `run_reingestion.py` script was timing out during Step 2 (Reanalyze all articles) after 10 minutes (600 seconds). This happens because:

- The `/api/reanalyze-all` endpoint processes **all articles sequentially**
- Each article requires **Gemini API calls** which can be slow (2-5 seconds per article)
- If you have 200+ articles, this easily exceeds 10 minutes

## Solution

The script has been updated with:

1. **Increased default timeout**: Now 1 hour (3600 seconds) instead of 10 minutes
2. **Configurable timeout**: Set via `REANALYZE_TIMEOUT` environment variable
3. **Better error handling**: Distinguishes between timeout, connection errors, and other issues
4. **Helpful troubleshooting**: Provides clear guidance when timeout occurs

## Usage

### Basic Usage (1 hour timeout)
```bash
python run_reingestion_docker.py
```

### Custom Timeout (2 hours example)
```bash
export REANALYZE_TIMEOUT=7200  # 2 hours in seconds
python run_reingestion_docker.py
```

### Even Longer (for very large datasets)
```bash
export REANALYZE_TIMEOUT=10800  # 3 hours
python run_reingestion_docker.py
```

## What to Do If It Still Times Out

### Option 1: Check if Backend is Still Working
Even if the script times out, the backend might still be processing. Check:
```bash
# Watch backend logs
docker-compose logs -f backend

# Check database stats
curl http://localhost:5000/api/database-stats
```

### Option 2: Increase Timeout Further
```bash
# Set to 3 hours (for 500+ articles)
export REANALYZE_TIMEOUT=10800
python run_reingestion_docker.py
```

### Option 3: Process in Batches (Backend Modification Needed)
Modify the backend to process articles in smaller batches and return progress. This requires code changes to `backend/app.py`.

### Option 4: Run Reanalysis Separately
Instead of running the full reingestion, run reanalysis separately and monitor:

```bash
# Start reanalysis in background (via curl)
curl -X POST http://localhost:5000/api/reanalyze-all &

# Monitor backend logs
docker-compose logs -f backend

# Check progress periodically
watch -n 60 'curl -s http://localhost:5000/api/database-stats | jq'
```

## Estimated Time Requirements

| Articles | Estimated Time | Recommended Timeout |
|----------|---------------|---------------------|
| < 50     | 5-10 minutes  | 600s (10 min)      |
| 50-100   | 10-20 minutes | 1800s (30 min)     |
| 100-200  | 20-40 minutes | 3600s (1 hour)     |
| 200-500  | 40-90 minutes | 7200s (2 hours)    |
| 500+     | 90+ minutes   | 10800s (3 hours)   |

*Note: Times are estimates and depend on Gemini API response times*

## Monitoring Progress

While reanalysis is running, you can monitor progress:

```bash
# In one terminal: watch backend logs
docker-compose logs -f backend | grep -i "reanalyze\|processed\|article"

# In another terminal: check database stats every minute
watch -n 60 'curl -s http://localhost:5000/api/database-stats | python -m json.tool'
```

## Alternative: Async Processing

For production use, consider modifying the backend to:
1. Process articles in background tasks (using Celery or similar)
2. Return a job ID immediately
3. Provide a status endpoint to check progress
4. This prevents timeout issues entirely

## Summary

- ✅ Default timeout increased to 1 hour
- ✅ Timeout is configurable via environment variable
- ✅ Better error messages with troubleshooting tips
- ✅ Script provides guidance when timeout occurs

The timeout issue should now be resolved for most use cases!

