#!/usr/bin/env python3
"""
Script to clear the database and reingest fresh data
This ensures all articles use only 'verified' or 'unverified' status
"""

import requests
import time
import json

# Configuration
BACKEND_URL = "http://localhost:5000"

def make_request(endpoint, method="GET", data=None, timeout=60):
    """Make HTTP request to backend API"""
    url = f"{BACKEND_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=30)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=timeout)
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error making {method} request to {endpoint}: {e}")
        return None

def check_backend_health():
    """Check if backend is healthy"""
    print("🔍 Checking backend health...")
    health = make_request("/api/health")
    if health and health.get('status') == 'healthy':
        print("✅ Backend is healthy")
        return True
    else:
        print("❌ Backend is not healthy")
        return False

def get_database_stats():
    """Get current database statistics"""
    print("📊 Getting database statistics...")
    stats = make_request("/api/database-stats")
    if stats:
        print(f"📈 Current database state:")
        print(f"   - Total articles: {stats.get('total_articles', 0)}")
        print(f"   - Articles with summary: {stats.get('content_stats', {}).get('articles_with_summary', 0)}")
        print(f"   - BD matches: {stats.get('matching_records', {}).get('bd_matches', 0)}")
        print(f"   - International matches: {stats.get('matching_records', {}).get('international_matches', 0)}")
        return stats
    return None

def clear_database():
    """Clear all data from the database"""
    print("🗑️  Clearing database...")
    result = make_request("/api/clear-database", method="POST")
    if result and result.get('status') == 'success':
        deleted = result.get('deleted', {})
        print(f"✅ Database cleared successfully!")
        print(f"   - Deleted {deleted.get('articles', 0)} articles")
        print(f"   - Deleted {deleted.get('bd_matches', 0)} BD matches")
        print(f"   - Deleted {deleted.get('int_matches', 0)} international matches")
        return True
    else:
        print("❌ Failed to clear database")
        return False

def fetch_latest_data():
    """Fetch latest data from Exa"""
    print("📥 Fetching latest data from Exa...")
    print("⏳ This may take 2-3 minutes as it processes 25 articles with Gemini analysis...")
    
    # Use longer timeout for Exa fetch
    result = make_request("/api/fetch-latest", method="POST", timeout=300)  # 5 minutes
    if result and result.get('status') == 'success':
        stats = result.get('stats', {})
        print(f"✅ Data fetch completed!")
        print(f"   - Processed: {stats.get('processed', 0)} articles")
        print(f"   - Skipped: {stats.get('skipped', 0)} articles")
        print(f"   - Failed: {stats.get('failed', 0)} articles")
        return True
    else:
        print("❌ Failed to fetch latest data")
        return False

def reanalyze_all_articles():
    """Reanalyze all articles with Gemini"""
    print("🤖 Reanalyzing all articles with Gemini...")
    print("⏳ This may take several minutes depending on the number of articles...")
    
    # Use longer timeout for reanalysis
    result = make_request("/api/reanalyze-all", method="POST", timeout=300)  # 5 minutes
    if result and result.get('status') == 'success':
        stats = result.get('stats', {})
        print(f"✅ Reanalysis completed!")
        print(f"   - Processed: {stats.get('processed', 0)} articles")
        print(f"   - Skipped: {stats.get('skipped', 0)} articles")
        print(f"   - Failed: {stats.get('failed', 0)} articles")
        return True
    else:
        print("❌ Failed to reanalyze articles")
        return False

def verify_fact_check_status():
    """Verify that no articles have 'partially_verified' status"""
    print("🔍 Verifying fact-check statuses...")
    articles = make_request("/api/articles?limit=1000")
    if articles:
        partially_verified_count = 0
        verified_count = 0
        unverified_count = 0
        
        for article in articles:
            # Extract fact check status from the article
            fact_check_status = None
            try:
                if article.get('summary_json'):
                    summary = json.loads(article['summary_json'])
                    fact_check_status = summary.get('fact_check', {}).get('status', 'unverified')
                else:
                    fact_check_status = article.get('fact_check', 'unverified')
            except:
                fact_check_status = 'unverified'
            
            if fact_check_status == 'partially_verified':
                partially_verified_count += 1
            elif fact_check_status == 'verified':
                verified_count += 1
            else:
                unverified_count += 1
        
        print(f"📊 Fact-check status distribution:")
        print(f"   - Verified: {verified_count}")
        print(f"   - Unverified: {unverified_count}")
        print(f"   - Partially verified: {partially_verified_count}")
        
        if partially_verified_count == 0:
            print("✅ No articles with 'partially_verified' status found!")
            return True
        else:
            print("❌ Found articles with 'partially_verified' status!")
            return False
    else:
        print("❌ Failed to fetch articles for verification")
        return False

def main():
    """Main execution flow"""
    print("🚀 Starting database clear and reingest process...")
    print("=" * 60)
    
    # Step 1: Check backend health
    if not check_backend_health():
        print("❌ Backend is not available. Please ensure Docker containers are running.")
        return
    
    # Step 2: Get initial database stats
    initial_stats = get_database_stats()
    
    # Step 3: Clear database
    if not clear_database():
        print("❌ Failed to clear database. Stopping.")
        return
    
    # Step 4: Wait a moment for database operations to complete
    print("⏳ Waiting for database operations to complete...")
    time.sleep(5)
    
    # Step 5: Fetch latest data
    if not fetch_latest_data():
        print("❌ Failed to fetch latest data. Stopping.")
        return
    
    # Step 6: Wait for data processing
    print("⏳ Waiting for data processing to complete...")
    time.sleep(10)
    
    # Step 7: Reanalyze all articles
    if not reanalyze_all_articles():
        print("❌ Failed to reanalyze articles. Stopping.")
        return
    
    # Step 8: Wait for analysis to complete
    print("⏳ Waiting for Gemini analysis to complete...")
    time.sleep(15)
    
    # Step 9: Get final database stats
    print("\n📊 Final database statistics:")
    final_stats = get_database_stats()
    
    # Step 10: Verify fact-check statuses
    if verify_fact_check_status():
        print("\n🎉 SUCCESS: Database clear and reingest completed successfully!")
        print("✅ All articles now use only 'verified' or 'unverified' status")
    else:
        print("\n⚠️  WARNING: Some articles still have 'partially_verified' status")
    
    print("\n" + "=" * 60)
    print("🏁 Process completed!")

if __name__ == "__main__":
    main() 