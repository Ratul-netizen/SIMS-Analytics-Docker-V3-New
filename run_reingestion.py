#!/usr/bin/env python3
"""
Simple script to run reingestion and fetch more data for SIMS Analytics
"""

import requests
import time
import json

def run_reingestion():
    """Run the reingestion process to fetch more data"""
    
    print("🚀 Starting SIMS Analytics Reingestion...")
    print("=" * 50)
    
    # Step 1: Fetch latest news
    print("📰 Step 1: Fetching latest news from Exa...")
    try:
        response = requests.post('http://localhost:5000/api/fetch-latest', timeout=300)
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
        response = requests.post('http://localhost:5000/api/reanalyze-all', timeout=600)
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
        response = requests.get('http://localhost:5000/api/database-stats', timeout=30)
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
        response = requests.get('http://localhost:5000/api/health', timeout=5)
        if response.status_code == 200:
            health = response.json()
            if health.get('status') == 'healthy':
                return True
        return False
    except:
        return False

if __name__ == "__main__":
    print("🔧 SIMS Analytics Reingestion Script")
    print("=" * 40)
    
    # Check if server is running
    print("🔍 Checking if backend server is running...")
    if not check_server_status():
        print("❌ Backend server is not running!")
        print("💡 Please start the backend server first:")
        print("   cd backend")
        print("   python app.py")
        exit(1)
    
    print("✅ Backend server is running!")
    
    # Run reingestion
    success = run_reingestion()
    
    if success:
        print("\n✨ All done! Your dashboard should now have fresh data.")
    else:
        print("\n💥 Reingestion failed. Check the error messages above.")
        exit(1) 