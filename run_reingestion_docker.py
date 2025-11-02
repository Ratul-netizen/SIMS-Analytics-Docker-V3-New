#!/usr/bin/env python3
"""
Docker-compatible version of reingestion script
Works both from host and inside Docker containers
"""

import requests
import time
import json
import os
import sys

# Get backend URL from environment or use sensible defaults
def get_backend_url():
    """Determine backend URL based on environment"""
    # Check if running in Docker (use service name)
    if os.path.exists('/.dockerenv'):
        return os.getenv('BACKEND_URL', 'http://backend:5000')
    # Running on host, use localhost
    return os.getenv('BACKEND_URL', 'http://localhost:5000')

BACKEND_URL = get_backend_url()

def run_reingestion():
    """Run the reingestion process to fetch more data"""
    
    print("🚀 Starting SIMS Analytics Reingestion...")
    print(f"🔗 Connecting to: {BACKEND_URL}")
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
            print(f"   Response: {response.text[:200]}")
            return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection Error: Cannot reach backend at {BACKEND_URL}")
        print(f"   Make sure the backend container is running: docker-compose ps")
        return False
    except Exception as e:
        print(f"❌ Error fetching latest news: {e}")
        return False
    
    # Step 2: Reanalyze all articles with Gemma
    print("\n🔍 Step 2: Reanalyzing all articles with Gemma...")
    print("⏳ This may take several minutes...")
    try:
        response = requests.post(f'{BACKEND_URL}/api/reanalyze-all', timeout=600)
        if response.status_code == 200:
            result = response.json()
            stats = result.get('stats', {})
            print(f"✅ Success: {result.get('message', 'Reanalysis complete')}")
            print(f"   📊 Stats: {stats.get('processed', 0)} processed, {stats.get('failed', 0)} failed, {stats.get('skipped', 0)} skipped")
        else:
            print(f"❌ Error: HTTP {response.status_code}")
            print(f"   Response: {response.text[:200]}")
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
    except requests.exceptions.ConnectionError:
        return False
    except Exception as e:
        print(f"⚠️  Warning: Health check error: {e}")
        return False

if __name__ == "__main__":
    print("🔧 SIMS Analytics Reingestion Script")
    print("=" * 40)
    
    # Check if server is running
    print(f"🔍 Checking if backend server is running at {BACKEND_URL}...")
    if not check_server_status():
        print("❌ Backend server is not running or not healthy!")
        print("\n💡 Troubleshooting:")
        print("   1. Start Docker containers: docker-compose up -d")
        print("   2. Check backend logs: docker-compose logs backend")
        print("   3. Verify health: curl http://localhost:5000/api/health")
        print(f"   4. Or set BACKEND_URL env var if different: export BACKEND_URL=http://your-backend:5000")
        sys.exit(1)
    
    print("✅ Backend server is running!")
    
    # Run reingestion
    success = run_reingestion()
    
    if success:
        print("\n✨ All done! Your dashboard should now have fresh data.")
        sys.exit(0)
    else:
        print("\n💥 Reingestion failed. Check the error messages above.")
        sys.exit(1)

