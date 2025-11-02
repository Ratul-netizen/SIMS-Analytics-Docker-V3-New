# How to Run `run_reingestion.py` in Docker

This guide explains multiple ways to run the reingestion script with your Docker setup.

## Analysis

The `run_reingestion.py` script is a **client-side script** that makes HTTP requests to your Flask backend API:
- `POST /api/fetch-latest` - Fetches new news articles
- `POST /api/reanalyze-all` - Reanalyzes all articles with Gemini
- `GET /api/database-stats` - Gets database statistics
- `GET /api/health` - Checks if backend is running

---

## Option 1: Run from Host Machine (Recommended)

**When to use:** Simplest approach, works when backend port is exposed.

### Prerequisites
Ensure you have Python 3 and `requests` installed on your host machine:
```bash
pip install requests
```

### Steps
1. Start your Docker containers:
   ```bash
   docker-compose up -d
   ```

2. Wait for backend to be healthy (check logs):
   ```bash
   docker-compose logs backend
   ```

3. Run the script from the project root:
   ```bash
   python run_reingestion.py
   ```

The script connects to `http://localhost:5000`, which works because the backend container exposes port 5000.

---

## Option 2: Run Inside Backend Container

**When to use:** When you want to run it in the same environment as the backend.

### Steps
1. Copy the script into the backend container:
   ```bash
   docker cp run_reingestion.py sims_backend:/app/run_reingestion.py
   ```

2. Install `requests` in the container (if not already installed):
   ```bash
   docker exec sims_backend pip install requests
   ```

3. Run the script inside the container:
   ```bash
   docker exec -it sims_backend python /app/run_reingestion.py
   ```

**Note:** The script will connect to `http://localhost:5000` since it's running in the same container as the Flask server.

---

## Option 3: Run as Docker Service (Docker-Native Approach)

**When to use:** Most Docker-native approach, runs as a separate container.

### Create a Docker wrapper script
First, let's create a version that uses Docker networking:

1. Create `run_reingestion_docker.py`:
```python
#!/usr/bin/env python3
"""
Docker-compatible version of reingestion script
Uses Docker service name instead of localhost
"""

import requests
import time
import json
import os

# Get backend URL from environment or use Docker service name
BACKEND_URL = os.getenv('BACKEND_URL', 'http://backend:5000')

def run_reingestion():
    """Run the reingestion process to fetch more data"""
    
    print("🚀 Starting SIMS Analytics Reingestion...")
    print(f"🔗 Backend URL: {BACKEND_URL}")
    print("=" * 50)
    
    # Step 1: Fetch latest news
    print("📰 Step 1: Fetching latest news from Exa...")
    try:
        response = requests.post(f'{BACKEND_URL}/api/fetch-latest', timeout=300)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success: {result.get('message', 'Fetched latest news')}")
        else:
            print(f"❌ Error: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error fetching latest news: {e}")
        return False
    
    # Step 2: Reanalyze all articles with Gemma
    print("\n🔍 Step 2: Reanalyzing all articles with Gemma...")
    try:
        response = requests.post(f'{BACKEND_URL}/api/reanalyze-all', timeout=600)
        if response.status_code == 200:
            result = response.json()
            stats = result.get('stats', {})
            print(f"✅ Success: {result.get('message', 'Reanalysis complete')}")
            print(f"   📊 Stats: {stats.get('processed', 0)} processed, {stats.get('failed', 0)} failed, {stats.get('skipped', 0)} skipped")
        else:
            print(f"❌ Error: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error reanalyzing articles: {e}")
        return False
    
    # Step 3: Get updated database stats
    print("\n📊 Step 3: Getting updated database statistics...")
    try:
        response = requests.get(f'{BACKEND_URL}/api/database-stats', timeout=30)
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Database Stats:")
            print(f"   📄 Total Articles: {stats.get('total_articles', 0)}")
            print(f"   🇮🇳 Indian Sources: {stats.get('articles_by_source_type', {}).get('indian_sources', 0)}")
            print(f"   🇧🇩 Bangladeshi Sources: {stats.get('articles_by_source_type', {}).get('bangladeshi_sources', 0)}")
            print(f"   🌍 International Sources: {stats.get('articles_by_source_type', {}).get('international_sources', 0)}")
            print(f"   📝 Articles with Summary: {stats.get('content_stats', {}).get('articles_with_summary', 0)}")
        else:
            print(f"❌ Error getting stats: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Error getting database stats: {e}")
    
    print("\n🎉 Reingestion process completed!")
    print("💡 You can now refresh your dashboard to see the new data.")
    return True

def check_server_status():
    """Check if the backend server is running"""
    try:
        response = requests.get(f'{BACKEND_URL}/api/health', timeout=5)
        if response.status_code == 200:
            health = response.json()
            if health.get('status') == 'healthy':
                return True
        return False
    except:
        return False

if __name__ == "__main__":
    print("🔧 SIMS Analytics Reingestion Script (Docker)")
    print("=" * 40)
    
    # Check if server is running
    print("🔍 Checking if backend server is running...")
    if not check_server_status():
        print(f"❌ Backend server is not running at {BACKEND_URL}!")
        print("💡 Please ensure Docker containers are running:")
        print("   docker-compose up -d")
        exit(1)
    
    print("✅ Backend server is running!")
    
    # Run reingestion
    success = run_reingestion()
    
    if success:
        print("\n✨ All done! Your dashboard should now have fresh data.")
    else:
        print("\n💥 Reingestion failed. Check the error messages above.")
        exit(1)
```

2. Add to `docker-compose.yml`:
```yaml
  reingestion:
    build:
      context: .
      dockerfile: Dockerfile.reingestion
    container_name: sims_reingestion
    environment:
      - BACKEND_URL=http://backend:5000
    depends_on:
      backend:
        condition: service_healthy
    networks:
      - sims_network
    profiles:
      - tools
```

3. Create `Dockerfile.reingestion`:
```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install requests
RUN pip install requests

# Copy the reingestion script
COPY run_reingestion_docker.py /app/run_reingestion.py

CMD ["python", "run_reingestion.py"]
```

4. Run as a one-off container:
```bash
docker-compose run --rm reingestion
```

---

## Option 4: Add as Flask CLI Command (Recommended for Production)

**When to use:** Best for automation and scheduled tasks.

### Implementation
Add this to your `backend/app.py`:

```python
@app.cli.command('reingest')
def reingest():
    """Run the complete reingestion process"""
    from flask import current_app
    
    print("🚀 Starting SIMS Analytics Reingestion...")
    print("=" * 50)
    
    # Step 1: Fetch latest news
    print("📰 Step 1: Fetching latest news from Exa...")
    # Call your existing fetch-exa command logic
    # ... (implement using your existing functions)
    
    # Step 2: Reanalyze all articles
    print("\n🔍 Step 2: Reanalyzing all articles with Gemma...")
    # Call your existing reanalyze-all logic
    # ... (implement using your existing functions)
    
    print("\n🎉 Reingestion process completed!")
```

### Usage:
```bash
# From host machine
docker exec sims_backend flask reingest

# Or as a one-off container
docker-compose run --rm backend flask reingest
```

---

## Quick Comparison

| Option | Pros | Cons |
|--------|------|------|
| **Option 1: Host** | Simplest, no Docker changes needed | Requires Python on host |
| **Option 2: Backend Container** | Same environment as backend | Manual file copying |
| **Option 3: Docker Service** | Most Docker-native | Requires Dockerfile changes |
| **Option 4: Flask CLI** | Best for automation | Requires code changes |

---

## Recommended Approach

For **quick one-time runs**: Use **Option 1** (run from host)

For **production/automation**: Use **Option 4** (Flask CLI command)

For **scheduled tasks**: Add to your cron job or use Docker's built-in scheduler.

---

## Troubleshooting

### Script can't connect to backend
- Check if backend container is running: `docker-compose ps`
- Verify port 5000 is exposed: `docker-compose port backend 5000`
- Check backend health: `curl http://localhost:5000/api/health`

### Script times out
- Increase timeout values in the script (currently 300s for fetch, 600s for reanalyze)
- Check backend logs: `docker-compose logs backend`

### Missing dependencies
- For Option 1: Install `requests` on host: `pip install requests`
- For Option 2: Install in container: `docker exec sims_backend pip install requests`

