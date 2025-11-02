# Timeout Fixes Summary

## Issues Fixed

### 1. ✅ Step 1 Timeout (Fetch Latest News)
**Problem**: Timing out after 5 minutes (300s)
- **Root Cause**: Processing 25 articles with Gemini API takes 10-15 minutes
- **Fix Applied**: 
  - Increased default timeout to **15 minutes** (900s)
  - Made configurable via `FETCH_TIMEOUT` environment variable
  - Added specific timeout error handling with troubleshooting tips

### 2. ✅ Step 2 Timeout (Reanalyze All)
**Problem**: Timing out after 10 minutes (600s)  
- **Root Cause**: Reanalyzing all articles sequentially can take 30-60 minutes
- **Fix Applied**:
  - Increased default timeout to **1 hour** (3600s)
  - Made configurable via `REANALYZE_TIMEOUT` environment variable
  - Added specific timeout error handling

## Configuration

### Default Timeouts
- **Step 1 (Fetch)**: 15 minutes (900 seconds)
- **Step 2 (Reanalyze)**: 1 hour (3600 seconds)

### Custom Timeouts

**For Step 1 (if you have slow API responses):**
```bash
export FETCH_TIMEOUT=1800  # 30 minutes
python run_reingestion_docker.py
```

**For Step 2 (if you have many articles):**
```bash
export REANALYZE_TIMEOUT=7200  # 2 hours
python run_reingestion_docker.py
```

**Both:**
```bash
export FETCH_TIMEOUT=1800      # 30 minutes
export REANALYZE_TIMEOUT=7200  # 2 hours
python run_reingestion_docker.py
```

## Time Estimates

| Operation | Articles | Estimated Time | Recommended Timeout |
|-----------|----------|----------------|---------------------|
| **Fetch Latest** | 25 new | 10-15 minutes | 900s (15 min) |
| **Reanalyze All** | < 50 | 10-20 minutes | 1800s (30 min) |
| **Reanalyze All** | 50-100 | 20-40 minutes | 3600s (1 hour) |
| **Reanalyze All** | 100-200 | 40-90 minutes | 7200s (2 hours) |
| **Reanalyze All** | 200+ | 90+ minutes | 10800s (3 hours) |

## Troubleshooting

### If Step 1 Times Out

1. **Check if backend is still processing:**
   ```bash
   docker-compose logs -f backend
   ```
   Look for "Processing NEW item" messages - if you see them, backend is working!

2. **Increase timeout:**
   ```bash
   export FETCH_TIMEOUT=1800  # 30 minutes
   python run_reingestion_docker.py
   ```

3. **Check API status:**
   - Exa API might be slow
   - Gemini API might be rate-limited
   - Check backend logs for specific errors

### If Step 2 Times Out

1. **Check backend logs** to see progress:
   ```bash
   docker-compose logs backend | grep "Reanalyzing article"
   ```

2. **Increase timeout based on article count:**
   ```bash
   # For 100+ articles
   export REANALYZE_TIMEOUT=7200
   python run_reingestion_docker.py
   ```

3. **Check if it's still processing:**
   ```bash
   # Check database stats to see if articles are being processed
   curl http://localhost:5000/api/database-stats
   ```

## What Happens on Timeout?

**Important**: Even if the script times out, **the backend may still be processing**!

- The timeout is for the HTTP request, not the backend process
- Backend continues processing in the background
- Check backend logs to confirm if processing is still ongoing
- New articles will appear in the database when processing completes

## Best Practices

1. **Run during off-peak hours** - API response times are better
2. **Monitor backend logs** in another terminal:
   ```bash
   docker-compose logs -f backend
   ```
3. **Check database stats** to verify articles are being added:
   ```bash
   curl http://localhost:5000/api/database-stats | python -m json.tool
   ```
4. **Be patient** - Gemini API processing can be slow but it's working!

## Summary

✅ **Both timeouts increased** to handle realistic processing times  
✅ **Configurable** via environment variables  
✅ **Better error messages** with troubleshooting guidance  
✅ **Timeout doesn't stop backend** - processing continues even if script times out

The script should now complete successfully for normal use cases!

