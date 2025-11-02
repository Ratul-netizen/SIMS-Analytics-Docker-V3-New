#!/usr/bin/env python3
"""
Diagnostic script to check why ingestion might not be fetching new data
"""

import requests
import os
import sys

def get_backend_url():
    """Determine backend URL based on environment"""
    if os.path.exists('/.dockerenv'):
        return os.getenv('BACKEND_URL', 'http://backend:5000')
    return os.getenv('BACKEND_URL', 'http://localhost:5000')

BACKEND_URL = get_backend_url()

def check_backend():
    """Check if backend is running"""
    try:
        response = requests.get(f'{BACKEND_URL}/api/health', timeout=5)
        if response.status_code == 200:
            return True
        return False
    except:
        return False

def get_database_stats():
    """Get database statistics"""
    try:
        response = requests.get(f'{BACKEND_URL}/api/database-stats', timeout=30)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def check_recent_articles():
    """Check for recent articles that might block ingestion"""
    try:
        # We can't directly query, but we can get all articles and filter by date
        response = requests.get(f'{BACKEND_URL}/api/articles?limit=1000', timeout=30)
        if response.status_code == 200:
            articles = response.json()
            
            from datetime import datetime, timedelta
            recent_cutoff = datetime.now() - timedelta(hours=2)
            
            recent_count = 0
            for article in articles:
                if article.get('publishedDate'):
                    try:
                        pub_date = datetime.fromisoformat(article['publishedDate'].replace('Z', '+00:00'))
                        if pub_date >= recent_cutoff:
                            recent_count += 1
                    except:
                        pass
            
            return recent_count, len(articles)
        return None, None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None, None

def main():
    print("🔍 SIMS Analytics Ingestion Diagnostic")
    print("=" * 50)
    
    # Check backend
    print(f"\n1. Checking backend at {BACKEND_URL}...")
    if not check_backend():
        print("❌ Backend is not running!")
        print("   Start it with: docker-compose up -d")
        sys.exit(1)
    print("✅ Backend is running")
    
    # Get database stats
    print("\n2. Checking database statistics...")
    stats = get_database_stats()
    if stats:
        print(f"   📄 Total Articles: {stats.get('total_articles', 0)}")
        print(f"   📝 Articles with Summary: {stats.get('content_stats', {}).get('articles_with_summary', 0)}")
        
        by_source = stats.get('articles_by_source_type', {})
        print(f"   🇮🇳 Indian Sources: {by_source.get('indian_sources', 0)}")
        print(f"   🇧🇩 Bangladeshi Sources: {by_source.get('bangladeshi_sources', 0)}")
        print(f"   🌍 International Sources: {by_source.get('international_sources', 0)}")
    else:
        print("❌ Could not get database stats")
    
    # Check recent articles (this might be blocking ingestion)
    print("\n3. Checking recent articles (last 2 hours)...")
    recent_count, total_count = check_recent_articles()
    if recent_count is not None:
        print(f"   ⏰ Recent articles (last 2 hours): {recent_count}")
        print(f"   📊 Total articles checked: {total_count}")
        
        if recent_count > 10:
            print(f"\n⚠️  WARNING: Found {recent_count} articles in the last 2 hours!")
            print("   🚫 This will BLOCK new ingestion!")
            print("   📋 The backend checks for >10 recent articles and skips ingestion")
            print("   💡 Solutions:")
            print("      1. Wait 2+ hours and try again")
            print("      2. Modify backend/app.py to change the threshold")
            print("      3. Delete some recent articles if they're duplicates")
        else:
            print(f"   ✅ Recent count ({recent_count}) is below threshold (10)")
    else:
        print("   ⚠️  Could not check recent articles")
    
    # Check environment variables
    print("\n4. Checking environment variables...")
    print("   (Run in backend container to check)")
    print("   docker exec sims_backend env | grep -E 'EXA_API_KEY|GEMINI_API_KEY'")
    
    # Recommendations
    print("\n" + "=" * 50)
    print("📋 DIAGNOSIS SUMMARY:")
    print("=" * 50)
    
    if recent_count and recent_count > 10:
        print("\n❌ LIKELY CAUSE: Too many recent articles blocking ingestion")
        print("\n🔧 FIX: Modify backend/app.py line ~1566")
        print("   Change: if recent_articles > 10:")
        print("   To:     if recent_articles > 50:  # or remove entirely")
    elif stats and stats.get('total_articles', 0) == 0:
        print("\n⚠️  No articles in database - first time running?")
        print("   Run: python run_reingestion_docker.py")
    else:
        print("\n✅ No obvious blocking issues detected")
        print("   Check backend logs: docker-compose logs backend")
        print("   Try fetching again: python run_reingestion_docker.py")

if __name__ == "__main__":
    main()

