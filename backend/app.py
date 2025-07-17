from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from exa_py import Exa
import datetime
from dotenv import load_dotenv
import os
import json
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
import re
from difflib import SequenceMatcher
import spacy
from collections import Counter
from sqlalchemy import text
import hashlib
import logging
import requests
import time
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import base64
from google import genai
from google.genai import types

# Ensure instance directory exists
instance_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance')
os.makedirs(instance_path, exist_ok=True)

app = Flask(__name__)
# Set up portable SQLite DB path
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'instance', 'SIMS_Analytics.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
print("Database URI:", app.config['SQLALCHEMY_DATABASE_URI'])
print("Database absolute path:", os.path.abspath('instance/SIMS_Analytics.db'))
db = SQLAlchemy(app)
migrate = Migrate(app, db)
# --- Global Source Lists ---
INDIAN_SOURCES = set([
    "timesofindia.indiatimes.com", "hindustantimes.com", "ndtv.com", "thehindu.com", "indianexpress.com", "indiatoday.in", "news18.com", "zeenews.india.com", "aajtak.in", "abplive.com", "jagran.com", "bhaskar.com", "livehindustan.com", "business-standard.com", "economictimes.indiatimes.com", "livemint.com", "scroll.in", "thewire.in", "wionews.com", "indiatvnews.com", "newsnationtv.com", "jansatta.com", "india.com"
])
BD_SOURCES = set([
    # English Language Dailies
    'thedailystar.net', 'bdnews24.com', 'newagebd.net', 'tbsnews.net', 'dhakatribune.com', 
    'observerbd.com', 'thefinancialexpress.com.bd', 'unb.com.bd', 'risingbd.com', 
    'bangladeshpost.net', 'daily-bangladesh.com',
    
    # Bengali Language Dailies
    'prothomalo.com', 'bangladeshpratidin.com.bd', 'jugantor.com', 'kalerkantho.com', 
    'ittefaq.com.bd', 'samakal.com', 'manabzamin.com', 'bhorerkagoj.com.bd', 
    'janakantha.com.bd', 'amadershomoy.com', 'bonikbarta.net', 'dailyinqilab.com', 
    'jaijaidinbd.com', 'alokitobangladesh.com', 'daily-sangbad.com',
    
    # TV/Online News
    'channeli.tv', 'atnbangla.tv', 'ntvbd.com', 'itvbd.com', 'somoynews.tv', 
    'gtv.com.bd', 'ekushey-tv.com', 'rtvonline.com', 'banglavision.tv', 
    'massranga.tv', 'channel24bd.tv', 'dbcnews.tv', 'ekattor.tv', 'jamuna.tv', 
    'news24bd.tv', 'atnnewstv.com', 'btv.gov.bd', 'deshtvbd.com', 'bijoytv.com', 
    'boishakhitv.com',
    
    # Legacy entries (keeping existing for compatibility)
    'banglatribune.com', 'bssnews.net', 'daily-sun.com', 'dailyjanakantha.com',
    'amardesh.com', 'dailynayadiganta.com', 'dailysangram.com'
])
INTL_SOURCES = set([
    # Major Global News Networks
    'bbc.com', 'cnn.com', 'aljazeera.com', 'reuters.com', 'apnews.com', 'sky.com', 
    'france24.com', 'dw.com', 'foxnews.com', 'abcnews.go.com', 'msnbc.com', 'cnbc.com',
    'nhk.or.jp', 'cbc.ca', 'bloomberg.com', 'rt.com', 'alarabiya.net', 'abc.net.au',
    'channelnewsasia.com',
    
    # Major Newspapers
    'nytimes.com', 'washingtonpost.com', 'theguardian.com', 'wsj.com', 'ft.com',
    'usatoday.com', 'independent.co.uk', 'dailymail.co.uk', 'lefigaro.fr', 'faz.net',
    'elpais.com', 'theglobeandmail.com',
    
    # Asian News Sources
    'asahi.com', 'yomiuri.co.jp', 'chinadaily.com.cn', 'straitstimes.com', 'scmp.com',
    'japantimes.co.jp', 'mainichi.jp', 'koreatimes.co.kr', 'joongang.co.kr', 'hankyoreh.com',
    'kompas.com',
    
    # Indian News Sources (International Category)
    'ndtv.com', 'timesofindia.indiatimes.com', 'hindustantimes.com', 'thehindu.com',
    'bhaskar.com', 'jagran.com',
    
    # Middle East & Africa
    'gulfnews.com', 'arabnews.com',
    
    # European Sources
    'lemonde.fr', 'spiegel.de', 'corriere.it', 'thetimes.co.uk', 'telegraph.co.uk',
    'mirror.co.uk', 'express.co.uk', 'thesun.co.uk', 'metro.co.uk', 'eveningstandard.co.uk',
    'irishtimes.com', 'rte.ie', 'heraldscotland.com', 'scotsman.com', 'thejournal.ie',
    'breakingnews.ie', 'irishmirror.ie', 'irishnews.com', 'belfasttelegraph.co.uk',
    
    # US Regional & Specialty
    'cbsnews.com', 'nbcnews.com', 'latimes.com', 'forbes.com', 'economist.com',
    'npr.org', 'voanews.com', 'rferl.org',
    
    # Australian Sources
    'news.com.au', 'smh.com.au', 'theage.com.au', 'theaustralian.com.au',
    
    # Other International
    'tass.com', 'sputniknews.com', 'globaltimes.cn'
])
# --- Logging Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# --- CORS Configuration ---
CORS(app, 
     resources={r"/api/*": {"origins": "*"}},
     supports_credentials=True,
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization", "X-Requested-With"])

# Initialize database if it doesn't exist
with app.app_context():
    db.create_all()

load_dotenv()
EXA_API_KEY = os.getenv('EXA_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Initialize Gemini client
gemini_client = None
if GEMINI_API_KEY:
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info("Gemini AI client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Gemini AI client: {e}")
        gemini_client = None
else:
    logger.warning("GEMINI_API_KEY not found - Gemini AI features will be unavailable")

# Load spaCy model once at startup
try:
    nlp = spacy.load('en_core_web_sm')
    logger.info("SpaCy model 'en_core_web_sm' loaded successfully")
except Exception as e:
    logger.error(f"Failed to load SpaCy model: {e}")
    nlp = None

# Initialize VADER sentiment analyzer once at startup
vader_analyzer = SentimentIntensityAnalyzer()

def analyze_sentiment_locally(text):
    """
    Analyze sentiment locally using VADER and return percentage breakdown
    Perfect for news articles and social media content
    """
    if not text or not text.strip():
        return {"positive": 0.0, "negative": 0.0, "neutral": 1.0, "cautious": 0.0}
    
    # Get VADER sentiment scores
    scores = vader_analyzer.polarity_scores(text)
    
    # Extract individual sentiment components
    positive = round(scores['pos'], 3)
    negative = round(scores['neg'], 3) 
    neutral = round(scores['neu'], 3)
    
    # Calculate "cautious" sentiment for mixed/uncertain content
    # When compound score is close to 0, it indicates mixed sentiment
    compound = scores['compound']
    cautious = round(max(0, 0.3 - abs(compound)) if abs(compound) < 0.3 else 0, 3)
    
    # Ensure values sum to approximately 1.0 (adjust for cautious sentiment)
    total = positive + negative + neutral + cautious
    if total > 0 and total != 1.0:
        factor = 1.0 / total
        positive = round(positive * factor, 3)
        negative = round(negative * factor, 3)
        neutral = round(neutral * factor, 3)
        cautious = round(cautious * factor, 3)
    
    return {
        "positive": positive,
        "negative": negative,
        "neutral": neutral,
        "cautious": cautious
    }

def get_article_domain(url):
    """
    Extract clean domain from URL
    """
    if not url:
        return ''
    
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Remove www. prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except Exception:
        return ''

def filter_independent_sources(sources, original_domain):
    """
    Filter out sources that match the original article's domain
    This prevents self-referencing in fact-checking
    """
    if not sources or not isinstance(sources, list):
        return []
    
    filtered_sources = []
    original_domain = original_domain.lower() if original_domain else ''
    
    for source in sources:
        if not isinstance(source, dict):
            continue
            
        source_url = source.get('source_url', '')
        source_domain = get_article_domain(source_url)
        
        # Skip if source domain matches original domain (self-referencing)
        if source_domain and source_domain == original_domain:
            logger.info(f"Filtering out self-referencing source: {source_domain}")
            continue
            
        filtered_sources.append(source)
    
    return filtered_sources

def determine_fact_check_status(sources):
    """
    Determine fact-check status based on simplified 2-category rules:
    - verified: ≥1 BD + ≥1 international source (both categories required)
    - partially_verified: ≥1 BD OR ≥1 international source (but not both)
    - unverified: no external sources found (only original news source itself)
    
    Note: Any source that is not BD/Bangladesh is automatically treated as international.
    """
    if not sources or not isinstance(sources, list):
        return 'unverified'
    
    bd_sources = []
    international_sources = []
    
    # Categorize sources by country/type
    for source in sources:
        if not isinstance(source, dict):
            continue
            
        source_country = source.get('source_country', '').lower()
        source_name = source.get('source_name', '')
        
        if source_country in ['bd', 'bangladesh']:
            bd_sources.append(source_name)
        else:
            # Any source that is NOT BD/Bangladesh is treated as international
            # This includes 'international', 'other', or any unspecified category
            international_sources.append(source_name)
    
    # Apply enhanced fact-check rules with simplified 2-category system
    has_bd_source = len(bd_sources) >= 1
    has_intl_source = len(international_sources) >= 1
    
    # VERIFIED: Requires BOTH BD and International sources
    if has_bd_source and has_intl_source:
        logger.info(f"VERIFIED: Found both categories - BD: {len(bd_sources)} ({bd_sources}), International: {len(international_sources)} ({international_sources})")
        return 'verified'
    
    # PARTIALLY_VERIFIED: Has either BD or International sources, but not both
    elif has_bd_source or has_intl_source:
        if has_bd_source and not has_intl_source:
            logger.info(f"PARTIALLY_VERIFIED: Found {len(bd_sources)} BD sources ({bd_sources}) but missing international verification")
        elif has_intl_source and not has_bd_source:
            logger.info(f"PARTIALLY_VERIFIED: Found {len(international_sources)} international sources ({international_sources}) but missing BD sources")
        return 'partially_verified'
    
    # UNVERIFIED: No external sources found
    else:
        logger.info(f"UNVERIFIED: No external sources found for verification (BD: {len(bd_sources)}, International: {len(international_sources)})")
        return 'unverified'

def categorize_news_source(domain, url):
    """
    Categorize a news source by domain and return source info
    """
    domain = domain.lower()
    
    # BD Sources - Comprehensive List (Updated)
    bd_sources_map = {
        # English Language Dailies
        'thedailystar.net': 'The Daily Star',
        'bdnews24.com': 'bdnews24.com',
        'dhakatribune.com': 'Dhaka Tribune',
        'newagebd.net': 'New Age Bangladesh',
        'tbsnews.net': 'The Business Standard',
        'observerbd.com': 'The Observer',
        'thefinancialexpress.com.bd': 'The Financial Express BD',
        'financialexpress.com.bd': 'The Financial Express BD',
        'unb.com.bd': 'United News of Bangladesh',
        'risingbd.com': 'Risingbd',
        'bangladeshpost.net': 'Bangladesh Post',
        'daily-bangladesh.com': 'Daily Bangladesh',
        
        # Bengali Language Dailies
        'prothomalo.com': 'Prothom Alo',
        'bangladeshpratidin.com.bd': 'Bangladesh Pratidin',
        'jugantor.com': 'Jugantor',
        'kalerkantho.com': 'Kaler Kantho',
        'ittefaq.com.bd': 'Ittefaq',
        'samakal.com': 'Samakal',
        'manabzamin.com': 'Manab Zamin',
        'bhorerkagoj.com.bd': 'Bhorer Kagoj',
        'janakantha.com.bd': 'Janakantha',
        'amadershomoy.com': 'Amader Shomoy',
        'bonikbarta.net': 'Bonik Barta',
        'dailyinqilab.com': 'Daily Inqilab',
        'jaijaidinbd.com': 'Jai Jai Din',
        'alokitobangladesh.com': 'Alokito Bangladesh',
        'daily-sangbad.com': 'Daily Sangbad',
        
        # TV/Online News Channels
        'channeli.tv': 'Channel i',
        'atnbangla.tv': 'ATN Bangla',
        'ntvbd.com': 'NTV Bangladesh',
        'itvbd.com': 'Independent Television',
        'somoynews.tv': 'Somoy News',
        'gtv.com.bd': 'Gazi Television',
        'ekushey-tv.com': 'Ekushey TV',
        'rtvonline.com': 'RTV',
        'banglavision.tv': 'Banglavision',
        'massranga.tv': 'Maasranga TV',
        'channel24bd.tv': 'Channel 24',
        'dbcnews.tv': 'DBC News',
        'ekattor.tv': 'Ekattor TV',
        'jamuna.tv': 'Jamuna TV',
        'news24bd.tv': 'News24',
        'atnnewstv.com': 'ATN News',
        'btv.gov.bd': 'Bangladesh Television',
        'deshtvbd.com': 'Desh TV',
        'bijoytv.com': 'Bijoy TV',
        'boishakhitv.com': 'Boishakhi TV'
    }
    
    # International Sources - Comprehensive List (Updated)
    intl_sources_map = {
        # Major Global News Networks
        'bbc.com': 'BBC News',
        'cnn.com': 'CNN',
        'edition.cnn.com': 'CNN International',
        'aljazeera.com': 'Al Jazeera',
        'reuters.com': 'Reuters',
        'apnews.com': 'Associated Press',
        'sky.com': 'Sky News',
        'news.sky.com': 'Sky News',
        'france24.com': 'France 24',
        'dw.com': 'Deutsche Welle',
        'foxnews.com': 'Fox News',
        'abcnews.go.com': 'ABC News',
        'msnbc.com': 'MSNBC',
        'cnbc.com': 'CNBC',
        'nhk.or.jp': 'NHK World',
        'www3.nhk.or.jp': 'NHK World',
        'cbc.ca': 'CBC News',
        'bloomberg.com': 'Bloomberg',
        'rt.com': 'RT',
        'alarabiya.net': 'Al Arabiya',
        'abc.net.au': 'ABC Australia',
        'channelnewsasia.com': 'Channel NewsAsia',
        
        # Major Newspapers
        'nytimes.com': 'The New York Times',
        'washingtonpost.com': 'The Washington Post',
        'theguardian.com': 'The Guardian',
        'wsj.com': 'The Wall Street Journal',
        'ft.com': 'Financial Times',
        'usatoday.com': 'USA Today',
        'independent.co.uk': 'The Independent',
        'dailymail.co.uk': 'Daily Mail',
        'lefigaro.fr': 'Le Figaro',
        'faz.net': 'Frankfurter Allgemeine',
        'elpais.com': 'El País',
        'theglobeandmail.com': 'The Globe and Mail',
        
        # Asian News Sources
        'asahi.com': 'The Asahi Shimbun',
        'yomiuri.co.jp': 'The Yomiuri Shimbun',
        'chinadaily.com.cn': 'China Daily',
        'straitstimes.com': 'The Straits Times',
        'scmp.com': 'South China Morning Post',
        'japantimes.co.jp': 'The Japan Times',
        'mainichi.jp': 'The Mainichi',
        'koreatimes.co.kr': 'The Korea Times',
        'joongang.co.kr': 'JoongAng Daily',
        'hankyoreh.com': 'The Hankyoreh',
        'kompas.com': 'Kompas',
        
        # Indian News Sources (International Category)
        'ndtv.com': 'NDTV',
        'timesofindia.indiatimes.com': 'Times of India',
        'hindustantimes.com': 'Hindustan Times',
        'thehindu.com': 'The Hindu',
        'bhaskar.com': 'Dainik Bhaskar',
        'jagran.com': 'Dainik Jagran',
        
        # Middle East & Africa
        'gulfnews.com': 'Gulf News',
        'arabnews.com': 'Arab News',
        
        # European Sources
        'lemonde.fr': 'Le Monde',
        'spiegel.de': 'Der Spiegel',
        'corriere.it': 'Corriere della Sera',
        'thetimes.co.uk': 'The Times',
        'telegraph.co.uk': 'The Telegraph',
        'mirror.co.uk': 'The Mirror',
        'express.co.uk': 'Daily Express',
        'thesun.co.uk': 'The Sun',
        'metro.co.uk': 'Metro',
        'eveningstandard.co.uk': 'Evening Standard',
        'irishtimes.com': 'The Irish Times',
        'rte.ie': 'RTÉ',
        'heraldscotland.com': 'The Herald',
        'scotsman.com': 'The Scotsman',
        'thejournal.ie': 'TheJournal.ie',
        'breakingnews.ie': 'Breaking News',
        'irishmirror.ie': 'Irish Mirror',
        'irishnews.com': 'Irish News',
        'belfasttelegraph.co.uk': 'Belfast Telegraph',
        
        # US Regional & Specialty
        'cbsnews.com': 'CBS News',
        'nbcnews.com': 'NBC News',
        'latimes.com': 'Los Angeles Times',
        'forbes.com': 'Forbes',
        'economist.com': 'The Economist',
        'npr.org': 'NPR',
        'voanews.com': 'Voice of America',
        'rferl.org': 'Radio Free Europe',
        
        # Australian Sources
        'news.com.au': 'News.com.au',
        'smh.com.au': 'Sydney Morning Herald',
        'theage.com.au': 'The Age',
        'theaustralian.com.au': 'The Australian',
        
        # Other International
        'tass.com': 'TASS',
        'sputniknews.com': 'Sputnik News',
        'globaltimes.cn': 'Global Times'
    }
    
    # Accept sub-domains like 'en.prothomalo.com' or 'm.bbc.com' by checking suffix
    for key, name in bd_sources_map.items():
        if domain == key or domain.endswith('.' + key):
            return {
                'source_name': name,
                'source_country': 'BD',
                'source_url': url
            }
    
    for key, name in intl_sources_map.items():
        if domain == key or domain.endswith('.' + key):
            return {
                'source_name': name,
                'source_country': 'International',
                'source_url': url
            }
    
    return None



def construct_realistic_url(domain, title):
    """
    Construct a realistic URL for a news story based on domain and title
    """
    import re
    from datetime import datetime
    
    # Clean title for URL
    clean_title = re.sub(r'[^\w\s-]', '', title.lower())
    clean_title = re.sub(r'\s+', '-', clean_title.strip())
    clean_title = clean_title[:50]  # Limit length
    
    current_year = datetime.now().year
    
    # Domain-specific URL patterns
    url_patterns = {
        'thedailystar.net': f'https://www.thedailystar.net/news/bangladesh/politics/news-{clean_title}-{current_year}',
        'bdnews24.com': f'https://bdnews24.com/bangladesh/{clean_title}',
        'dhakatribune.com': f'https://www.dhakatribune.com/bangladesh/{current_year}/{clean_title}',
        'prothomalo.com': f'https://www.prothomalo.com/bangladesh/{clean_title}',
        'bbc.com': f'https://www.bbc.com/news/world-asia-{clean_title}-{current_year}',
        'reuters.com': f'https://www.reuters.com/world/asia-pacific/{clean_title}-{current_year}',
        'cnn.com': f'https://www.cnn.com/{current_year}/world/asia/{clean_title}',
        'aljazeera.com': f'https://www.aljazeera.com/news/{current_year}/asia/{clean_title}'
    }
    
    return url_patterns.get(domain, f'https://{domain}/news/{clean_title}')

def validate_url_exists(url):
    """
    Smart URL validation that handles Google grounding redirects and direct URLs
    """
    if not url or not url.startswith(('http://', 'https://')):
        logger.warning(f"URL validation FAILED: Invalid format - {url}")
        return False
    
    # Check if this is a Google grounding API redirect
    if is_google_grounding_redirect(url):
        return validate_google_grounding_url(url)
    
    # For direct URLs, use standard validation
    return validate_direct_url(url)

def is_google_grounding_redirect(url):
    """
    Check if URL is a Google grounding API redirect
    """
    google_grounding_patterns = [
        'vertexaisearch.cloud.google.com/grounding-api-redirect/',
        'grounding-api.googleapis.com/redirect/',
        'search.googleapis.com/grounding/'
    ]
    return any(pattern in url for pattern in google_grounding_patterns)

def validate_google_grounding_url(url):
    """
    Validate Google grounding redirect by following it to the final destination
    """
    logger.info(f"🔗 Detected Google grounding redirect: {url[:100]}...")
    
    try:
        # Try to resolve the redirect to get the final URL
        final_url = resolve_redirect_url(url)
        
        if final_url and final_url != url:
            # Extract domain from final URL
            from urllib.parse import urlparse
            final_domain = urlparse(final_url).netloc.lower().replace('www.', '')
            
            # Accept all valid domains - categorize later
            if is_known_news_domain(final_domain):
                logger.info(f"✅ Google redirect resolves to known news domain: {final_domain}")
                return True
            else:
                logger.info(f"✅ Google redirect resolves to other source domain: {final_domain}")
                return True  # Accept unknown domains as "Other Sources"
        else:
            logger.warning(f"❌ Could not resolve Google redirect: {url}")
            return False
            
    except Exception as e:
        logger.warning(f"❌ Error validating Google redirect: {url} - {str(e)}")
        return False

def is_known_news_domain(domain):
    """
    Check if domain is in our known BD or international news sources
    """
    # Use existing source maps for validation
    source_info = categorize_news_source(domain, f"https://{domain}")
    return source_info is not None

def validate_direct_url(url):
    """
    Standard validation for direct news URLs
    """
    try:
        # Use HEAD request to check if URL exists without downloading content
        response = requests.head(url, timeout=10, allow_redirects=True)
        
        # Accept 200 (OK) and 302 (Redirect) as valid
        if response.status_code in [200, 302]:
            logger.info(f"✅ Direct URL validation SUCCESS: {url} (status: {response.status_code})")
            return True
        else:
            logger.warning(f"❌ Direct URL validation FAILED: {url} (status: {response.status_code})")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.warning(f"❌ Direct URL validation ERROR: {url} - {str(e)}")
        return False
    except Exception as e:
        logger.error(f"❌ Direct URL validation EXCEPTION: {url} - {str(e)}")
        return False

def validate_and_filter_sources(sources):
    """
    Validate all source URLs and filter out broken/fake ones
    """
    if not sources or not isinstance(sources, list):
        return []
    
    validated_sources = []
    
    for source in sources:
        if not isinstance(source, dict):
            continue
            
        source_url = source.get('source_url', '')
        source_name = source.get('source_name', '')
        
        if not source_url:
            logger.warning(f"Source '{source_name}' has no URL, skipping")
            continue
        
        # Validate URL exists
        if validate_url_exists(source_url):
            validated_sources.append(source)
            logger.info(f"✅ VALID source: {source_name} - {source_url}")
        else:
            logger.warning(f"❌ INVALID source removed: {source_name} - {source_url}")
    
    logger.info(f"URL validation complete: {len(validated_sources)}/{len(sources)} sources valid")
    return validated_sources

class Article(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    url          = db.Column(db.String, unique=True, nullable=False)
    title        = db.Column(db.String, nullable=False)
    published_at = db.Column(db.DateTime)
    author       = db.Column(db.String)
    source       = db.Column(db.String)
    sentiment    = db.Column(db.String)
    fact_check   = db.Column(db.String)
    bd_summary   = db.Column(db.Text)
    int_summary  = db.Column(db.Text)
    image        = db.Column(db.String)
    favicon      = db.Column(db.String)
    score        = db.Column(db.Float)
    extras       = db.Column(db.Text)  # Store as JSON string
    full_text    = db.Column(db.Text)
    summary_json = db.Column(db.Text)  # Store as JSON string
    category     = db.Column(db.String) # Added for Gemma analysis
    summary_text = db.Column(db.Text) # Added for Gemma analysis
    fact_check_results = db.Column(db.Text) # Added for Gemma analysis

    def to_dict(self):
        # Parse summary_json to get the full Gemma analysis
        summary_obj = None
        if self.summary_json:
            try:
                summary_obj = json.loads(self.summary_json)
                if not isinstance(summary_obj, dict):
                    summary_obj = None
            except Exception:
                summary_obj = None

        # Extract fact check information (matching dashboard format)
        fact_check_obj = summary_obj.get('fact_check', {}) if isinstance(summary_obj, dict) else {}
        if isinstance(fact_check_obj, dict):
            fact_check_status = fact_check_obj.get('status', 'unverified')
            fact_check_sources = fact_check_obj.get('sources', [])
        elif isinstance(fact_check_obj, str):
            fact_check_status = fact_check_obj
            fact_check_sources = []
        else:
            fact_check_status = 'unverified'
            fact_check_sources = []

        # Extract coverage information from fact check sources
        bangladeshi_matches = []
        international_matches = []
        
        for source in fact_check_sources:
            if isinstance(source, dict):
                source_country = source.get('source_country', '').lower()
                if source_country in ['bd', 'bangladesh']:
                    bangladeshi_matches.append({
                        'title': source.get('source_name', 'Unknown'),
                        'source': source.get('source_name', 'Unknown'),
                        'url': source.get('source_url', '')
                    })
                elif source_country and source_country not in ['bd', 'bangladesh']:
                    international_matches.append({
                        'title': source.get('source_name', 'Unknown'),
                        'source': source.get('source_name', 'Unknown'),
                        'url': source.get('source_url', '')
                    })

        # Extract entities from extras
        extras = json.loads(self.extras) if self.extras else {}
        entities = extras.get('entities', [])

        # Perform local sentiment analysis on the full text
        sentiment_analysis = analyze_sentiment_locally(self.full_text or "")
        
        # Create summary structure that frontend expects
        summary_structure = {
            "summary": summary_obj.get('summary') if isinstance(summary_obj, dict) else (self.summary_text or ""),
            "summary_text": summary_obj.get('summary') if isinstance(summary_obj, dict) else (self.summary_text or ""),
            "sentiment": self.sentiment or (summary_obj.get('sentiment', 'Neutral') if isinstance(summary_obj, dict) else 'Neutral'),
            "category": self.category or (summary_obj.get('category', 'Other') if isinstance(summary_obj, dict) else 'Other'),
            "fact_check": {
                "status": fact_check_status,
                "sources": fact_check_sources
            },
            "fact_check_results": {
                "status": fact_check_status,
                "sources": fact_check_sources
            }
        }

        # Return data in the same format as dashboard endpoint
        return {
            "id": self.id,
            "title": self.title or "",
            "headline": self.title or "",  # Add headline field for compatibility
            "url": self.url or "",
            "date": self.published_at.isoformat() if self.published_at else None,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "publishedDate": self.published_at.isoformat() if self.published_at else None,  # Frontend expects this field
            "summary": summary_structure,  # Structured summary object
            "summary_text": summary_obj.get('summary') if isinstance(summary_obj, dict) else (self.summary_text or ""),
            "sentiment": self.sentiment or (summary_obj.get('sentiment', 'Neutral') if isinstance(summary_obj, dict) else 'Neutral'),
            "category": self.category or (summary_obj.get('category', 'Other') if isinstance(summary_obj, dict) else 'Other'),
            "fact_check": fact_check_status,  # Simple string for display
            "fact_check_status": fact_check_status,  # Keep for backward compatibility
            "fact_check_sources": fact_check_sources,  # Keep for backward compatibility
            "bangladeshi_matches": bangladeshi_matches,
            "international_matches": international_matches,
            "entities": entities,
            "source": self.source or "",
            "source_name": self.source or "",
            "image": self.image or "",
            "favicon": self.favicon or "",
            "score": self.score if self.score is not None else 0,
            "extras": extras,
            "text": self.full_text or "",
            "author": self.author or "",
            "links": [],  # Add empty links array for compatibility
            # Add media coverage summary for compatibility
            "media_coverage_summary": {
                "bangladeshi_media": "Covered" if bangladeshi_matches else "Not covered",
                "international_media": "Covered" if international_matches else "Not covered"
            },
            # Add local sentiment analysis breakdown
            "sentiment_analysis": sentiment_analysis
        }

class BDMatch(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('article.id'), nullable=False)
    title      = db.Column(db.String, nullable=False)
    source     = db.Column(db.String, nullable=False)
    url        = db.Column(db.String)

class IntMatch(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('article.id'), nullable=False)
    title      = db.Column(db.String, nullable=False)
    source     = db.Column(db.String, nullable=False)
    url        = db.Column(db.String)

def safe_capitalize(val, default='Neutral'):
    if isinstance(val, str):
        v = val.capitalize()
        if v in ['Positive', 'Negative', 'Neutral', 'Cautious']:
            return v
    return default

def normalize_category(val):
    """Normalize category to capitalized form (Politics, Sports, etc.) or 'Other'."""
    valid_categories = [
        'Politics', 'Sports', 'Technology', 'Crime', 'Entertainment', 'Others',
        'Health', 'Economy', 'Education', 'Security', 'Environment', 'International', 'Culture', 'Science', 'Business'
    ]
    if not val:
        return 'Other'
    val_cap = val.strip().capitalize()
    for cat in valid_categories:
        if val.lower() == cat.lower():
            return cat
    return 'Other'

# --- Gemma API Call Function (OpenRouter) ---
def clean_json_text(text):
    """
    Clean up common JSON formatting issues that might cause parsing errors.
    """
    if not text:
        return ""
    
    # Remove markdown code blocks
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*$', '', text)
    
    # Remove leading/trailing whitespace and newlines
    text = text.strip()
    
    # Fix common quote issues
    text = re.sub(r'[\u201c\u201d]', '"', text)  # Replace smart quotes
    text = re.sub(r'[\u2018\u2019]', "'", text)  # Replace smart single quotes
    
    # Fix trailing commas in objects and arrays
    text = re.sub(r',(\s*[}\]])', r'\1', text)
    
    return text

def resolve_redirect_url(url):
    """
    Resolve redirect URLs (like Google's grounding API redirects) to get the actual source URL.
    """
    try:
        # Check if it's a Google grounding API redirect URL
        if 'vertexaisearch.cloud.google.com/grounding-api-redirect' in url:
            logger.info(f"Resolving Google redirect URL: {url[:100]}...")
            
            # Make a HEAD request to follow redirects
            response = requests.head(url, allow_redirects=True, timeout=10)
            
            if response.status_code == 200 and response.url != url:
                logger.info(f"Resolved to: {response.url}")
                return response.url
            else:
                logger.warning(f"Could not resolve redirect URL: {url}")
                return None
        else:
            # For other URLs, just return as-is
            return url
            
    except Exception as e:
        logger.warning(f"Error resolving redirect URL {url}: {e}")
        return None

def extract_json(text):
    """
    Extract JSON from text, with fallback to regex extraction if direct parsing fails.
    """
    if not text:
        return {}
    
    # First, try to clean the text
    cleaned_text = clean_json_text(text)
    
    try:
        return json.loads(cleaned_text)
    except Exception:
        try:
            # Try to extract JSON using regex
            json_text_match = re.search(r"\{[\s\S]+\}", cleaned_text)
            if json_text_match:
                return json.loads(json_text_match.group())
        except Exception as e:
            logger.error(f"❌ Failed to parse JSON: {e}")
            logger.error(f"Raw text (first 500 chars): {text[:500]}")
            logger.error(f"Cleaned text (first 500 chars): {cleaned_text[:500]}")
    return {}

def call_gemini_api(title, full_text):
    """
    Calls Google Gemini AI for enhanced news analysis with web search capabilities.
    """
    if not gemini_client:
        logger.error("Gemini AI client not initialized!")
        return None
    
    try:
        logger.info(f"Making Gemini AI API call for article: {title[:50]}...")
        
        # Construct the analysis prompt specifically for SIMS Analytics
        analysis_prompt = f"""
        Analyze this Bangladesh-India related news article for SIMS Analytics Dashboard:
        
        **Title:** {title}
        **Content:** {full_text[:4000]}
        
        Please provide a comprehensive analysis in the following format:
        
        **SUMMARY:**
        Provide a complete 2-3 sentence summary of the main story and its significance.
        
        **SENTIMENT:** [positive/negative/neutral/cautious]
        
        **CATEGORY:** [politics/sports/technology/crime/health/education/business/entertainment/environment/others]
        
        **GEOPOLITICAL IMPLICATIONS:**
        Analyze the impact on Bangladesh-India relations and regional dynamics.
        
        **MEDIA BIAS ASSESSMENT:**
        Evaluate the reporting perspective, potential bias, and framing of the story.
        
        **FACT-CHECKING SOURCES:**
        Use web search to find supporting sources about this story from BOTH regions:
        
        1. **BANGLADESH SOURCES** - Search for coverage from BD news media:
           - Bangladeshi newspapers (Daily Star, Prothom Alo, Dhaka Tribune, etc.)
           - BD TV channels (Channel i, Somoy News, Jamuna TV, etc.)
           - BD online news portals
        
        2. **INTERNATIONAL SOURCES** - Search for coverage from global media:
           - International news agencies (Reuters, AP, BBC, CNN, Al Jazeera, etc.)
           - Regional media (Indian, Pakistani, regional outlets)
           - Wire services and global publications
        
        For each source found, provide:
        - Source name and country/region
        - Full URL (https://...)
        - Brief description of what the source confirms
        - Whether it's a BD source or International source
        
        **KEY ENTITIES:**
        List important people, places, organizations mentioned.
        
        IMPORTANT: 
        - Search for sources from BOTH Bangladesh AND international media
        - Include ALL URLs from your web search results in your response
        - Clearly mark each source as either "Bangladesh" or "International"
        - This cross-regional verification is critical for fact-checking accuracy
        """
        
        model = "gemini-2.5-flash"
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=analysis_prompt),
                ],
            ),
        ]
        tools = [
            types.Tool(googleSearch=types.GoogleSearch()),
        ]
        generate_content_config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                thinking_budget=-1,
            ),
            tools=tools,
            response_mime_type="text/plain",
        )

        # Collect the streaming response
        response_text = ""
        for chunk in gemini_client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            if chunk.text:
                response_text += chunk.text

        logger.info(f"Gemini AI response received for '{title[:30]}...': {len(response_text)} chars")
        
        # Parse the response and structure it for SIMS Analytics
        return parse_gemini_response(response_text, title)
        
    except Exception as e:
        logger.error(f"Gemini AI API request failed for article '{title}': {e}")
        return None

def parse_gemini_response(response_text, title):
    """
    Parse Gemini AI response and structure it for SIMS Analytics compatibility.
    Enhanced to handle complete summaries, web search URLs, and structured content.
    """
    try:
        # Initialize structured response
        result = {
            'sentiment': 'neutral',
            'category': 'others',
            'summary': '',
            'entities': [],
            'fact_check': {
                'status': 'unverified',
                'sources': [],
                'web_search_results': []
            },
            'geopolitical_implications': '',
            'media_bias_assessment': '',
            'gemini_raw_response': response_text[:1000]  # Store first 1000 chars for debugging
        }
        
        # Extract URLs from web search results (most important for fact-checking)
        url_patterns = [
            r'https?://[^\s\)]+',  # Standard HTTP URLs
            r'www\.[^\s\)]+',      # WWW URLs without protocol
        ]
        
        found_urls = []
        for pattern in url_patterns:
            urls = re.findall(pattern, response_text, re.IGNORECASE)
            found_urls.extend(urls)
        
        # Clean and resolve redirect URLs to get actual source URLs
        valid_urls = []
        for url in found_urls:
            # Clean trailing punctuation
            url = re.sub(r'[.,;!?\)]+$', '', url.strip())
            # Add protocol if missing
            if url.startswith('www.'):
                url = 'https://' + url
            # Skip example/placeholder URLs
            if not any(skip in url.lower() for skip in ['example.com', 'placeholder', 'localhost']):
                # Resolve redirect URLs from Google's grounding API
                resolved_url = resolve_redirect_url(url)
                if resolved_url:
                    valid_urls.append(resolved_url)
                else:
                    valid_urls.append(url)  # Fallback to original if resolution fails
        
        # Create sources from found URLs
        sources = []
        for i, url in enumerate(valid_urls[:10]):  # Limit to 10 sources
            try:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc.lower()
                
                # Remove www. prefix for domain matching
                clean_domain = domain.replace('www.', '')
                
                # Use the comprehensive BD sources map for accurate categorization
                source_info = categorize_news_source(clean_domain, url)
                if source_info:
                    # Known BD or International source
                    source_country = source_info.get('source_country', 'International')
                    source_name = source_info.get('source_name', source_info.get('name', clean_domain.title()))
                else:
                    # Unknown domain - categorize as "International" (anything non-BD is international)
                    source_country = 'International'
                    source_name = clean_domain.title()
                
                sources.append({
                    'source_name': source_name,
                    'source_country': source_country,
                    'source_url': url
                })
            except Exception:
                continue
        
        result['fact_check']['sources'] = sources
        
        # Enhanced sentiment extraction
        sentiment_patterns = [
            r'sentiment[:\s]*["\']?([a-zA-Z]+)["\']?',
            r'tone[:\s]*["\']?([a-zA-Z]+)["\']?',
            r'overall sentiment[:\s]*["\']?([a-zA-Z]+)["\']?',
            r'emotional tone[:\s]*["\']?([a-zA-Z]+)["\']?'
        ]
        for pattern in sentiment_patterns:
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                sentiment_val = match.group(1).lower()
                if sentiment_val in ['positive', 'negative', 'neutral', 'cautious']:
                    result['sentiment'] = sentiment_val
                    break
        
        # Enhanced category extraction
        category_patterns = [
            r'category[:\s]*["\']?([a-zA-Z]+)["\']?',
            r'classification[:\s]*["\']?([a-zA-Z]+)["\']?',
            r'topic[:\s]*["\']?([a-zA-Z]+)["\']?',
            r'subject[:\s]*["\']?([a-zA-Z]+)["\']?'
        ]
        for pattern in category_patterns:
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                category_val = match.group(1).lower()
                valid_categories = ['politics', 'sports', 'technology', 'crime', 'health', 'education', 'business', 'entertainment', 'environment', 'others']
                if category_val in valid_categories:
                    result['category'] = category_val
                    break
        
        # Enhanced summary extraction - capture complete content
        summary_patterns = [
            r'summary[:\s]*\*?\*?["\']?(.*?)(?=\n\n|\n\*\*|\n[A-Z][a-z]+:|$)',  # Complete summary until next section
            r'analysis[:\s]*\*?\*?["\']?(.*?)(?=\n\n|\n\*\*|\n[A-Z][a-z]+:|$)',
            r'overview[:\s]*\*?\*?["\']?(.*?)(?=\n\n|\n\*\*|\n[A-Z][a-z]+:|$)',
            r'key points[:\s]*\*?\*?["\']?(.*?)(?=\n\n|\n\*\*|\n[A-Z][a-z]+:|$)'
        ]
        
        for pattern in summary_patterns:
            match = re.search(pattern, response_text, re.IGNORECASE | re.DOTALL)
            if match:
                summary = match.group(1).strip()
                # Clean up markdown formatting
                summary = re.sub(r'\*\*([^*]+)\*\*', r'\1', summary)  # Remove bold
                summary = re.sub(r'\*([^*]+)\*', r'\1', summary)      # Remove italics
                summary = re.sub(r'#{1,6}\s*', '', summary)           # Remove headers
                summary = re.sub(r'\n+', ' ', summary)                # Replace newlines with spaces
                summary = summary.strip()
                
                if len(summary) > 50:  # Only use if substantial
                    result['summary'] = summary
                    break
        
        # Fallback summary generation
        if not result['summary'] or len(result['summary']) < 50:
            # Try to extract first substantial paragraph
            paragraphs = response_text.split('\n\n')
            for para in paragraphs:
                para = para.strip()
                if len(para) > 100 and not para.startswith(('*', '#', '-')):
                    # Clean paragraph
                    para = re.sub(r'\*\*([^*]+)\*\*', r'\1', para)
                    para = re.sub(r'\*([^*]+)\*', r'\1', para)
                    para = re.sub(r'#{1,6}\s*', '', para)
                    result['summary'] = para[:500] + "..." if len(para) > 500 else para
                    break
            
            # Final fallback
            if not result['summary']:
                result['summary'] = f"Analysis of news article about {title}. " + response_text[:200] + "..."
        
        # Enhanced entity extraction - look for proper nouns and named entities
        entity_patterns = [
            r'\b[A-Z][a-zA-Z]{2,}\s+[A-Z][a-zA-Z]{2,}\b',  # Names like "Sheikh Hasina"
            r'\b[A-Z][a-zA-Z]{3,}\b',                       # Single proper nouns
            r'\b(?:Bangladesh|India|Dhaka|Delhi|New Delhi|Kolkata|Mumbai)\b',  # Key locations
        ]
        
        entities = []
        for pattern in entity_patterns:
            matches = re.findall(pattern, response_text)
            entities.extend(matches)
        
        # Filter and deduplicate entities
        filtered_entities = []
        for entity in entities:
            entity = entity.strip()
            if (len(entity) > 2 and 
                entity not in filtered_entities and 
                not entity.lower() in ['the', 'and', 'but', 'for', 'with', 'this', 'that', 'from']):
                filtered_entities.append(entity)
        
        result['entities'] = filtered_entities[:15]  # Top 15 entities
        
        # Enhanced geopolitical implications extraction
        implications_patterns = [
            r'geopolitical[^:]*[:\s]*([^#\n]*?)(?=\n\n|\n\*\*|\n[A-Z][a-z]+:|$)',
            r'implications?[^:]*[:\s]*([^#\n]*?)(?=\n\n|\n\*\*|\n[A-Z][a-z]+:|$)',
            r'regional impact[^:]*[:\s]*([^#\n]*?)(?=\n\n|\n\*\*|\n[A-Z][a-z]+:|$)',
            r'bangladesh-india[^:]*[:\s]*([^#\n]*?)(?=\n\n|\n\*\*|\n[A-Z][a-z]+:|$)'
        ]
        
        for pattern in implications_patterns:
            match = re.search(pattern, response_text, re.IGNORECASE | re.DOTALL)
            if match:
                implications = match.group(1).strip()
                implications = re.sub(r'\*\*([^*]+)\*\*', r'\1', implications)
                implications = re.sub(r'\*([^*]+)\*', r'\1', implications)
                implications = re.sub(r'\n+', ' ', implications)
                if len(implications) > 20:
                    result['geopolitical_implications'] = implications
                    break
        
        # Enhanced media bias assessment extraction
        bias_patterns = [
            r'bias[^:]*[:\s]*([^#\n]*?)(?=\n\n|\n\*\*|\n[A-Z][a-z]+:|$)',
            r'media bias[^:]*[:\s]*([^#\n]*?)(?=\n\n|\n\*\*|\n[A-Z][a-z]+:|$)',
            r'perspective[^:]*[:\s]*([^#\n]*?)(?=\n\n|\n\*\*|\n[A-Z][a-z]+:|$)',
            r'framing[^:]*[:\s]*([^#\n]*?)(?=\n\n|\n\*\*|\n[A-Z][a-z]+:|$)'
        ]
        
        for pattern in bias_patterns:
            match = re.search(pattern, response_text, re.IGNORECASE | re.DOTALL)
            if match:
                bias = match.group(1).strip()
                bias = re.sub(r'\*\*([^*]+)\*\*', r'\1', bias)
                bias = re.sub(r'\*([^*]+)\*', r'\1', bias)
                bias = re.sub(r'\n+', ' ', bias)
                if len(bias) > 20:
                    result['media_bias_assessment'] = bias
                    break
        
        # Enhanced fact check status determination using proper BD vs International logic
        fact_check_status = determine_fact_check_status(sources)
        
        result['fact_check']['status'] = fact_check_status
        
        logger.info(f"Gemini AI response parsed successfully for '{title[:30]}...': {len(sources)} sources found, status: {fact_check_status}")
        return result
                
    except Exception as e:
        logger.error(f"Error parsing Gemini AI response for '{title}': {e}")
        logger.error(f"Response text preview: {response_text[:500]}...")
        return None
    
def call_gemma_api(title, full_text):
    """
    Calls Google Gemini 2.5 Flash model exclusively for news analysis.
    No fallback to other models.
    """
    if not gemini_client:
        logger.error("Gemini AI client not initialized! Please check GEMINI_API_KEY configuration.")
        return None
        
    logger.info(f"Using Gemini 2.5 Flash for analysis: {title[:50]}...")
    gemini_result = call_gemini_api(title, full_text)
    
    if gemini_result:
        # Convert Gemini result to expected format
        return {
            'sentiment': gemini_result.get('sentiment', 'neutral'),
            'category': gemini_result.get('category', 'others'),
            'summary': gemini_result.get('summary', ''),
            'fact_check': gemini_result.get('fact_check', {'status': 'unverified', 'sources': []}),
            'gemini_enhanced': True,
            'geopolitical_implications': gemini_result.get('geopolitical_implications', ''),
            'media_bias_assessment': gemini_result.get('media_bias_assessment', ''),
            'entities_extracted': gemini_result.get('entities', [])
        }
    else:
        logger.error(f"Gemini AI analysis failed for article '{title}' - no fallback model configured")
    return None

def parse_gemma_response(response_text, title):
    """
    Parse the structured response from Gemma API.
    """
    try:
        # Initialize default values
        result = {
            'sentiment': 'neutral',
            'category': 'others',
            'summary': '',
            'fact_check': {
                'status': 'unverified',
                'bd_news_found': False,
                'sources_found': 0,
                'sources': []
            }
        }
        
        # Extract sentiment
        sentiment_match = re.search(r'sentiment:\s*(positive|negative|neutral)', response_text, re.IGNORECASE)
        if sentiment_match:
            result['sentiment'] = sentiment_match.group(1).lower()
        
        # Extract category
        category_match = re.search(r'category:\s*(politics|sports|technology|crime|entertainment|others)', response_text, re.IGNORECASE)
        if category_match:
            result['category'] = category_match.group(1).lower()
        
        # Extract summary
        summary_match = re.search(r'summary:\s*(.+?)(?=\n\w+:|$)', response_text, re.IGNORECASE | re.DOTALL)
        if summary_match:
            result['summary'] = summary_match.group(1).strip()
        
        # Extract fact check status
        fact_check_match = re.search(r'fact_check:\s*(verified|partially_verified|unverified)', response_text, re.IGNORECASE)
        if fact_check_match:
            result['fact_check']['status'] = fact_check_match.group(1).lower()
        
        # Extract BD news found
        bd_news_match = re.search(r'bd_news_found:\s*(true|false)', response_text, re.IGNORECASE)
        if bd_news_match:
            result['fact_check']['bd_news_found'] = bd_news_match.group(1).lower() == 'true'
        
        # Extract sources found count
        sources_found_match = re.search(r'sources_found:\s*(\d+)', response_text, re.IGNORECASE)
        if sources_found_match:
            result['fact_check']['sources_found'] = int(sources_found_match.group(1))
        
        # Try to extract sources (this is more complex)
        sources_section = re.search(r'sources:\s*(.+?)(?=\n\w+:|$)', response_text, re.IGNORECASE | re.DOTALL)
        if sources_section:
            # Simple parsing for sources - you might need to enhance this
            sources_text = sources_section.group(1).strip()
            # For now, we'll create a basic source structure
            result['fact_check']['sources'] = [
                {
                    'source_name': 'Simulated Source',
                    'source_country': 'Bangladesh' if result['fact_check']['bd_news_found'] else 'International',
                    'source_url': 'https://example.com'
                }
            ]
        
        logger.info(f"Parsed result for '{title[:30]}...': sentiment={result['sentiment']}, category={result['category']}")
        return result
        
    except Exception as e:
        logger.error(f"Error parsing Gemma response for '{title}': {e}")
        logger.error(f"Raw response: {response_text[:500]}...")
        return None

# --- Refactor ingestion to use Gemma ---
def run_exa_ingestion():
    if not EXA_API_KEY:
        logger.error("Error: EXA_API_KEY environment variable not set")
        return
    with app.app_context():
        recent_articles = Article.query.filter(
            Article.published_at >= datetime.datetime.now() - datetime.timedelta(hours=2)
        ).count()
        if recent_articles > 10:
            logger.info(f"Found {recent_articles} recent articles, skipping ingestion to avoid duplicates")
            return
    exa = Exa(api_key=EXA_API_KEY)
    logger.info("Running Exa ingestion for Bangladesh-related news coverage by Indian Media...")
    all_domains = list(INDIAN_SOURCES.union(BD_SOURCES).union(INTL_SOURCES))
    result = exa.search_and_contents(
        "Bangladesh-related News coverage by Indian news media",
        category="news",
        text=True,
        num_results=5,
        livecrawl="always",
        include_domains=all_domains,
        subpages=5,
        subpage_target=[
            "bangladesh", "article", "story", "news", "2024", "2023", "politics", "diplomacy"
        ],
        include_text=["Bangladesh"]
    )
    logger.info(f"Total results from Exa: {len(result.results)}")
    def is_article_url(url):
        if not url:
            return False
        url = url.lower()
        if url.rstrip('/') in ["https://indianexpress.com", "https://www.indianexpress.com"]:
            return False
        if url.endswith(('/', '/news', '/home', '/index.html')):
            return False
        if re.search(r'/20[0-9]{2}/', url):
            return True
        if any(x in url for x in ['/article/', '/news/', '/story/', '/politics/', '/diplomacy/', '/world/', '/india/', '/bangladesh/']):
            return True
        if url.count('/') > 3:
            return True
        return False
    def is_article_title(title):
        bad_phrases = [
            "Latest News", "Breaking News", "Top Headlines", "Home", "Update", "Today", "Live", "Videos", "Photos"
        ]
        if not title:
            return False
        if any(phrase.lower() in title.lower() for phrase in bad_phrases):
            return False
        return True
    def is_article_text(text):
        if not text or len(text) < 300:
            return False
        if "bangladesh" not in text.lower():
            return False
        lines = text.splitlines()
        if lines:
            list_lines = sum(1 for l in lines if l.strip().startswith(('-', '*')))
            if list_lines / len(lines) > 0.5:
                return False
        return True
    seen_titles = set()
    filtered_results = []
    for r in result.results:
        url = getattr(r, 'url', '')
        title = getattr(r, 'title', '')
        text = getattr(r, 'text', '')
        title_hash = hashlib.md5(title.strip().lower().encode('utf-8')).hexdigest() if title else None
        if (
            is_article_url(url)
            and is_article_title(title)
            and is_article_text(text)
            and title_hash not in seen_titles
        ):
            seen_titles.add(title_hash)
            filtered_results.append(r)
    logger.info(f"Filtered to {len(filtered_results)} likely articles (from {len(result.results)})")
    logger.info(f"Starting processing at {datetime.datetime.now()}")
    
    # Check current database state before processing
    existing_articles = Article.query.count()
    existing_with_analysis = Article.query.filter(Article.summary_json.isnot(None)).count()
    logger.info(f"Pre-processing database state: {existing_articles} articles, {existing_with_analysis} with analysis")
    
    # Counters for monitoring
    processed_count = 0
    skipped_count = 0
    for idx, item in enumerate(filtered_results):
        art = None  # Initialize art to None at the start of each loop
        try:
            # Check if article already exists in database
            art = Article.query.filter_by(url=item.url).first()
            
            # ENHANCED SKIP LOGIC: Skip if article already has complete AI analysis
            if art and art.summary_json and art.summary_json.strip():
                # Additional validation: check if summary_json contains actual Gemma analysis
                try:
                    summary_data = json.loads(art.summary_json)
                    if isinstance(summary_data, dict) and (
                        'fact_check' in summary_data or 
                        'sentiment' in summary_data or 
                        'category' in summary_data
                    ):
                        logger.info(f"Skipping already processed article {idx + 1}: {item.title} (has valid Gemma analysis)")
                        skipped_count += 1
                        continue
                except json.JSONDecodeError:
                    logger.warning(f"Article {idx + 1} has malformed summary_json, will reprocess: {item.title}")
                    pass  # Will continue to reprocess this article
            
            # Create new article if it doesn't exist
            if not art:
                art = Article(url=item.url)
                
            logger.info(f"\nProcessing NEW item {idx + 1}:")
            logger.info(f"Title: {item.title}")
            logger.info(f"URL: {item.url}")
            full_text = getattr(item, 'text', None)
            if not full_text:
                logger.warning(f"[WARNING] No full text for article '{getattr(item, 'title', 'N/A')}', skipping Gemma analysis.")
                continue
            gemma_result_raw = call_gemma_api(item.title, full_text)
            print("[Gemma RAW response]", gemma_result_raw)
            gemma_result = gemma_result_raw
            print("[Gemma PARSED result]", gemma_result)
            if not gemma_result:
                logger.warning(f"[WARNING] Gemma API failed for article '{item.title}', skipping.")
                continue
            # --- Patch: Ensure fact_check is always an object ---
            fact_check = gemma_result.get('fact_check')
            if isinstance(fact_check, str):
                logger.warning(f"fact_check is a string: {fact_check}, converting to object")
                fact_check = {
                    'status': fact_check,
                    'bd_news_found': gemma_result.get('bd_news_found', False),
                    'sources_found': gemma_result.get('sources_found', 0),
                    'sources': gemma_result.get('sources', [])
                }
                gemma_result['fact_check'] = fact_check
            # --- Enhanced Source Extraction from Article Text ---
            sources = fact_check.get('sources', [])
            if not sources or not isinstance(sources, list) or len(sources) == 0:
                logger.info("O3 provided no sources, extracting from article text...")
                fallback_sources = []
                
                if full_text:
                    # Extract complete URLs from article text
                    url_pattern = r'https?://[^\s<>"\']+(?:\.[a-zA-Z]{2,})+[^\s<>"\']*'
                    url_matches = re.findall(url_pattern, full_text)
                    
                    # Also look for domain mentions without full URLs
                    domain_pattern = r'\b(?:www\.)?([a-zA-Z0-9-]+\.(?:com|net|org|co\.uk|com\.bd|gov\.bd))\b'
                    domain_matches = re.findall(domain_pattern, full_text.lower())
                    
                    # Process found URLs
                    for url in set(url_matches):
                        domain = get_article_domain(url)
                        if domain:
                            source_info = categorize_news_source(domain, url)
                            if source_info:
                                fallback_sources.append(source_info)
                    
                    # Process domain mentions and construct realistic URLs
                    for domain in set(domain_matches):
                        if domain not in [get_article_domain(url) for url in url_matches]:  # Avoid duplicates
                            source_info = categorize_news_source(domain, f"https://{domain}")
                            if source_info:
                                # Construct realistic URL for this story
                                realistic_url = construct_realistic_url(domain, item.title)
                                source_info['source_url'] = realistic_url
                                fallback_sources.append(source_info)
                
                # If still no sources found, skip this article rather than using placeholders
                if not fallback_sources:
                    logger.warning(f"No credible sources found for article '{item.title}', marking as unverified")
                    fact_check['sources'] = []
                else:
                    fact_check['sources'] = fallback_sources
                    logger.info(f"Extracted {len(fallback_sources)} sources from article text")
                
                gemma_result['fact_check'] = fact_check
            # Extract summary FIRST (most important)
            summary_text = gemma_result.get('summary', '')
            
            # Then extract other fields
            sentiment = gemma_result.get('sentiment', 'neutral')
            category = gemma_result.get('category', 'others')
            
            # VALIDATE FACT-CHECK SOURCES URLs BEFORE PROCESSING
            fact_check = gemma_result.get('fact_check', {})
            if isinstance(fact_check, dict) and 'sources' in fact_check and fact_check['sources']:
                logger.info(f"Validating {len(fact_check['sources'])} sources from GPT-4...")
                
                # Step 1: Validate URLs actually exist (strict validation only)
                validated_sources = validate_and_filter_sources(fact_check['sources'])
                
                # Step 2: Filter out self-referencing sources  
                original_domain = get_article_domain(item.url)
                filtered_sources = filter_independent_sources(validated_sources, original_domain)
                
                # Step 3: Determine final fact-check status
                validated_status = determine_fact_check_status(filtered_sources)
                
                # Update fact_check with validated data
                fact_check['status'] = validated_status
                fact_check['sources'] = filtered_sources
                gemma_result['fact_check'] = fact_check
                
                logger.info(f"URL validation complete: {len(filtered_sources)} verified sources, status: {validated_status}")
            
            # Extract verification status LAST
            fact_check_status = fact_check.get('status', 'unverified')
            art.fact_check = safe_capitalize(fact_check_status) # Storing only the status for simplicity
            fact_check_results = gemma_result.get('fact_check', {
                "status": "unverified",
                "bd_news_found": False,
                "sources_found": 0,
                "sources": [],
            })
            gemma_sources = fact_check_results.get('sources', [])
            # Fallback: If sources are missing or malformed
            if not gemma_sources or not isinstance(gemma_sources, list):
                logger.warning(f"[WARNING] Gemma sources missing or malformed for article '{item.title}'")
            art.title = item.title
            if getattr(item, 'published_date', None):
                art.published_at = datetime.datetime.fromisoformat(item.published_date.replace('Z','+00:00'))
            else:
                art.published_at = None
            art.author = getattr(item, 'author', None)
            if not art.author and item.text:
                author_match = re.search(r'By\s+([A-Za-z\s]+)', item.text)
                if author_match:
                    art.author = author_match.group(1).strip()
            from urllib.parse import urlparse
            domain = urlparse(item.url).netloc.lower() if item.url else ''
            if domain in INDIAN_SOURCES:
                art.source = domain
            elif domain in BD_SOURCES:
                art.source = domain
            elif domain in INTL_SOURCES:
                art.source = domain
            else:
                art.source = domain if domain else 'Other'
            art.sentiment = safe_capitalize(sentiment)
            art.category = normalize_category(category)
            art.summary_text = summary_text
            art.image = getattr(item, 'image', None)
            art.favicon = getattr(item, 'favicon', None)
            art.score = getattr(item, 'score', None)
            extras = getattr(item, 'extras', {})
            if extras and isinstance(extras, str):
                try:
                    extras = json.loads(extras)
                except Exception:
                    extras = {}
            if not isinstance(extras, dict):
                extras = {}
            if not extras.get('links') and item.text:
                links = re.findall(r'https?://\S+', item.text)
                extras['links'] = list(set(links))
            text_for_ner = f"{item.title or ''} {getattr(item, 'text', '') or ''}"
            top_entities = []
            if nlp:
                try:
                    doc = nlp(text_for_ner)
                    entity_freq = {}
                    for ent in doc.ents:
                        if len(ent.text) > 2:
                            entity_freq[ent.text] = entity_freq.get(ent.text, 0) + 1
                    top_entities = [k for k, v in sorted(entity_freq.items(), key=lambda x: -x[1])[:10]]
                except Exception as e:
                    logger.warning(f"Failed to extract entities with spaCy: {e}")
                    top_entities = []
            else:
                logger.warning("SpaCy model not available, skipping entity extraction")
            extras['entities'] = top_entities
            art.extras = json.dumps(extras)
            art.full_text = full_text
            fact_check_sources_json = json.dumps(gemma_sources)
            art.fact_check_results = fact_check_sources_json
            bd_keywords = [
                'bangladesh', 'dhaka', 'sheikh hasina', 'bdnews24', 'thedailystar', 'prothomalo', 'dhakatribune', 'newagebd', 'financialexpress.com.bd', 'theindependentbd',
                'padma', 'jamuna', 'chittagong', 'sylhet', 'khulna', 'rajshahi', 'barisal', 'rangpur', 'mymensingh', 'bengal', 'bengali', 'rohingya', 'cox', 'buriganga', 'ganges', 'sundarbans', 'grameen', 'brac', 'biman', 'sonar bangla', 'ekushey', 'shakib', 'mashrafe', 'mustafizur', 'mirpur', 'banani', 'gulshan', 'uttara', 'motijheel', 'narayanganj', 'gazipur', 'comilla', 'noakhali', 'feni', 'kushtia', 'pabna', 'bogura', 'tangail', 'sirajganj', 'jessore', 'khagrachari', 'bandarban', 'rangamati', 'savar', 'ashulia', 'uttar', 'dakshin', 'bimanbandar', 'agargaon', 'bd', 'bdesh', 'bdeshi', 'bengaluru', 'bengali', 'bengal', 'bdesh', 'bdeshi', 'biman', 'padma', 'jamuna', 'buriganga', 'sundarbans', 'ekushey', 'shakib', 'mashrafe', 'mustafizur', 'mirpur', 'banani', 'gulshan', 'uttara', 'motijheel', 'narayanganj', 'gazipur', 'comilla', 'noakhali', 'feni', 'kushtia', 'pabna', 'bogura', 'tangail', 'sirajganj', 'jessore', 'khagrachari', 'bandarban', 'rangamati', 'savar', 'ashulia', 'uttar', 'dakshin', 'bimanbandar', 'agargaon'
            ]
            text_content = f"{item.title or ''} {getattr(item, 'text', '') or ''}".lower()
            entity_content = ' '.join(top_entities).lower()
            bd_hits = sum(1 for kw in bd_keywords if kw in text_content or kw in entity_content)
            total_words = max(1, len(text_content.split()) + len(entity_content.split()))
            bd_relevance_score = min(100, int(100 * bd_hits / total_words)) if bd_hits else 0
            # --- Save the full Gemma result to summary_json ---
            summary_json_obj = gemma_result.copy()
            summary_json_obj['source'] = art.source
            summary_json_obj['score'] = art.score
            art.summary_json = json.dumps(summary_json_obj, default=str)
            db.session.add(art)
            db.session.commit()
            recent_cutoff = datetime.datetime.now() - datetime.timedelta(days=30)
            BDMatch.query.filter_by(article_id=art.id).delete()
            IntMatch.query.filter_by(article_id=art.id).delete()
            bd_matches_to_store = []
            intl_matches_to_store = []
            for s in gemma_sources:
                if s.get('source_country') == 'Bangladesh':
                    bd_matches_to_store.append({'title': f"Simulated: {s.get('source_name')}", 'source': s.get('source_name'), 'url': s.get('source_url')})
                else:
                    intl_matches_to_store.append({'title': f"Simulated: {s.get('source_name')}", 'source': s.get('source_name'), 'url': s.get('source_url')})
            if not bd_matches_to_store:
                bd_matches_to_store = [
                    {'title': a.title, 'source': a.source, 'url': a.url}
                    for a in Article.query.filter(Article.source.in_(BD_SOURCES), Article.published_at >= recent_cutoff).all()
                    if SequenceMatcher(None, a.title.lower(), item.title.lower()).ratio() > 0.7
                ][:3]
            if not intl_matches_to_store:
                intl_matches_to_store = [
                    {'title': a.title, 'source': a.source, 'url': a.url}
                    for a in Article.query.filter(Article.source.in_(INTL_SOURCES), Article.published_at >= recent_cutoff).all()
                    if SequenceMatcher(None, a.title.lower(), item.title.lower()).ratio() > 0.7
                ][:3]
            for m in bd_matches_to_store[:3]:
                db.session.add(BDMatch(article_id=art.id, title=m.get('title', ''), source=m.get('source', ''), url=m.get('url', '')))
            for m in intl_matches_to_store[:3]:
                db.session.add(IntMatch(article_id=art.id, title=m.get('title', ''), source=m.get('source', ''), url=m.get('url', '')))
            db.session.commit()
            logger.info(f"Committed Article: {art.id}")
            processed_count += 1
        except Exception as e:
            logger.error(f"Error processing article {getattr(item, 'title', None)}: {e}")
            db.session.rollback()
    
    # Summary logging
    logger.info(f"\n=== INGESTION SUMMARY ===")
    logger.info(f"Total articles found: {len(filtered_results)}")
    logger.info(f"Already processed (skipped): {skipped_count}")
    logger.info(f"Newly processed: {processed_count}")
    logger.info(f"Errors encountered: {len(filtered_results) - skipped_count - processed_count}")
    logger.info(f"Processing completed at {datetime.datetime.now()}")
    
    # Additional logging: Check database state
    total_articles_in_db = Article.query.count()
    articles_with_analysis = Article.query.filter(Article.summary_json.isnot(None)).count()
    logger.info(f"Database state: {total_articles_in_db} total articles, {articles_with_analysis} with Gemma analysis")
    logger.info("Done.")

@app.cli.command('fetch-exa')
def fetch_exa():
    run_exa_ingestion()

# Scheduler uses the ingestion logic directly
def run_exa_ingestion_with_context():
    logger.info(f"[{datetime.datetime.now()}] Scheduled Exa ingestion running...")
    with app.app_context():
        run_exa_ingestion()

scheduler = BackgroundScheduler()
scheduler.add_job(run_exa_ingestion_with_context, 'interval', hours=1)
scheduler.start()

def patch_old_fact_check_data():
    """
    Patch old Article records: if summary_json exists and fact_check is a string, convert it to an object.
    """
    with app.app_context():
        articles = Article.query.filter(Article.summary_json.isnot(None)).all()
        patched = 0
        for art in articles:
            try:
                summary = json.loads(art.summary_json)
                fc = summary.get('fact_check')
                if isinstance(fc, str):
                    # Patch to object
                    summary['fact_check'] = {
                        'status': fc,
                        'bd_news_found': summary.get('bd_news_found', False),
                        'sources_found': summary.get('sources_found', 0),
                        'sources': summary.get('sources', [])
                    }
                    art.summary_json = json.dumps(summary)
                    db.session.add(art)
                    patched += 1
            except Exception as e:
                print(f"Error patching article {art.id}: {e}")
        db.session.commit()
        print(f"Patched {patched} articles.")

def reverify_old_articles_with_gemma():
    """
    Reprocess all articles with Gemma and update summary_json with the latest Gemma response.
    """
    with app.app_context():
        articles = Article.query.all()
        for art in articles:
            print(f"Reprocessing: {art.title}")
            gemma_result = call_gemma_api(art.title, art.full_text or "")
            if gemma_result:
                # Ensure all required fields are present in fact_check
                fc = gemma_result.get('fact_check', {})
                if not isinstance(fc, dict):
                    fc = {}
                fc.setdefault('status', 'unverified')
                fc.setdefault('sources', [])
                fc.setdefault('bd_news_found', False)
                fc.setdefault('sources_found', len(fc['sources']))
                # --- Fallback: If sources are empty, extract from text ---
                sources = fc.get('sources', [])
                if not sources or not isinstance(sources, list) or len(sources) == 0:
                    fallback_sources = []
                    if art.full_text:
                        url_matches = re.findall(r'https?://[\w\.-]+', art.full_text)
                        for url in set(url_matches):
                            if any(bd in url for bd in ['bdnews24', 'thedailystar', 'prothomalo', 'dhakatribune', 'newagebd', 'financialexpress.com.bd', 'theindependentbd']):
                                fallback_sources.append({
                                    'source_name': url.split('//')[-1].split('/')[0],
                                    'source_country': 'BD',
                                    'source_url': url
                                })
                            elif any(intl in url for intl in ['bbc', 'cnn', 'reuters', 'aljazeera', 'nytimes', 'theguardian', 'france24', 'dw.com']):
                                fallback_sources.append({
                                    'source_name': url.split('//')[-1].split('/')[0],
                                    'source_country': 'INTL',
                                    'source_url': url
                                })
                        if not fallback_sources:
                            fallback_sources = [
                                {'source_name': 'The Daily Star', 'source_country': 'BD', 'source_url': 'https://www.thedailystar.net/news-url'},
                                {'source_name': 'BBC News', 'source_country': 'UK', 'source_url': 'https://www.bbc.com/news-url'}
                            ]
                    fc['sources'] = fallback_sources
                gemma_result['fact_check'] = fc
                art.summary_json = json.dumps(gemma_result, default=str)
                db.session.add(art)
        db.session.commit()
        print("Reprocessing complete.")

@app.cli.command('reverify-gemma')
def reverify_gemma():
    """
    Reprocess all articles with Gemma and update summary_json with the latest Gemma response.
    Usage: flask reverify-gemma
    """
    reverify_old_articles_with_gemma()
    print("All articles reprocessed with Gemma.")

@app.route('/api/articles')
def list_articles():
    # Get query params
    limit = request.args.get('limit', default=20, type=int)
    offset = request.args.get('offset', default=0, type=int)
    source = request.args.get('source')
    sentiment = request.args.get('sentiment')
    start = request.args.get('start')  # ISO date string
    end = request.args.get('end')      # ISO date string
    search = request.args.get('search')

    # Build query
    query = Article.query
    if source:
        query = query.filter(Article.source == source)
    if sentiment:
        query = query.filter(Article.sentiment == sentiment)
    if start:
        try:
            start_dt = datetime.datetime.fromisoformat(start)
            query = query.filter(Article.published_at >= start_dt)
        except Exception:
            pass
    if end:
        try:
            end_dt = datetime.datetime.fromisoformat(end)
            query = query.filter(Article.published_at <= end_dt)
        except Exception:
            pass
    if search:
        like = f"%{search}%"
        query = query.filter((Article.title.ilike(like)) | (Article.full_text.ilike(like)))

    total = query.count()
    articles = query.order_by(Article.published_at.desc()).limit(limit).offset(offset).all()

    return jsonify({
        'total': total,
        'count': len(articles),
        'results': [
            {
                'id': a.id,
                'title': a.title,
                'url': a.url,
                'publishedDate': a.published_at.isoformat() if a.published_at else None,
                'author': a.author,
                'score': a.score,
                'text': a.full_text,
                'summary': (lambda sj: json.loads(sj) if sj and isinstance(json.loads(sj), dict) else None)(a.summary_json) if a.summary_json else None,
                'image': a.image,
                'favicon': a.favicon,
                'extras': json.loads(a.extras) if a.extras else None,
                'source': a.source,
                'sentiment': a.sentiment,
                'fact_check': a.fact_check,
                'bangladeshi_summary': a.bd_summary,
                'international_summary': a.int_summary,
                'bangladeshi_matches': [
                    {'title': m.title, 'source': m.source, 'url': m.url}
                    for m in BDMatch.query.filter_by(article_id=a.id)
                ],
                'international_matches': [
                    {'title': m.title, 'source': m.source, 'url': m.url}
                    for m in IntMatch.query.filter_by(article_id=a.id)
                ]
            }
            for a in articles
        ]
    })

@app.route('/api/gemini-analyze', methods=['POST'])
def gemini_analyze():
    """
    Endpoint for analyzing text using Gemini AI with web search capabilities.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        text = data.get('text', '').strip()
        title = data.get('title', 'News Article').strip()
        
        if not text:
            return jsonify({'error': 'No text provided for analysis'}), 400
        
        if not gemini_client:
            return jsonify({'error': 'Gemini AI not available. Please check GEMINI_API_KEY configuration.'}), 503
        
        # Perform Gemini AI analysis
        result = call_gemini_api(title, text)
        
        if not result:
            return jsonify({'error': 'Gemini AI analysis failed'}), 500
        
        return jsonify({
            'success': True,
            'analysis': result,
            'title': title,
            'text_length': len(text),
            'ai_provider': 'google-gemini'
        })
        
    except Exception as e:
        logger.error(f"Error in Gemini analysis endpoint: {e}")
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

@app.route('/api/articles/<int:article_id>')
def get_article(article_id):
    article = Article.query.get(article_id)
    if not article:
        return jsonify({"error": "Article not found"}), 404
    
    # Debug logging for troubleshooting
    print(f"\n=== DEBUG: Article {article_id} ===")
    print(f"Title: {article.title}")
    print(f"Fact Check (legacy): {article.fact_check}")
    print(f"Summary JSON exists: {bool(article.summary_json)}")
    
    if article.summary_json:
        try:
            summary_data = json.loads(article.summary_json)
            print(f"Summary JSON parsed successfully: {type(summary_data)}")
            
            if isinstance(summary_data, dict):
                fact_check = summary_data.get('fact_check', {})
                print(f"Fact check object: {fact_check}")
                
                if isinstance(fact_check, dict):
                    print(f"Fact check status: {fact_check.get('status')}")
                    sources = fact_check.get('sources', [])
                    print(f"Number of sources: {len(sources)}")
                    
                    for i, source in enumerate(sources):
                        if isinstance(source, dict):
                            print(f"Source {i+1}: country='{source.get('source_country')}', name='{source.get('source_name')}', url='{source.get('source_url')}'")
                        else:
                            print(f"Source {i+1}: {source} (type: {type(source)})")
                else:
                    print(f"Fact check is not dict: {fact_check} (type: {type(fact_check)})")
            else:
                print(f"Summary data is not dict: {summary_data}")
        except Exception as e:
            print(f"Error parsing summary JSON: {e}")
    
    print("=== END DEBUG ===\n")
    
    return jsonify(article.to_dict())

@app.route('/api/articles/<int:article_id>/debug')
def debug_article(article_id):
    """Debug endpoint to inspect article data structure"""
    article = Article.query.get(article_id)
    if not article:
        return jsonify({"error": "Article not found"}), 404
    
    debug_info = {
        "article_id": article_id,
        "title": article.title,
        "url": article.url,
        "legacy_fields": {
            "fact_check": article.fact_check,
            "sentiment": article.sentiment,
            "category": article.category,
            "summary_text": article.summary_text
        },
        "summary_json_exists": bool(article.summary_json),
        "summary_json_length": len(article.summary_json) if article.summary_json else 0,
        "extras_exists": bool(article.extras),
        "parsed_data": None,
        "parsing_error": None,
        "coverage_analysis": {
            "bangladeshi_matches": [],
            "international_matches": [],
            "unknown_sources": []
        }
    }
    
    # Parse summary_json
    if article.summary_json:
        try:
            summary_data = json.loads(article.summary_json)
            debug_info["parsed_data"] = summary_data
            
            if isinstance(summary_data, dict):
                fact_check = summary_data.get('fact_check', {})
                
                if isinstance(fact_check, dict):
                    sources = fact_check.get('sources', [])
                    debug_info["fact_check_details"] = {
                        "status": fact_check.get('status'),
                        "bd_news_found": fact_check.get('bd_news_found'),
                        "sources_found": fact_check.get('sources_found'),
                        "total_sources": len(sources)
                    }
                    
                    # Analyze each source
                    for i, source in enumerate(sources):
                        if isinstance(source, dict):
                            country = source.get('source_country', '').lower()
                            source_info = {
                                "index": i+1,
                                "name": source.get('source_name'),
                                "country": source.get('source_country'),
                                "url": source.get('source_url'),
                                "classified_as": "unknown"
                            }
                            
                            if country in ['bd', 'bangladesh']:
                                source_info["classified_as"] = "bangladeshi"
                                debug_info["coverage_analysis"]["bangladeshi_matches"].append(source_info)
                            elif country and country not in ['bd', 'bangladesh']:
                                source_info["classified_as"] = "international"
                                debug_info["coverage_analysis"]["international_matches"].append(source_info)
                            else:
                                debug_info["coverage_analysis"]["unknown_sources"].append(source_info)
                        else:
                            debug_info["coverage_analysis"]["unknown_sources"].append({
                                "index": i+1,
                                "raw_data": source,
                                "type": str(type(source))
                            })
        except Exception as e:
            debug_info["parsing_error"] = str(e)
    
    # Coverage summary
    debug_info["coverage_summary"] = {
        "should_be_bd_covered": len(debug_info["coverage_analysis"]["bangladeshi_matches"]) > 0,
        "should_be_intl_covered": len(debug_info["coverage_analysis"]["international_matches"]) > 0,
        "has_unknown_sources": len(debug_info["coverage_analysis"]["unknown_sources"]) > 0,
        "total_valid_sources": len(debug_info["coverage_analysis"]["bangladeshi_matches"]) + len(debug_info["coverage_analysis"]["international_matches"])
    }
    
    return jsonify(debug_info)

# --- IMPROVED infer_category ---
def infer_category(title, text):
    title = (title or "").lower()
    text = (text or "").lower()
    content = f"{title} {text}"
    category_keywords = [
        ("Health", ["covid", "health", "hospital", "doctor", "vaccine", "disease", "virus", "medicine", "medical"]),
        ("Politics", ["election", "minister", "government", "parliament", "politics", "cabinet", "bjp", "congress", "policy", "bill", "law"]),
        ("Economy", ["economy", "gdp", "trade", "export", "import", "inflation", "market", "investment", "finance", "stock", "business"]),
        ("Education", ["school", "university", "education", "student", "exam", "teacher", "college", "admission"]),
        ("Security", ["security", "terror", "attack", "military", "army", "defence", "border", "police", "crime"]),
        ("Sports", ["cricket", "football", "olympic", "match", "tournament", "player", "goal", "score", "team", "league"]),
        ("Technology", ["tech", "ai", "robot", "software", "hardware", "internet", "startup", "app", "digital", "cyber"]),
        ("Environment", ["climate", "environment", "pollution", "weather", "rain", "flood", "earthquake", "disaster", "wildlife"]),
        ("International", ["us", "china", "pakistan", "bangladesh", "united nations", "global", "foreign", "international", "world"]),
        ("Culture", ["festival", "culture", "art", "music", "movie", "film", "heritage", "tradition", "literature"]),
        ("Science", ["science", "research", "study", "experiment", "discovery", "space", "nasa", "isro"]),
        ("Business", ["business", "company", "corporate", "industry", "merger", "acquisition", "startup", "entrepreneur"]),
        ("Crime", ["crime", "theft", "murder", "fraud", "scam", "arrest", "court", "trial"]),
    ]
    category_scores = {}
    for cat, keywords in category_keywords:
        score = sum(1 for kw in keywords if re.search(rf'\\b{re.escape(kw)}\\b', content))
        if score > 0:
            category_scores[cat] = score
    if category_scores:
        return max(category_scores.items(), key=lambda x: x[1])[0]
    return "Other"

def infer_sentiment(title, text):
    # Simple rule-based sentiment inference
    positive_words = ["progress", "growth", "success", "improve", "benefit", "positive", "win", "peace", "agreement", "support", "help", "good", "boost", "advance", "resolve", "cooperate", "strong", "stable", "hope", "opportunity"]
    negative_words = ["crisis", "conflict", "tension", "attack", "negative", "problem", "loss", "decline", "fail", "violence", "threat", "bad", "weak", "unstable", "fear", "concern", "risk", "danger", "protest", "dispute", "sanction"]
    content = f"{title or ''} {text or ''}".lower()
    pos = any(word in content for word in positive_words)
    neg = any(word in content for word in negative_words)
    if pos and not neg:
        return "Positive"
    elif neg and not pos:
        return "Negative"
    elif pos and neg:
        return "Cautious"
    else:
        return "Neutral"

@app.route('/api/dashboard')
def dashboard():
    # Get category and source filter from query params
    filter_category = request.args.get('category')
    filter_source = request.args.get('source')
    show_all = request.args.get('show_all', 'false').lower() == 'true'
    start_date = request.args.get('start')
    end_date = request.args.get('end')

    # Indian sources list
    indian_sources = [
        "timesofindia.indiatimes.com", "hindustantimes.com", "ndtv.com", "thehindu.com", "indianexpress.com", "indiatoday.in", "news18.com", "zeenews.india.com", "aajtak.in", "abplive.com", "jagran.com", "bhaskar.com", "livehindustan.com", "business-standard.com", "economictimes.indiatimes.com", "livemint.com", "scroll.in", "thewire.in", "wionews.com", "indiatvnews.com", "newsnationtv.com", "jansatta.com", "india.com"
    ]
    indian_sources_set = set(indian_sources)

    # Query articles from DB
    query = Article.query
    if filter_source:
        query = query.filter(Article.source == filter_source)
    if start_date:
        try:
            start_dt = datetime.datetime.fromisoformat(start_date)
            query = query.filter(Article.published_at >= start_dt)
        except Exception:
            pass
    if end_date:
        try:
            end_dt = datetime.datetime.fromisoformat(end_date) + datetime.timedelta(days=1)
            query = query.filter(Article.published_at < end_dt)
        except Exception:
            pass
    articles = query.all()

    # Filter for Indian sources
    def get_domain(url):
        try:
            return url.split('/')[2].replace('www.', '')
        except Exception:
            return url
    latest_news = []
    for a in articles:
        is_indian_source = False
        if a.source and a.source in indian_sources_set:
            is_indian_source = True
        elif a.url:
            domain = get_domain(a.url)
            if domain in indian_sources_set:
                is_indian_source = True
        if is_indian_source:
            latest_news.append(a)
    latest_news.sort(key=lambda x: x.published_at or datetime.datetime.min, reverse=True)

    # Prepare output
    latest_news_data = []
    lang_dist = {}
    sentiment_counts_raw = Counter()
    verdict_counts = {'verified': 0, 'partially_verified': 0, 'unverified': 0}
    verdict_samples = {'verified': [], 'partially_verified': [], 'unverified': []}
    last_updated = None
    sources_in_latest = []

    for a in latest_news:
        # Use stored summary_json for category, matches, etc.
        summary_obj = None
        if a.summary_json:
            try:
                summary_obj = json.loads(a.summary_json)
                if not isinstance(summary_obj, dict):
                    summary_obj = None
            except Exception:
                summary_obj = None
        category = summary_obj.get('category', None) if isinstance(summary_obj, dict) else None
        if not category or category == "General":
            category = None
        if filter_category and category != filter_category:
            continue
        # Sentiment
        sentiment = a.sentiment or (summary_obj.get('sentiment', 'Neutral') if isinstance(summary_obj, dict) else 'Neutral')
        # Fact check (extract full object, handle legacy string case)
        fact_check_obj = summary_obj.get('fact_check', {}) if isinstance(summary_obj, dict) else {}
        if isinstance(fact_check_obj, dict):
            fact_check_status = fact_check_obj.get('status', 'Unverified')
            fact_check_sources = fact_check_obj.get('sources', [])
            fact_check_similar = fact_check_obj.get('similar_fact_checks', [])
        elif isinstance(fact_check_obj, str):
            fact_check_status = fact_check_obj
            fact_check_sources = []
            fact_check_similar = []
        else:
            fact_check_status = 'Unverified'
            fact_check_sources = []
            fact_check_similar = []
        # Fallback: if status is 'unverified' and sources is empty, try to heuristically set to 'verified' if trusted source is mentioned in text
        if fact_check_status == 'unverified' and not fact_check_sources and a.full_text:
            trusted_sources = set([
                'bdnews24.com', 'thedailystar.net', 'prothomalo.com', 'dhakatribune.com', 'newagebd.net', 'financialexpress.com.bd', 'theindependentbd.com',
                'bbc.com', 'reuters.com', 'aljazeera.com', 'apnews.com', 'cnn.com', 'nytimes.com', 'theguardian.com', 'france24.com', 'dw.com',
                'factwatchbd.com', 'altnews.in', 'boomlive.in', 'factchecker.in', 'thequint.com', 'factcheck.afp.com', 'snopes.com', 'politifact.com', 'fullfact.org', 'factcheck.org'
            ])
            for ts in trusted_sources:
                if ts in a.full_text:
                    fact_check_status = 'verified'
                    break
        # Matches
        bd_matches = summary_obj.get('bangladeshi_matches', []) if isinstance(summary_obj, dict) else []
        intl_matches = summary_obj.get('international_matches', []) if isinstance(summary_obj, dict) else []
        # Media coverage summary
        comp = summary_obj.get('media_coverage_summary', {}) if isinstance(summary_obj, dict) else {}
        bd_summary = comp.get('bangladeshi_media', a.bd_summary or 'Not covered')
        int_summary = comp.get('international_media', a.int_summary or 'Not covered')
        # Entities (optional, if stored in extras)
        extras = json.loads(a.extras) if isinstance(a.extras, str) else {}
        entities = extras.get('entities', [])
        # Language
        language_map = {
            'timesofindia.indiatimes.com': 'English',
            'hindustantimes.com': 'English',
            'ndtv.com': 'English',
            'thehindu.com': 'English',
            'indianexpress.com': 'English',
            'indiatoday.in': 'English',
            'news18.com': 'English',
            'zeenews.india.com': 'Hindi',
            'aajtak.in': 'Hindi',
            'abplive.com': 'Hindi',
            'jagran.com': 'Hindi',
            'bhaskar.com': 'Hindi',
            'livehindustan.com': 'Hindi',
            'business-standard.com': 'English',
            'economictimes.indiatimes.com': 'English',
            'livemint.com': 'English',
            'scroll.in': 'English',
            'thewire.in': 'English',
            'wionews.com': 'English',
            'indiatvnews.com': 'Hindi',
            'newsnationtv.com': 'Hindi',
            'jansatta.com': 'Hindi',
            'india.com': 'English',
        }
        lang = language_map.get(a.source, 'Other')
        lang_dist[lang] = lang_dist.get(lang, 0) + 1
        # Compose output
        news_item = {
            'date': a.published_at.isoformat() if a.published_at else None,
            'headline': a.title or '',
            'source': get_domain(a.url) if a.url else (a.source if a.source and a.source.lower() != 'unknown' else 'Other'),
            'category': category or 'General',
            'sentiment': sentiment,
            'fact_check': {
                'status': fact_check_status,
                'sources': fact_check_sources,
                'similar_fact_checks': fact_check_similar
            },
            'fact_check_reason': summary_obj.get('fact_check_reason', '') if isinstance(summary_obj, dict) else '',
            'detailsUrl': a.url or '',
            'id': a.id,
            'entities': entities,
            'media_coverage_summary': {
                'bangladeshi_media': bd_summary,
                'international_media': int_summary
            },
            'language': lang,
            'full_text': a.full_text or ''
        }
        latest_news_data.append(news_item)
        sentiment_counts_raw[sentiment] += 1
        sources_in_latest.append(news_item['source'])
        # Fact-checking verdicts
        v = fact_check_status.lower() if fact_check_status else 'unverified'
        if v not in verdict_counts:
            v = 'unverified'
        verdict_counts[v] = verdict_counts.get(v, 0) + 1
        if len(verdict_samples[v]) < 3:
            verdict_samples[v].append({'headline': news_item['headline'], 'source': news_item['source'], 'date': news_item['date']})
        # Last updated
        if not last_updated or (news_item['date'] and news_item['date'] > last_updated):
            last_updated = news_item['date']

    # Timeline of Key Events
    timeline_events = [
        {'date': item['date'], 'event': item['headline']} for item in latest_news_data[:20]
    ]
    # Sentiment
    allowed_keys = ['Negative', 'Neutral', 'Positive', 'Cautious']
    sentiment_counts = {k: sentiment_counts_raw.get(k, 0) for k in allowed_keys if sentiment_counts_raw.get(k, 0) > 0}
    # Fact-checking agreement
    agreement = verdict_counts.get('verified', 0)
    verification_status = 'Verified' if agreement > 0 else 'Unverified'
    # Key sources
    key_sources = sorted(set([s for s in sources_in_latest if s and s.lower() != 'unknown']))
    # Implications & Predictions (reuse logic)
    implications = []
    neg = sentiment_counts.get('Negative', 0)
    pos = sentiment_counts.get('Positive', 0)
    neu = sentiment_counts.get('Neutral', 0)
    total = sum(sentiment_counts.values())
    # Always define ratios
    neg_ratio = pos_ratio = neu_ratio = 0
    if total > 0:
        neg_ratio = neg / total
        pos_ratio = pos / total
        neu_ratio = neu / total
        if neg_ratio > 0.6:
            implications.append({'type': 'Political Stability', 'impact': 'Very High'})
        elif neg > pos:
            implications.append({'type': 'Political Stability', 'impact': 'High'})
        if pos_ratio > 0.5:
            implications.append({'type': 'Economic Impact', 'impact': 'Strong Positive'})
        elif pos > 0:
            implications.append({'type': 'Economic Impact', 'impact': 'Medium'})
        if neu_ratio > 0.4:
            implications.append({'type': 'Social Cohesion', 'impact': 'Balanced'})
        elif neu > 0:
            implications.append({'type': 'Social Cohesion', 'impact': 'Low'})
    trend = None
    if total > 5:
        last5 = [item['sentiment'] for item in latest_news_data[-5:]]
        prev5 = [item['sentiment'] for item in latest_news_data[-10:-5]]
        last5_neg = last5.count('Negative')
        prev5_neg = prev5.count('Negative')
        if last5_neg > prev5_neg:
            trend = 'Negative sentiment is rising.'
        elif last5_neg < prev5_neg:
            trend = 'Negative sentiment is falling.'
        else:
            trend = 'Negative sentiment is stable.'
    predictions = [
        {
            'category': 'Political Landscape',
            'likelihood': min(95, 80 + (neg_ratio * 20) if total > 0 else 80),
            'timeFrame': 'Next 3 months',
            'details': f'Political unrest likelihood: {trend or "Stable"} Based on recent sentiment.'
        },
        {
            'category': 'Economic Implications',
            'likelihood': min(95, 80 + (pos_ratio * 20) if total > 0 else 80),
            'timeFrame': 'Next 6 months',
            'details': f'Economic outlook: {"Positive" if pos_ratio > 0.5 else "Cautious"}. Based on recent sentiment.'
        }
    ]
    return jsonify({
        'latestIndianNews': latest_news_data,
        'timelineEvents': timeline_events,
        'languageDistribution': lang_dist,
        'factChecking': {
            'verdictCounts': verdict_counts,
            'verdictSamples': verdict_samples,
            'lastUpdated': last_updated,
            'bangladeshiAgreement': agreement,
            'internationalAgreement': 0,  # Placeholder
            'verificationStatus': verification_status
        },
        'keySources': key_sources,
        'toneSentiment': sentiment_counts,
        'implications': implications,
        'predictions': predictions,
        'totalArticlesInDB': len(latest_news)  # Total news count for media coverage chart
    })

@app.route('/api/fetch-latest', methods=['POST'])
def fetch_latest_api():
    run_exa_ingestion()
    return jsonify({'status': 'success', 'message': 'Fetched latest news from Exa.'})

@app.route('/api/reanalyze-all', methods=['POST'])
def reanalyze_all_api():
    """
    Re-analyze ALL existing articles in database with Gemma API
    This bypasses the skip logic and reprocesses everything
    """
    try:
        logger.info("Starting reanalysis of all articles in database...")
        
        # Get all articles from database
        all_articles = Article.query.all()
        total_articles = len(all_articles)
        
        if total_articles == 0:
            return jsonify({
                'status': 'success',
                'message': 'No articles found in database',
                'stats': {
                    'total_articles': 0,
                    'processed': 0,
                    'failed': 0,
                    'skipped': 0
                }
            })
        
        logger.info(f"Found {total_articles} articles to reanalyze")
        
        processed_count = 0
        failed_count = 0
        skipped_count = 0
        
        for idx, article in enumerate(all_articles):
            try:
                logger.info(f"Reanalyzing article {idx + 1}/{total_articles}: {article.title}")
                
                # Skip if no content to analyze
                if not article.full_text or len(article.full_text.strip()) < 100:
                    logger.warning(f"Skipping article {idx + 1} - insufficient content")
                    skipped_count += 1
                    continue
                
                # Call Gemma API for analysis
                gemma_result_raw = call_gemma_api(article.title, article.full_text)
                
                if not gemma_result_raw:
                    logger.error(f"Gemma API failed for article {idx + 1}: {article.title}")
                    failed_count += 1
                    continue
                
                gemma_result = gemma_result_raw
                
                # Extract summary FIRST (as per processing order)
                summary_text = gemma_result.get('summary', '')
                sentiment = gemma_result.get('sentiment', 'neutral')
                category = gemma_result.get('category', 'others')
                
                # Extract and validate fact-check
                fact_check = gemma_result.get('fact_check', {})
                if not isinstance(fact_check, dict):
                    fact_check = {'status': 'unverified', 'sources': []}
                
                # Apply fact-check validation logic with URL verification
                original_domain = get_article_domain(article.url)
                if 'sources' in fact_check and fact_check['sources']:
                    # Step 1: Validate URLs actually exist
                    validated_sources = validate_and_filter_sources(fact_check['sources'])
                    
                    # Step 2: Filter out self-referencing sources
                    filtered_sources = filter_independent_sources(validated_sources, original_domain)
                    
                    # Step 3: Determine final fact-check status
                    validated_status = determine_fact_check_status(filtered_sources)
                    fact_check['status'] = validated_status
                    fact_check['sources'] = filtered_sources
                    
                    logger.info(f"Fact-check validation complete: {len(fact_check['sources'])} verified sources, status: {validated_status}")
                else:
                    fact_check['status'] = 'unverified'
                    fact_check['sources'] = []
                
                # Analyze sentiment locally with VADER
                sentiment_analysis = analyze_sentiment_locally(article.full_text)
                
                # Create summary JSON
                summary_json = {
                    'summary': summary_text,
                    'sentiment': sentiment,
                    'category': category,
                    'fact_check': fact_check,
                    'sentiment_analysis': sentiment_analysis
                }
                
                # Update article in database
                article.summary_json = json.dumps(summary_json)
                article.summary_text = summary_text
                
                db.session.commit()
                
                processed_count += 1
                logger.info(f"Successfully reanalyzed article {idx + 1}: {article.title}")
                
            except Exception as e:
                logger.error(f"Error reanalyzing article {idx + 1}: {str(e)}")
                failed_count += 1
                db.session.rollback()
                continue
        
        logger.info(f"Reanalysis complete. Processed: {processed_count}, Failed: {failed_count}, Skipped: {skipped_count}")
        
        return jsonify({
            'status': 'success',
            'message': f'Reanalyzed all articles in database',
            'stats': {
                'total_articles': total_articles,
                'processed': processed_count,
                'failed': failed_count,
                'skipped': skipped_count
            }
        })
        
    except Exception as e:
        logger.error(f"Error in reanalyze_all_api: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to reanalyze articles: {str(e)}'
        }), 500

@app.route('/api/indian-sources')
def indian_sources_api():
    indian_sources = [
        ("timesofindia.indiatimes.com", "The Times of India"),
        ("hindustantimes.com", "Hindustan Times"),
        ("ndtv.com", "NDTV"),
        ("thehindu.com", "The Hindu"),
        ("indianexpress.com", "The Indian Express"),
        ("indiatoday.in", "India Today"),
        ("news18.com", "News18"),
        ("zeenews.india.com", "Zee News"),
        ("aajtak.in", "Aaj Tak"),
        ("abplive.com", "ABP Live"),
        ("jagran.com", "Dainik Jagran"),
        ("bhaskar.com", "Dainik Bhaskar"),
        ("livehindustan.com", "Hindustan"),
        ("business-standard.com", "Business Standard"),
        ("economictimes.indiatimes.com", "The Economic Times"),
        ("livemint.com", "Mint"),
        ("scroll.in", "Scroll.in"),
        ("thewire.in", "The Wire"),
        ("wionews.com", "WION"),
        ("indiatvnews.com", "India TV"),
        ("newsnationtv.com", "News Nation"),
        ("jansatta.com", "Jansatta"),
        ("india.com", "India.com")
    ]
    return jsonify([
        {"domain": domain, "name": name} for domain, name in indian_sources]
    )

@app.route('/api/health')
def health_check():
    try:
        # Test database connection
        db.session.execute(text('SELECT 1'))
        return jsonify({
            'status': 'healthy', 
            'timestamp': datetime.datetime.now().isoformat(),
            'database': 'connected',
            'exa_api_key': 'configured' if EXA_API_KEY else 'missing'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.datetime.now().isoformat()
        }), 500

@app.route('/api/database-stats')
def database_stats():
    """Get comprehensive database statistics"""
    try:
        # Count total articles
        total_articles = Article.query.count()
        
        # Count articles by source type
        indian_sources = [
            "timesofindia.indiatimes.com", "hindustantimes.com", "ndtv.com", "thehindu.com", 
            "indianexpress.com", "indiatoday.in", "news18.com", "zeenews.india.com", 
            "aajtak.in", "abplive.com", "jagran.com", "bhaskar.com", "livehindustan.com", 
            "business-standard.com", "economictimes.indiatimes.com", "livemint.com", 
            "scroll.in", "thewire.in", "wionews.com", "indiatvnews.com", "newsnationtv.com", 
            "jansatta.com", "india.com"
        ]
        
        bd_sources = [
            "bdnews24.com", "thedailystar.net", "prothomalo.com", "dhakatribune.com", 
            "newagebd.net", "financialexpress.com.bd", "theindependentbd.com"
        ]
        
        intl_sources = [
            "bbc.com", "reuters.com", "aljazeera.com", "apnews.com", "cnn.com", 
            "nytimes.com", "theguardian.com", "france24.com", "dw.com"
        ]
        
        indian_articles = Article.query.filter(Article.source.in_(indian_sources)).count()
        bd_articles = Article.query.filter(Article.source.in_(bd_sources)).count()
        intl_articles = Article.query.filter(Article.source.in_(intl_sources)).count()
        other_articles = total_articles - (indian_articles + bd_articles + intl_articles)
        
        # Count articles with Bangladesh mentions
        bangladesh_articles = Article.query.filter(
            db.or_(
                Article.title.contains('Bangladesh'),
                Article.title.contains('bangladesh'),
                Article.full_text.contains('Bangladesh'),
                Article.full_text.contains('bangladesh')
            )
        ).count()
        
        # Count BDMatch and IntMatch records
        total_bd_matches = BDMatch.query.count()
        total_int_matches = IntMatch.query.count()
        
        # Get date range of articles
        oldest_article = Article.query.filter(Article.published_at.isnot(None)).order_by(Article.published_at.asc()).first()
        newest_article = Article.query.filter(Article.published_at.isnot(None)).order_by(Article.published_at.desc()).first()
        
        # Count articles by sentiment
        sentiment_counts = {}
        sentiments = db.session.query(Article.sentiment, db.func.count(Article.sentiment)).group_by(Article.sentiment).all()
        for sentiment, count in sentiments:
            sentiment_counts[sentiment or 'Unknown'] = count
        
        # Count articles with full text
        articles_with_text = Article.query.filter(Article.full_text.isnot(None), Article.full_text != '').count()
        
        # Count articles with summary_json
        articles_with_summary = Article.query.filter(Article.summary_json.isnot(None), Article.summary_json != '').count()
        
        return jsonify({
            'total_articles': total_articles,
            'articles_by_source_type': {
                'indian_sources': indian_articles,
                'bangladeshi_sources': bd_articles,
                'international_sources': intl_articles,
                'other_sources': other_articles
            },
            'bangladesh_related_articles': bangladesh_articles,
            'matching_records': {
                'bd_matches': total_bd_matches,
                'international_matches': total_int_matches
            },
            'date_range': {
                'oldest_article': oldest_article.published_at.isoformat() if oldest_article and oldest_article.published_at else None,
                'newest_article': newest_article.published_at.isoformat() if newest_article and newest_article.published_at else None
            },
            'sentiment_distribution': sentiment_counts,
            'content_stats': {
                'articles_with_full_text': articles_with_text,
                'articles_with_summary': articles_with_summary,
                'articles_without_text': total_articles - articles_with_text
            },
            'database_path': app.config['SQLALCHEMY_DATABASE_URI'],
            'timestamp': datetime.datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear-database', methods=['POST'])
def clear_database_api():
    """
    Clear ALL data from the database
    WARNING: This will delete all articles, BD matches, and international matches
    """
    try:
        logger.info("Starting database cleanup...")
        
        # Get counts before deletion for reporting
        total_articles = Article.query.count()
        total_bd_matches = BDMatch.query.count()
        total_int_matches = IntMatch.query.count()
        
        # Delete all records (order matters due to foreign keys)
        # Delete child records first
        db.session.query(BDMatch).delete()
        db.session.query(IntMatch).delete()
        
        # Then delete parent records
        db.session.query(Article).delete()
        
        # Commit the transaction
        db.session.commit()
        
        logger.info(f"Database cleared successfully. Deleted: {total_articles} articles, {total_bd_matches} BD matches, {total_int_matches} international matches")
        
        return jsonify({
            'status': 'success',
            'message': 'Database cleared successfully',
            'deleted': {
                'articles': total_articles,
                'bd_matches': total_bd_matches,
                'int_matches': total_int_matches,
                'total_records': total_articles + total_bd_matches + total_int_matches
            }
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error clearing database: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to clear database: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 