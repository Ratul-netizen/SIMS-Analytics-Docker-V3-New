#!/usr/bin/env python3
"""
Script to check if any articles still have 'partially_verified' status
"""

import requests
import json

def check_partially_verified():
    """Check if any articles have partially_verified status"""
    try:
        # Get all articles
        response = requests.get('http://localhost:5000/api/articles?limit=1000', timeout=30)
        response.raise_for_status()
        articles = response.json()
        
        print(f"Total articles in database: {len(articles)}")
        
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
                print(f"  Found partially_verified: {article.get('title', 'Unknown')[:50]}...")
            elif fact_check_status == 'verified':
                verified_count += 1
            else:
                unverified_count += 1
        
        print(f"\nFact-check status distribution:")
        print(f"  - Verified: {verified_count}")
        print(f"  - Unverified: {unverified_count}")
        print(f"  - Partially verified: {partially_verified_count}")
        
        if partially_verified_count == 0:
            print("\n✅ No articles with 'partially_verified' status found!")
            print("The pie chart should only show 'Verified' and 'Unverified' segments.")
            print("\nIf you're still seeing 'Partially Verified' in the chart, try:")
            print("1. Hard refresh your browser (Ctrl+F5)")
            print("2. Clear browser cache")
            print("3. Wait a few minutes for the chart to update")
        else:
            print(f"\n❌ Found {partially_verified_count} articles with 'partially_verified' status!")
            print("These need to be reanalyzed to remove the partially_verified status.")
        
    except Exception as e:
        print(f"Error checking articles: {e}")

if __name__ == "__main__":
    check_partially_verified() 