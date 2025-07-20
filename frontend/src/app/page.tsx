"use client"

import { useState, useEffect, useMemo } from "react";
import axios from "axios";
import { format } from "date-fns";
import { Line, Pie, Bar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip as ChartTooltip,
  Legend,
  ArcElement,
  BarElement,
} from "chart.js";
import { FaCheckCircle, FaExclamationCircle, FaRegNewspaper, FaChartLine, FaCloud, FaNewspaper, FaGlobe, FaRobot } from "react-icons/fa";
import ChartDataLabels from "chartjs-plugin-datalabels";
import ReactWordcloud from 'react-wordcloud';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  ChartTooltip,
  Legend,
  ArcElement,
  BarElement,
  ChartDataLabels
);

const PAGE_SIZE = 10;

interface NewsItem {
  id: string;
  headline: string;
  date: string;
  url: string;
  news_category: string;
  category: string;
  sentiment: string;
  sentiment_toward_bangladesh: string;
  fact_check: {
    status: string;
    sources?: any[];
  };
  source_domain: string;
  source: string;
  bangladeshi_matches?: any[];
  international_matches?: any[];
  media_coverage_summary: {
    bangladeshi_media: string;
    international_media: string;
  };
  credibility_score: number;
  [key: string]: any; // Add index signature for dynamic property access
}

interface DashboardData {
  latestIndianNews: NewsItem[];
  languageDistribution: {
    [key: string]: number;
  };
  toneSentiment: {
    [key: string]: number;
  };
  implications: {
    type: string;
    impact: string;
  }[];
  predictions: {
    category: string;
    likelihood?: string;
    timeFrame?: string;
    details?: string;
  }[];
  factChecking: {
    bangladeshiAgreement?: number;
    internationalAgreement?: number;
    lastUpdated?: string;
    verdictCounts?: {
      [key: string]: number;
    };
    verdictSamples?: {
      [key: string]: any[];
    };
    verificationStatus?: string;
    [key: string]: any;
  };
  keySources?: string[];
  totalArticlesInDB?: number;  // Total articles count from backend
}

// Utility to get backend base URL
const getApiBase = () => {
  if (typeof window !== 'undefined') {
    const { protocol, hostname, port } = window.location;
    
    // If running on localhost, use port 5000 for backend
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return `${protocol}//${hostname}:5000`;
    }
    
    // For VM deployment, use the same hostname but port 5000
    // This assumes the backend is accessible on port 5000
    return `${protocol}//${hostname}:5000`;
  }
  return '';
};

// Utility function to strip TLD from domain
function stripTLD(domain: string) {
  if (!domain) return '';
  // Remove protocol if present
  domain = domain.replace(/^https?:\/\//, '');
  // Remove www. if present
  domain = domain.replace(/^www\./, '');
  // Remove TLDs
  return domain.replace(/\.(com|in|org|net|co|info|gov|edu|int|mil|biz|io|ai|news|tv|me|us|uk|bd|au|ca|pk|lk|np|my|sg|ph|id|cn|jp|kr|ru|fr|de|es|it|nl|se|no|fi|dk|pl|cz|tr|ir|sa|ae|qa|kw|om|bh|jo|lb|sy|iq|ye|il|za|ng|ke|gh|tz|ug|zm|zw|mu|mg|ma|dz|tn|ly|eg|sd|et|sn|cm|ci|gh|sl|gm|lr|bw|na|mz|ao|cd|cg|ga|gq|gw|st|cv|sc|km|eh|so|ss|cf|td|ne|ml|bf|bj|tg|gn|gw|mr|sm|va|mc|ad|li|gi|je|gg|im|fo|gl|sj|ax|eu|asia|cat|arpa|pro|museum|coop|aero|xxx|idv|mobi|name|jobs|travel|post|geo|tel|gov|edu|mil|int|arpa|root|test|example|invalid|localhost)(\.[a-z]{2,})?$/, '');
}

// --- Calculate top 5 weighted keywords per individual article ---
const getTopWeightedKeywords = (item: any) => {
  const text = `${item.headline || ''} ${item.full_text || ''}`.toLowerCase();
  // Common stop words to filter out
  const stopWords = new Set([
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their', 'said', 'says', 'also', 'more', 'very', 'what', 'when', 'where', 'who', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'from', 'up', 'out', 'down', 'off', 'over', 'under', 'again', 'further', 'then', 'once'
  ]);
  // Extract words and count frequency
  const words = text.match(/\b[a-z]{3,}\b/g) || [];
  const wordFreq: Record<string, number> = {};
  words.forEach(word => {
    if (!stopWords.has(word) && word.length >= 3) {
      wordFreq[word] = (wordFreq[word] || 0) + 1;
    }
  });
  // Combine with entities for better keyword extraction
  const entities = item.entities || [];
  entities.forEach((entity: string) => {
    const entityLower = entity.toLowerCase();
    // Count how many times this entity appears in the text
    const entityCount = (text.match(new RegExp(entityLower.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g')) || []).length;
    if (entityCount > 0) {
      wordFreq[entity] = entityCount;
    }
  });
  // Sort by frequency and return top 5
  return Object.entries(wordFreq)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([word, count]) => ({ word, count }));
};

  // --- NER Top Entities from backend - DYNAMIC based on selection ---
  const getNEREntities = (news: any[]) => {
    const freq: Record<string, number> = {};
    news.forEach(item => {
      // Try multiple possible field locations for entities
      const entities = 
        item.summary?.extras?.entities || 
        item.summary?.entities || 
        item.entities || 
        [];
      
      entities.forEach((entity: string) => {
        if (entity && entity.length > 2) freq[entity] = (freq[entity] || 0) + 1;
      });
    });
    return Object.entries(freq).sort((a, b) => b[1] - a[1]).slice(0, 35);
  };

// --- Robust Field Extraction Helpers ---
function capitalize(word: string) {
  return word?.charAt(0).toUpperCase() + word?.slice(1).toLowerCase();
}
function getCategory(item: any): string {
  const raw = item.summary?.category || item.category || "Unknown";
  return capitalize(raw);
}
function getSentiment(item: any): string {
  const raw = item.sentiment || item.summary?.sentiment || "Neutral";
  return capitalize(raw);
}
function getFactCheckStatus(item: any): string {
  // Robust fallback for fact check status
  const status = 
    item.summary?.fact_check_results?.status ||
    item.summary?.fact_check?.status ||
    item.fact_check?.status ||
    (typeof item.fact_check === 'string' ? item.fact_check : null) ||
    "unverified";
  return String(status).toLowerCase();
}
function getFactCheckSources(item: any): any[] {
  return item.summary?.fact_check_results?.sources || [];
}
function isCovered(item: any): boolean {
  const status = getFactCheckStatus(item);
  const sources = getFactCheckSources(item);
  return status === "verified" && sources.length > 0;
}
function getBangladeshiMatches(item: any): any[] {
  return item.bangladeshi_matches || [];
}
function getInternationalMatches(item: any): any[] {
  return item.international_matches || [];
}
function getEntities(item: any): string[] {
  return item.summary?.extras?.entities || [];
}
function getGemmaSources(item: any): any[] {
  return item.summary?.gemma_sources || [];
}
function getSummaryText(item: any): string {
  return item.summary?.summary_text || "No summary available";
}
function getScore(item: any): string {
  const score = item.score;
  return score === 0 || score === null ? "Not Available" : (typeof score === "number" ? score.toFixed(3) : "-");
}

// --- Color Maps for Badges and Charts ---
const sentimentColorMap: Record<string, string> = {
  Positive: "bg-green-100 text-green-700 border-green-300",
  Negative: "bg-red-100 text-red-700 border-red-300",
  Neutral: "bg-blue-100 text-blue-700 border-blue-300",
  Cautious: "bg-yellow-100 text-yellow-700 border-yellow-300",
};
const categoryColorMap: Record<string, string> = {
  Politics: "bg-blue-100 text-blue-700 border-blue-300",
  Crime: "bg-red-100 text-red-700 border-red-300",
  Environment: "bg-emerald-100 text-emerald-700 border-emerald-300",
  Health: "bg-green-100 text-green-700 border-green-300",
  Technology: "bg-pink-100 text-pink-700 border-pink-300",
  Diplomacy: "bg-indigo-100 text-indigo-700 border-indigo-300",
  Sports: "bg-orange-100 text-orange-700 border-orange-300",
  Culture: "bg-purple-100 text-purple-700 border-purple-300",
  General: "bg-gray-100 text-gray-700 border-gray-300",
  World: "bg-cyan-100 text-cyan-700 border-cyan-300",
  SouthAsia: "bg-teal-100 text-teal-700 border-teal-300",
  India: "bg-indigo-100 text-indigo-700 border-indigo-300",
  Bangladesh: "bg-green-100 text-green-700 border-green-300",
  Religion: "bg-fuchsia-100 text-fuchsia-700 border-fuchsia-300",
  Business: "bg-yellow-100 text-yellow-700 border-yellow-300",
  Science: "bg-blue-100 text-blue-700 border-blue-300",
  Education: "bg-lime-100 text-lime-700 border-lime-300",
  Opinion: "bg-gray-200 text-gray-800 border-gray-400",
  Other: "bg-gray-100 text-gray-700 border-gray-300",
};
const factCheckColorMap: Record<string, string> = {
  verified: "bg-green-100 text-green-700 border-green-300",
  unverified: "bg-gray-100 text-gray-700 border-gray-300",
  true: "bg-green-100 text-green-700 border-green-300",
  false: "bg-red-100 text-red-700 border-red-300",
  mixed: "bg-yellow-100 text-yellow-700 border-yellow-300",
  True: "bg-green-100 text-green-700 border-green-300",
  False: "bg-red-100 text-red-700 border-red-300",
  Mixed: "bg-yellow-100 text-yellow-700 border-yellow-300",
};

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<string>("date");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(1);
  const [dateRange, setDateRange] = useState<{ start: string; end: string }>({ start: "", end: "" });
  const [tableLoading, setTableLoading] = useState(false);
  const [source, setSource] = useState<string>("");
  const [sources, setSources] = useState<{ domain: string, name: string }[]>([]);
  const [sentimentFilter, setSentimentFilter] = useState<string>("");
  const [keywordFilter, setKeywordFilter] = useState<string>("");
  const [factCheckTooltip, setFactCheckTooltip] = useState<{ show: boolean, text: string, x: number, y: number }>({ show: false, text: '', x: 0, y: 0 });
  const [categoryFilter, setCategoryFilter] = useState<string>("");
  const categoryOptions = useMemo(() => {
    const catSet = new Set((data?.latestIndianNews || []).map((item: any) => getCategory(item)).filter(Boolean));
    return ["", ...Array.from(catSet) as string[]];
  }, [data]);
  const sentimentOptions = ["", "Positive", "Negative", "Neutral", "Cautious"];
  const [selectedEntity, setSelectedEntity] = useState<string>("");
  const [showFactCheck, setShowFactCheck] = useState(false);
  const [showMediaCoverage, setShowMediaCoverage] = useState(false);
  const [showMediaComparison, setShowMediaComparison] = useState(false);
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [showCredibility, setShowCredibility] = useState(false);
  const [showClustering, setShowClustering] = useState(false);
  const [showBias, setShowBias] = useState(false);
  const [showImplications, setShowImplications] = useState(false);
  const [showPredictions, setShowPredictions] = useState(false);
  const [showFactChecking, setShowFactChecking] = useState(false);
  const [showKeySources, setShowKeySources] = useState(false);
  const [showCustomReport, setShowCustomReport] = useState(false);
  const [showAll, setShowAll] = useState(false);

  // Fetch Indian sources for dropdown
  useEffect(() => {
    const fetchSources = async () => {
      try {
        const response = await axios.get(`${getApiBase()}/api/indian-sources`, {
          timeout: 5000,
          headers: {
            'Content-Type': 'application/json',
          }
        });
        setSources(response.data as { domain: string; name: string; }[]);
      } catch (err: any) {
        console.error('Failed to fetch sources:', err);
        // Don't set error state here as it's not critical for main functionality
      }
    };
    fetchSources();
  }, []);

  // Fetch dashboard data
  const fetchDashboard = async (range = dateRange, src = source) => {
    setLoading(true);
    setError(null);
    try {
      const params: any = {};
      if (range.start) params.start = range.start;
      if (range.end) params.end = range.end;
      if (src) params.source = src;
      if (showAll) params.show_all = 'true';
      
      const apiUrl = `${getApiBase()}/api/dashboard`;
      console.log('Fetching from:', apiUrl);
      
      const response = await axios.get(apiUrl, { 
        params,
        timeout: 10000, // 10 second timeout
        headers: {
          'Content-Type': 'application/json',
        }
      });
      
      console.log('Dashboard API response:', response.data);
      
      // Add comprehensive data structure logging
      if (response.data && (response.data as any).latestIndianNews) {
        const data = response.data as any;
        console.log('Sample article structure:', data.latestIndianNews[0]);
        console.log('Articles with summary:', data.latestIndianNews.filter((item: any) => item.summary));
        console.log('Articles with entities:', data.latestIndianNews.filter((item: any) => 
          item.summary?.extras?.entities || item.summary?.entities || item.entities
        ));
        console.log('Articles with media coverage:', data.latestIndianNews.filter((item: any) => 
          item.summary?.supportingArticleMatches || item.summary?.supporting_article_matches || item.bangladeshi_matches
        ));
        console.log('Articles with fact check:', data.latestIndianNews.filter((item: any) => 
          item.summary?.fact_check_results || item.fact_check
        ));
      }
      
      setData(response.data as DashboardData);
    } catch (err: any) {
      console.error('API Error:', err);
      if (err.code === 'ECONNREFUSED') {
        setError("Cannot connect to backend server. Please check if the backend is running on port 5000.");
      } else if (err.response?.status === 404) {
        setError("API endpoint not found. Please check the backend configuration.");
      } else if (err.response?.status >= 500) {
        setError("Backend server error. Please check the server logs.");
      } else {
        setError(`Failed to fetch dashboard data: ${err.message || 'Unknown error'}`);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
    // eslint-disable-next-line
  }, []);

  // Refetch data when showAll changes
  useEffect(() => {
    if (data) { // Only refetch if we already have data loaded
      fetchDashboard();
    }
    // eslint-disable-next-line
  }, [showAll]);

  // Table sorting
  const handleSort = (col: string) => {
    if (sortBy === col) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortBy(col);
      setSortDir("asc");
    }
    setPage(1);
  };

  // Heuristics for bogus news
  const BAD_TITLE_PHRASES = [
    "latest news", "breaking news", "top headlines", "home", "update", "today", "live", "videos", "photos"
  ];
  function isBogus(article: any) {
    const title = (article.headline || article.title || '').toLowerCase();
    const text = (article.text || '').toLowerCase();
    if (BAD_TITLE_PHRASES.some(phrase => title.includes(phrase))) return true;
    // If text is missing or short, fallback to title for Bangladesh check
    if ((!text || text.length < 100) && !title.includes("bangladesh")) return true;
    // If text is present and long enough, require Bangladesh in text
    if (text.length >= 100 && !text.includes("bangladesh")) return true;
    return false;
  }
  // Filtered and deduped news
  const filteredNews = useMemo(() => {
    if (!data?.latestIndianNews) return [];
    const seenTitles = new Set();
    let filtered = [];
    for (const article of data.latestIndianNews) {
      const normTitle = (article.headline || article.title || '').trim().toLowerCase();
      if (!normTitle || seenTitles.has(normTitle)) continue;
      if (isBogus(article)) continue;
      seenTitles.add(normTitle);
      filtered.push(article);
    }
    // Apply UI filters
    if (selectedEntity) {
      filtered = filtered.filter(item => (item.entities || []).includes(selectedEntity));
    }
    if (sentimentFilter) {
      filtered = filtered.filter(item => {
        const itemSentiment = getSentiment(item);
        return itemSentiment === sentimentFilter;
      });
    }
    if (categoryFilter) {
      filtered = filtered.filter(item => {
        const itemCategory = getCategory(item);
        return itemCategory === categoryFilter;
      });
    }
    if (keywordFilter) filtered = filtered.filter(item => (item.headline || '').toLowerCase().includes(keywordFilter.toLowerCase()));
    return filtered;
  }, [data, selectedEntity, sentimentFilter, categoryFilter, keywordFilter]);

  // Global filtered dataset for ALL dashboard components
  const globalFilteredNews = useMemo(() => {
    if (!data?.latestIndianNews) return [];
    let filtered = [...data.latestIndianNews];
    if (selectedEntity) {
      filtered = filtered.filter(item => (item.entities || []).includes(selectedEntity));
    }
    if (sentimentFilter) {
      filtered = filtered.filter(item => {
        const itemSentiment = getSentiment(item);
        return itemSentiment === sentimentFilter;
      });
    }
    if (categoryFilter) {
      filtered = filtered.filter(item => {
        const itemCategory = getCategory(item);
        return itemCategory === categoryFilter;
      });
    }
    if (keywordFilter) filtered = filtered.filter(item => (item.headline || '').toLowerCase().includes(keywordFilter.toLowerCase()));
    return filtered;
  }, [data, selectedEntity, sentimentFilter, categoryFilter, keywordFilter]);

  const paginatedNews = () => {
    let sorted = [...filteredNews];
    sorted.sort((a, b) => {
      let aVal = a[sortBy] || "";
      let bVal = b[sortBy] || "";
      if (sortBy === "date") {
        aVal = aVal ? new Date(aVal).getTime() : 0;
        bVal = bVal ? new Date(bVal).getTime() : 0;
      }
      if (aVal < bVal) return sortDir === "asc" ? -1 : 1;
      if (aVal > bVal) return sortDir === "asc" ? 1 : -1;
      return 0;
    });
    
    // If showAll is true, return all sorted data, otherwise return paginated data
    if (showAll) {
      return sorted;
    }
    
    const startIdx = (page - 1) * PAGE_SIZE;
    return sorted.slice(startIdx, startIdx + PAGE_SIZE);
  };

  // Date range filter
  const handleDateChange = (e: any) => {
    setDateRange({ ...dateRange, [e.target.name]: e.target.value });
  };
  const handleDateFilter = async () => {
    setTableLoading(true);
    await fetchDashboard(dateRange);
    setTableLoading(false);
    setPage(1);
  };

  // --- Media Coverage Distribution using bangladeshi_matches and international_matches ---
  const mediaCoverageCounts = useMemo(() => {
    let totalBD = 0, totalIntl = 0, bothCovered = 0;
    let totalCoveredArticles = 0;
    
    globalFilteredNews.forEach((item: any) => {
      // Use the bangladeshi_matches and international_matches arrays directly
      const bdMatches = item.bangladeshi_matches || [];
      const intlMatches = item.international_matches || [];
      
      const hasBD = bdMatches.length > 0;
      const hasIntl = intlMatches.length > 0;
      
      // Count articles that have any coverage
      if (hasBD || hasIntl) {
        totalCoveredArticles++;
      }
      
      // Count total BD coverage (including those also covered internationally)
      if (hasBD) totalBD++;
      
      // Count total International coverage (including those also covered by BD)
      if (hasIntl) totalIntl++;
      
      // Count articles covered by both
      if (hasBD && hasIntl) bothCovered++;
    });
    
    // Get total news count from backend or fallback to current filtered count
    const totalNews = data?.totalArticlesInDB || globalFilteredNews.length;
    
    return { 
      totalBD, 
      totalIntl, 
      bothCovered, 
      totalCoveredArticles,
      totalNews,
      // Calculate percentages based on TOTAL NEWS (not just covered articles)
      bdPercentage: totalNews > 0 ? (totalBD / totalNews * 100).toFixed(1) : 0,
      intlPercentage: totalNews > 0 ? (totalIntl / totalNews * 100).toFixed(1) : 0,
      bothPercentage: totalNews > 0 ? (bothCovered / totalNews * 100).toFixed(1) : 0,
      totalPercentage: '100.0' // Always 100% for total news bar
    };
  }, [globalFilteredNews, data?.totalArticlesInDB]);
  
  const mediaCoverageLabels = [
    'Total News',
    'BD Covered',
    'International Covered',
    'Both Covered',
  ];
  const mediaCoverageValues = [
    mediaCoverageCounts.totalNews,  // Actual count for total news
    parseFloat(mediaCoverageCounts.bdPercentage as string),
    parseFloat(mediaCoverageCounts.intlPercentage as string),
    parseFloat(mediaCoverageCounts.bothPercentage as string),
  ];
  const mediaCoverageColors = ['#6b7280', '#0ea5e9', '#f59e42', '#22c55e']; // Gray for total, existing colors for coverage
  const mediaCoverageChartData = {
    labels: mediaCoverageLabels,
    datasets: [
      {
        label: 'Coverage Percentage',
        data: mediaCoverageValues,
        backgroundColor: mediaCoverageColors,
      },
    ],
  };

  // Sentiment color map for charts and badges
  const sentimentChartColorMap: Record<string, string> = {
    Positive: "#22c55e",   // green
    Negative: "#ef4444",   // red
    Neutral: "#3b82f6",    // blue
    Cautious: "#fbbf24",   // yellow
  };

  // Sentiment Pie Chart Data - using GLOBAL filtered data
  const sentimentCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    globalFilteredNews.forEach((item: any) => {
      // Use the helper function to get sentiment from new API structure
      const sentiment = getSentiment(item);
      counts[sentiment] = (counts[sentiment] || 0) + 1;
    });
    return counts;
  }, [globalFilteredNews]);
  const sentimentLabels = Object.keys(sentimentCounts);
  const sentimentValues = Object.values(sentimentCounts);
  const sentimentChartData = {
    labels: sentimentLabels,
    datasets: [
      {
        label: "Sentiment",
        data: sentimentValues,
        backgroundColor: sentimentLabels.map(label => sentimentChartColorMap[label] || "#a3a3a3"),
      },
    ],
  };

  // --- FactCheck Pie Chart Data - using GLOBAL filtered data ---
  const factCheckCounts = useMemo(() => {
    const counts: Record<string, number> = { verified: 0, unverified: 0 };
    globalFilteredNews.forEach((item: any) => {
      // Use the helper function to get fact check status from new API structure
      const status = getFactCheckStatus(item);
              // Count verified and unverified categories
        if (status === 'verified') {
          counts.verified++;
        } else {
          counts.unverified++;
        }
    });
    return counts;
  }, [globalFilteredNews]);
  const factCheckLabels = Object.keys(factCheckCounts);
  const factCheckValues = Object.values(factCheckCounts);
  const factCheckPieData = {
    labels: factCheckLabels.map(l => l.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())),
    datasets: [
      {
        data: factCheckValues,
        backgroundColor: factCheckLabels.map(l => 
          l === 'verified' ? '#22c55e' :     // Green for verified
          '#9ca3af'   // Gray for unverified
        ),
      },
    ],
  };

  // --- Category Bar Chart Data - using GLOBAL filtered data ---
  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    globalFilteredNews.forEach((item: any) => {
      // Use the helper function to get category from new API structure
      const val = getCategory(item);
      counts[val] = (counts[val] || 0) + 1;
    });
    return counts;
  }, [globalFilteredNews]);
  const categoryLabels = Object.keys(categoryCounts);
  const categoryValues = Object.values(categoryCounts);
  const langBarOptions = {
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: function (context: any) {
            const label = context.label || "";
            const value = context.parsed.y;
            const total = context.dataset.data.reduce((a: number, b: number) => a + b, 0);
            const percent = total ? ((value / total) * 100).toFixed(1) : 0;
            return `${label}: ${value} (${percent}%)`;
          },
        },
      },
      datalabels: {
        display: true,
        color: "#222",
        font: { weight: "bold" as const },
        anchor: "end" as const,
        align: "top" as const,
        formatter: (value: number, ctx: any) => {
          const total = ctx.chart.data.datasets[0].data.reduce((a: number, b: number) => a + b, 0);
          return total ? `${((value / total) * 100).toFixed(1)}%` : '';
        },
      },
    },
    maintainAspectRatio: false,
    responsive: true,
    scales: {
      y: { beginAtZero: true, ticks: { stepSize: 10 } },
    },
  };
  const categoryBarData = {
    labels: categoryLabels,
    datasets: [
      {
        label: 'Articles',
        data: categoryValues,
        backgroundColor: '#3b82f6',
      },
    ],
  };

  // --- NER Top Entities from backend - DYNAMIC based on selection ---
  const nerKeywords = useMemo(() => {
    if (selectedEntity) {
      // Show only the selected entity with a count of 1 for display
      return [[selectedEntity, 1]];
    } else {
      // Show all entities from the filtered news (responds to all filters)
      const entities = getNEREntities(filteredNews);
      if (entities.length > 0) {
        return entities;
      }
      // Fallback: use keywords from getTopWeightedKeywords if no entities found
      const keywordFreq: Record<string, number> = {};
      filteredNews.forEach(item => {
        getTopWeightedKeywords(item).forEach(({ word, count }: { word: string, count: number }) => {
          keywordFreq[word] = (keywordFreq[word] || 0) + count;
        });
      });
      return Object.entries(keywordFreq).sort((a, b) => b[1] - a[1]).slice(0, 35);
    }
  }, [filteredNews, selectedEntity]);

  // Add back getSentimentStats with correct color mapping - using GLOBAL filtered data
  const getSentimentStats = (filteredNews: any[]) => {
    const sentimentCounts: Record<string, number> = {};
    filteredNews.forEach((item: any) => {
      // Use the helper function to get sentiment from new API structure
      const sentiment = getSentiment(item);
      sentimentCounts[sentiment] = (sentimentCounts[sentiment] || 0) + 1;
    });
    
    return [
      { label: "Positive", value: sentimentCounts.Positive || 0, color: "bg-green-100 text-green-700", icon: <FaCheckCircle className="text-green-500" /> },
      { label: "Negative", value: sentimentCounts.Negative || 0, color: "bg-red-100 text-red-700", icon: <FaExclamationCircle className="text-red-500" /> },
      { label: "Neutral", value: sentimentCounts.Neutral || 0, color: "bg-blue-100 text-blue-700", icon: <FaRegNewspaper className="text-gray-500" /> },
      { label: "Cautious", value: sentimentCounts.Cautious || 0, color: "bg-yellow-100 text-yellow-700", icon: <FaRegNewspaper className="text-yellow-500" /> },
    ];
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-red-600 text-xl">{error || "No data available."}</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-2 md:px-4 py-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-8 bg-white p-4 rounded-xl shadow">
        <div className="flex items-center gap-4">
          <h1 className="text-4xl font-extrabold mb-4 md:mb-0 whitespace-nowrap">SIMS Analytics Dashboard</h1>
          <a
            href="/gemini-test"
            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors text-sm font-medium flex items-center gap-2"
            title="Test Gemini 2.5 Flash Analysis"
          >
            <FaGlobe />
            Gemini 2.5 Flash
          </a>
        </div>
        <div className="flex flex-wrap gap-1 items-center justify-end">
          <input type="date" name="start" value={dateRange.start} onChange={handleDateChange} className="border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400 transition" />
          <span className="font-bold text-base">-</span>
          <input type="date" name="end" value={dateRange.end} onChange={handleDateChange} className="border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400 transition" />
          <label htmlFor="source" className="font-medium ml-1 text-sm">Source:</label>
          <select
            id="source"
            className="border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400 transition"
            value={source}
            onChange={async (e) => {
              setSource(e.target.value);
              setPage(1);
              await fetchDashboard(dateRange, e.target.value);
            }}
          >
            <option value="">All</option>
            {sources.map((src) => (
              <option key={src.domain} value={src.domain}>{src.name}</option>
            ))}
          </select>
          <label htmlFor="sentiment" className="font-medium ml-1 text-sm">Sentiment:</label>
          <select
            id="sentiment"
            className="border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400 transition"
            value={sentimentFilter}
            onChange={e => { setSentimentFilter(e.target.value); setPage(1); }}
          >
            <option value="">All</option>
            <option value="Positive">Positive</option>
            <option value="Negative">Negative</option>
            <option value="Neutral">Neutral</option>
            <option value="Cautious">Cautious</option>
          </select>
          <label htmlFor="category" className="font-medium ml-1 text-sm">Category:</label>
          <select
            id="category"
            className="border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400 transition"
            value={categoryFilter}
            onChange={e => { setCategoryFilter(e.target.value); setPage(1); }}
          >
            <option value="">All</option>
            {categoryOptions.filter(opt => opt).map(opt => {
              const val = String(opt);
              return <option key={val} value={val}>{val}</option>;
            })}
          </select>
          <button className="bg-primary-600 text-white font-semibold px-4 py-1.5 rounded shadow hover:bg-primary-700 transition ml-1 text-sm" onClick={handleDateFilter} disabled={tableLoading}>
            {tableLoading ? "Loading..." : "Update Now"}
          </button>
          <button
            className="ml-1 px-4 py-1.5 rounded border border-gray-300 bg-white text-gray-700 font-semibold hover:bg-gray-100 transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-gray-300 text-sm"
            onClick={async () => {
              setDateRange({ start: "", end: "" });
              setSource("");
              setSentimentFilter("");
              setCategoryFilter("");
              setPage(1);
              await fetchDashboard({ start: "", end: "" }, "");
            }}
          >
            Reset Filters
          </button>
        </div>
      </div>

      {/* Show alert for negative sentiment spike immediately after news box */}
      {(() => {
        if (!data.latestIndianNews || data.latestIndianNews.length < 5) return null;
        const sentiments = data.latestIndianNews.map((item: any) => (item.sentiment || '').toLowerCase().trim());
        const negativeCount = sentiments.filter((s: string) => s === 'negative').length;
        const negativeSpike = negativeCount > data.latestIndianNews.length * 0.5;
        if (negativeSpike) {
          return (
            <div className="bg-red-100 text-red-700 rounded-lg shadow p-4 mb-8 font-semibold">
              Alert: Negative sentiment spike detected in recent news!
            </div>
          );
        }
        return null;
      })()}
      {/* Dashboard Visualizations */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
        {/* Media Coverage Distribution Bar Chart */}
        <div className="bg-white rounded-lg shadow p-6 flex flex-col items-center">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2"><FaGlobe /> Media Coverage Distribution</h3>
          <div className="w-full h-64">
            {mediaCoverageValues.every(v => v === 0) ? (
              <div className="text-gray-500 text-center flex items-center justify-center h-full">No media coverage data available.</div>
            ) : (
              <Bar 
                data={{
                  labels: mediaCoverageLabels,
                  datasets: [
                    {
                      label: 'Number of Articles',
                      data: mediaCoverageValues,
                      backgroundColor: mediaCoverageColors,
                      borderColor: mediaCoverageColors.map(color => color),
                      borderWidth: 1,
                    },
                  ],
                }} 
                options={{
                  plugins: {
                    legend: { display: false },
                    tooltip: {
                      callbacks: {
                        label: function (context: any) {
                          const label = context.label || "";
                          const value = context.parsed.y;
                          if (label === 'Total News') {
                            return `${label}: ${value} articles (100%)`;
                          } else {
                            const count = label === 'BD Covered' ? mediaCoverageCounts.totalBD : 
                                         label === 'International Covered' ? mediaCoverageCounts.totalIntl : 
                                         mediaCoverageCounts.bothCovered;
                            return `${label}: ${count} articles (${value}%)`;
                          }
                        },
                      },
                    },
                    datalabels: {
                      display: true,
                      color: "#222",
                      font: { weight: "bold" as const },
                      anchor: "end" as const,
                      align: "top" as const,
                      formatter: (value: number, context: any) => {
                        const label = context.chart.data.labels[context.dataIndex];
                        if (label === 'Total News') {
                          return `${value}`;  // Show count for total news
                        } else {
                          return `${value}%`;  // Show percentage for coverage
                        }
                      },
                    },
                  },
                  maintainAspectRatio: false,
                  responsive: true,
                  scales: {
                    y: { 
                      display: false,
                      beginAtZero: true,
                      max: Math.max(100, mediaCoverageCounts.totalNews)  // Dynamic max to accommodate both count and percentage
                    },
                    x: {
                      ticks: {
                        maxRotation: 0,
                        minRotation: 0
                      }
                    }
                  },
                }} 
              />
            )}
          </div>
        </div>
        {/* Sentiment Pie Chart (replaces Bar chart) */}
        <div className="bg-white rounded-lg shadow p-6 flex flex-col items-center justify-center h-full">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2"><FaChartLine /> Sentiment (All)</h3>
          <div className="flex justify-center items-center w-full h-64">
            <Pie data={sentimentChartData} options={{ plugins: { legend: { position: 'bottom' } } }} />
          </div>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
        {/* FactCheck Pie Chart */}
        <div className="bg-white rounded-lg shadow p-6 flex flex-col items-center justify-center h-full">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2"><FaCheckCircle /> FactCheck Distribution</h3>
          <div className="flex justify-center items-center w-full h-64">
            <Pie data={factCheckPieData} options={{ plugins: { legend: { position: 'bottom' } } }} />
          </div>
        </div>
        {/* Category Bar Chart */}
        <div className="bg-white rounded-lg shadow p-6 flex flex-col items-center">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2"><FaRegNewspaper /> Category Distribution</h3>
          <div className="w-full h-64">
            <Bar data={categoryBarData} options={langBarOptions} />
          </div>
        </div>
      </div>
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        {getSentimentStats(globalFilteredNews).map((stat: any) => (
          <div key={stat.label} className={`flex flex-col items-center bg-white rounded-lg shadow p-4 ${stat.color}`}>
            <div className="text-2xl mb-2">{stat.icon}</div>
            <div className="text-lg font-bold">{stat.value}</div>
            <div className="text-sm">{stat.label}</div>
          </div>
        ))}
      </div>
      {/* Top Entities (NER) word cloud */}
      <div className="bg-white rounded-lg shadow p-6 mb-8 relative">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2"><FaCloud className="text-primary-500" /> Top Entities (NER)</h3>
        <div className="w-full h-[24rem]">
          {nerKeywords.length > 0 ? (
            <ReactWordcloud
              words={nerKeywords.map(([word, value]) => ({ text: String(word), value: Number(value) }))}
              options={{
                rotations: 2,
                rotationAngles: [0, 90],
                fontSizes: [18, 64],
                fontFamily: 'system-ui',
                padding: 4,
                colors: ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'],
                enableTooltip: true,
                deterministic: false,
                scale: 'sqrt',
                spiral: 'archimedean',
                transitionDuration: 1000
              }}
              callbacks={{
                onWordClick: (word) => {
                  setSelectedEntity(word.text);
                  setPage(1);
                },
                getWordTooltip: (word) => `${word.text}: ${word.value}`,
              }}
            />
          ) : (
            <div className="text-gray-400 text-center text-lg mt-24">No entities found for current filters.</div>
          )}
          {selectedEntity && (
            <div className="absolute left-6 bottom-6 bg-white bg-opacity-90 rounded px-3 py-2 flex items-center gap-2 shadow">
              <span className="text-sm text-blue-700 font-semibold">Filtering by entity: {selectedEntity}</span>
              <button className="ml-2 px-2 py-1 rounded bg-gray-200 hover:bg-gray-300 text-sm" onClick={() => setSelectedEntity("")}>Clear</button>
            </div>
          )}
        </div>
      </div>

      {/* Latest Indian News Monitoring */}
      <div className="card mb-8">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-4 gap-4">
          <h2 className="text-2xl font-bold">Latest Indian News</h2>
          <div className="flex gap-2 items-center flex-wrap">
            <label htmlFor="source" className="font-medium">Source:</label>
            <select
              id="source"
              className="border rounded px-2 py-1"
              value={source}
              onChange={async (e) => {
                setSource(e.target.value);
                setPage(1);
                await fetchDashboard(dateRange, e.target.value);
              }}
            >
              <option value="">All</option>
              {sources.map((src) => (
                <option key={src.domain} value={src.domain}>{src.name}</option>
              ))}
            </select>
            
            {/* Show All Toggle */}
            <div className="flex items-center gap-2 ml-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showAll}
                  onChange={(e) => {
                    setShowAll(e.target.checked);
                    if (e.target.checked) {
                      setPage(1); // Reset to page 1 when showing all
                    }
                  }}
                  className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="font-medium text-sm">Show All ({filteredNews.length})</span>
              </label>
            </div>
          </div>
        </div>
        
        {/* Performance Warning for Large Datasets */}
        {showAll && filteredNews.length > 100 && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-yellow-600 text-sm">
                  ⚠️ Showing {filteredNews.length} articles. Large datasets may affect performance.
                </span>
              </div>
              <button
                onClick={() => setShowAll(false)}
                className="text-yellow-700 hover:text-yellow-800 text-sm font-medium underline"
              >
                Switch to paginated view
              </button>
            </div>
          </div>
        )}
        
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b">
                {[
                  { label: "Date", key: "date" },
                  { label: "Headline", key: "headline" },
                  { label: "Source", key: "source" },
                  { label: "Category", key: "category" },
                  { label: "Sentiment", key: "sentiment" },
                  { label: "Fact Checked", key: "fact_check" },
                  { label: "Keywords", key: "keywords" },
                ].map((col) => (
                  <th
                    key={col.key}
                    className="text-left py-3 px-4 cursor-pointer select-none"
                    onClick={() => col.key !== "keywords" && col.key !== "headline" && handleSort(col.key)}
                  >
                    {col.label}
                    {sortBy === col.key && col.key !== "keywords" && col.key !== "headline" && (
                      <span className="ml-1">{sortDir === "asc" ? "▲" : "▼"}</span>
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {paginatedNews().length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-6 text-gray-500">
                    No news articles found for the selected range.
                  </td>
                </tr>
              ) : (
                paginatedNews().map((item: any) => {
                  const parsedSummary = (() => {
                    try {
                      return typeof item.summary === "string" ? JSON.parse(item.summary) : item.summary;
                    } catch (e) {
                      return {};
                    }
                  })();
                  const sentiment = String(parsedSummary?.sentiment || item.sentiment || "neutral");
                  const category = getCategory(item);
                  const summary = String(parsedSummary?.summary_text || parsedSummary?.summary || "No summary available.");
                  const factCheckStatus = getFactCheckStatus(item);

                  return (
                    <tr key={item.id} className="border-b hover:bg-gray-50">
                      <td className="py-3 px-4">{item.date ? format(new Date(item.date), "dd-MMM-yy") : "-"}</td>
                      <td className="py-3 px-4 max-w-xs truncate" title={item.headline}>
                        <a href={`/news/${item.id}`} className="text-primary-600 underline">
                          {item.headline.length > 60 ? item.headline.slice(0, 60) + "..." : item.headline}
                        </a>
                      </td>
                      <td className="py-3 px-4">{stripTLD(item.source_domain || item.source)}</td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-1 rounded text-xs font-semibold ${categoryColorMap[category] || categoryColorMap.Other}`}>{category}</span>
                      </td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-1 rounded text-xs font-semibold ${sentimentColorMap[sentiment]}`}>{sentiment}</span>
                      </td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-1 rounded text-xs font-semibold ${factCheckColorMap[factCheckStatus]}`}>{factCheckStatus}</span>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex flex-wrap gap-1">
                          {(() => {
                            const weightedKeywords = getTopWeightedKeywords(item);
                            return weightedKeywords.length > 0 ? (
                              weightedKeywords.map(({ word, count }, idx) => (
                                <span key={idx} className="inline-flex items-center gap-1 bg-blue-100 text-blue-700 rounded-full px-2 py-0.5 text-xs font-semibold">
                                  {word}
                                  <span className="bg-blue-200 text-blue-800 rounded-full px-1.5 py-0.5 text-xs font-bold min-w-[16px] text-center">
                                    {count}
                                  </span>
                                </span>
                              ))
                            ) : (
                              <span className="text-gray-400 text-xs italic">No keywords</span>
                            );
                          })()}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
        {/* Pagination Bar */}
        {globalFilteredNews && globalFilteredNews.length > 0 && (
          <div className="flex justify-between items-center mt-4">
            {showAll ? (
              <div className="text-gray-600 text-sm">
                Showing all {filteredNews.length} articles
              </div>
            ) : (
              <>
                <div className="text-gray-600 text-sm">
                  Showing {Math.min((page - 1) * PAGE_SIZE + 1, filteredNews.length)} to {Math.min(page * PAGE_SIZE, filteredNews.length)} of {filteredNews.length} articles
                </div>
                <div className="flex items-center">
                  <button
                    className="px-4 py-2 rounded-l bg-gray-200 text-gray-700 font-semibold hover:bg-gray-300 disabled:opacity-50"
                    onClick={() => setPage(page - 1)}
                    disabled={page === 1}
                  >
                    Previous
                  </button>
                  <span className="px-4 py-2 bg-white border-t border-b text-gray-700 font-medium">
                    Page {page} of {Math.ceil(filteredNews.length / PAGE_SIZE)}
                  </span>
                  <button
                    className="px-4 py-2 rounded-r bg-gray-200 text-gray-700 font-semibold hover:bg-gray-300 disabled:opacity-50"
                    onClick={() => setPage(page + 1)}
                    disabled={page >= Math.ceil(filteredNews.length / PAGE_SIZE)}
                  >
                    Next
                  </button>
                </div>
              </>
            )}
          </div>
        )}
      </div>
      {/* Timeline of Key Events */}
      {filteredNews && filteredNews.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2"><FaRegNewspaper /> Timeline of Key Events</h3>
          <div className="overflow-x-auto">
            <ul className="timeline timeline-vertical">
              {filteredNews.slice(0, 10).map((item: NewsItem) => (
                <li key={item.id} className="mb-4">
                  <span className="font-bold">{item.date ? format(new Date(item.date), "MMM d, yyyy") : "-"}</span>:
                  <a href={item.url || `/news/${item.id}`} className="text-primary-600 underline ml-2" target="_blank" rel="noopener noreferrer">
                    {item.headline.length > 80 ? item.headline.slice(0, 80) + "..." : item.headline}
                  </a>
                  <div className="flex gap-2 mt-1">
                    <span className={`px-2 py-0.5 rounded text-xs ${categoryColorMap[getCategory(item)]}`}>{getCategory(item)}</span>
                    <span className={`px-2 py-0.5 rounded text-xs ${sentimentColorMap[getSentiment(item)]}`}>{getSentiment(item)}</span>
                    <span className={`px-2 py-0.5 rounded text-xs ${factCheckColorMap[getFactCheckStatus(item)]}`}>{getFactCheckStatus(item)}</span>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
      {/* Fact Check Summary */}
      {globalFilteredNews && globalFilteredNews.length > 0 && (
        <div className="bg-white rounded-lg shadow p-0 mb-8">
          <div className="flex items-center justify-between px-6 py-4 border-b">
            <h3 className="text-lg font-semibold flex items-center gap-2"><FaCheckCircle className="text-primary-600 text-xl" /> Fact Check Summary</h3>
            <button onClick={() => setShowFactCheck(v => !v)} className="ml-2 px-5 py-1.5 rounded bg-primary-600 text-white font-semibold shadow hover:bg-primary-700 transition text-base">
              {showFactCheck ? "Hide" : "Show"}
            </button>
          </div>
          {showFactCheck && (
            <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h4 className="font-medium mb-2">Verification Status</h4>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(globalFilteredNews.reduce((acc: Record<string, number>, item: NewsItem) => {
                    const status = getFactCheckStatus(item);
                    acc[status] = (acc[status] || 0) + 1;
                    return acc;
                  }, {})).map(([status, count]) => (
                    <div key={status} className="flex items-center gap-2">
                      <span className={`px-2 py-1 rounded text-xs font-semibold ${factCheckColorMap[status]}`}>{status}</span>
                      <span className="text-sm text-gray-600">({count})</span>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <h4 className="font-medium mb-2">Top Sources</h4>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(globalFilteredNews.reduce((acc: Record<string, number>, item: NewsItem) => {
                    const source = item.source_domain || item.source;
                    acc[source] = (acc[source] || 0) + 1;
                    return acc;
                  }, {})).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([source, count]) => (
                    <div key={source} className="flex items-center gap-2">
                      <span className="text-sm font-medium">{source}</span>
                      <span className="text-sm text-gray-600">({count})</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
      {/* Media Coverage Analysis */}
      {data.latestIndianNews && data.latestIndianNews.length > 0 && (
        <div className="bg-white rounded-lg shadow p-0 mb-8">
          <div className="flex items-center justify-between px-6 py-4 border-b">
            <h3 className="text-lg font-semibold flex items-center gap-2"><FaGlobe className="text-primary-600 text-xl" /> Media Coverage Analysis</h3>
            <button onClick={() => setShowMediaCoverage(v => !v)} className="ml-2 px-5 py-1.5 rounded bg-primary-600 text-white font-semibold shadow hover:bg-primary-700 transition text-base">
              {showMediaCoverage ? "Hide" : "Show"}
            </button>
          </div>
          {showMediaCoverage && (
            <div className="p-6">
              {/* Media Coverage Summary Statistics */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6 p-4 bg-gray-50 rounded-lg">
                <div className="text-center">
                  <div className="text-2xl font-bold text-gray-600">{mediaCoverageCounts.totalNews}</div>
                  <div className="text-lg font-semibold text-gray-600">100%</div>
                  <div className="text-sm text-gray-600">Total News</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">{mediaCoverageCounts.totalBD}</div>
                  <div className="text-lg font-semibold text-blue-600">{mediaCoverageCounts.bdPercentage}%</div>
                  <div className="text-sm text-gray-600">BD Covered</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-orange-600">{mediaCoverageCounts.totalIntl}</div>
                  <div className="text-lg font-semibold text-orange-600">{mediaCoverageCounts.intlPercentage}%</div>
                  <div className="text-sm text-gray-600">International Covered</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">{mediaCoverageCounts.bothCovered}</div>
                  <div className="text-lg font-semibold text-green-600">{mediaCoverageCounts.bothPercentage}%</div>
                  <div className="text-sm text-gray-600">Both Covered</div>
                </div>
              </div>
              
              {/* Detailed Coverage Examples */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h4 className="font-medium mb-2">Bangladeshi Media Coverage</h4>
                  <div className="space-y-2">
                    {(() => {
                      const bangladeshiItems = data.latestIndianNews.filter((item: NewsItem) => {
                        const matches = item.bangladeshi_matches || [];
                        return Array.isArray(matches) && matches.length > 0;
                      }).slice(0, 3);
                      
                      return bangladeshiItems.length > 0 ? (
                        bangladeshiItems.map((item: NewsItem, index: number) => {
                          const matches = item.bangladeshi_matches || [];
                          return (
                            <div key={index} className="text-sm text-gray-700">
                              <div className="font-medium">{item.headline}</div>
                              <div className="text-gray-600">BD Matches: {matches.length}</div>
                            </div>
                          );
                        })
                      ) : (
                        <div className="text-gray-400 text-sm italic">No data available</div>
                      );
                    })()}
                  </div>
                </div>
                <div>
                  <h4 className="font-medium mb-2">International Media Coverage</h4>
                  <div className="space-y-2">
                    {(() => {
                      const internationalItems = data.latestIndianNews.filter((item: NewsItem) => {
                        const matches = item.international_matches || [];
                        return Array.isArray(matches) && matches.length > 0;
                      }).slice(0, 3);
                      
                      return internationalItems.length > 0 ? (
                        internationalItems.map((item: NewsItem, index: number) => {
                          const matches = item.international_matches || [];
                          return (
                            <div key={index} className="text-sm text-gray-700">
                              <div className="font-medium">{item.headline}</div>
                              <div className="text-gray-600">Intl Matches: {matches.length}</div>
                            </div>
                          );
                        })
                      ) : (
                        <div className="text-gray-400 text-sm italic">No data available</div>
                      );
                    })()}
                  </div>
                </div>
                <div>
                  <h4 className="font-medium mb-2">International Sources Coverage</h4>
                  <div className="space-y-2">
                    {(() => {
                      const intlItems = data.latestIndianNews.filter((item: NewsItem) => {
                        const intlMatches = item.international_matches || [];
                        return intlMatches.length > 0;
                      }).slice(0, 3);
                      
                      return intlItems.length > 0 ? (
                        intlItems.map((item: NewsItem, index: number) => {
                          const intlMatches = item.international_matches || [];
                                                      return (
                              <div key={index} className="text-sm text-gray-700">
                                <div className="font-medium">{item.headline}</div>
                                <div className="text-gray-600">International Sources: {intlMatches.length}</div>
                              </div>
                            );
                        })
                      ) : (
                        <div className="text-gray-400 text-sm italic">No data available</div>
                      );
                    })()}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
      {/* --- New: Media Coverage Comparison Over Time --- */}
      {data.latestIndianNews && data.latestIndianNews.some((item: any) => item.source_type) && (
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2"><FaChartLine /> Media Coverage Comparison Over Time</h3>
          <div className="w-full h-64">
            <Line data={{
              labels: Array.from(new Set(data.latestIndianNews.map((item: any) => item.date ? format(new Date(item.date), "MMM d") : "-"))),
              datasets: [
                ...['Indian', 'Bangladeshi', 'International'].map((type) => ({
                  label: type,
                  data: Array.from(new Set(data.latestIndianNews.map((item: any) => item.date ? format(new Date(item.date), "MMM d") : "-"))).map(dateLabel =>
                    data.latestIndianNews.filter((item: any) => (item.date ? format(new Date(item.date), "MMM d") : "-") === dateLabel && item.source_type === type).length
                  ),
                  borderColor: type === 'Indian' ? '#0ea5e9' : type === 'Bangladeshi' ? '#22c55e' : '#f59e42',
                  backgroundColor: type === 'Indian' ? 'rgba(14,165,233,0.1)' : type === 'Bangladeshi' ? 'rgba(34,197,94,0.1)' : 'rgba(245,158,66,0.1)',
                  fill: false,
                  tension: 0.4,
                }))
              ],
            }} options={{
              responsive: true,
              plugins: { legend: { position: 'bottom' } },
            }} />
          </div>
        </div>
      )}
      {/* --- New: Geographical Heatmap (Placeholder) --- */}
      {data.latestIndianNews && data.latestIndianNews.some((item: any) => item.location) && (
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2"><FaGlobe /> Geographical Heatmap</h3>
          <div className="text-gray-500">[Heatmap visualization would go here if location data is available]</div>
        </div>
      )}
      {/* --- New: Source Credibility/Trust Score --- */}
      {data.latestIndianNews && data.latestIndianNews.some((item: any) => item.credibility_score) && (
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2"><FaCheckCircle /> Source Credibility Scores</h3>
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b">
                <th className="text-left py-2 px-4">Source</th>
                <th className="text-left py-2 px-4">Credibility Score</th>
              </tr>
            </thead>
            <tbody>
              {Array.from(new Set(data.latestIndianNews.map((item: any) => item.source))).map((source: any) => {
                const score = data.latestIndianNews.find((item: any) => item.source === source)?.credibility_score;
                return (
                  <tr key={source} className="border-b">
                    <td className="py-2 px-4">{source}</td>
                    <td className="py-2 px-4">
                      {score === 0 ? "Not Available" : (typeof score === "number" ? score.toFixed(3) : "-")}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      {/* --- New: Article Similarity/Clustering (Placeholder) --- */}
      {data.latestIndianNews && data.latestIndianNews.some((item: any) => item.cluster_id) && (
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2"><FaRegNewspaper /> Article Clusters</h3>
          <div className="text-gray-500">[Cluster visualization would go here if cluster_id/topic data is available]</div>
        </div>
      )}
      {/* --- New: Media Bias Analysis (Placeholder) --- */}
      {data.latestIndianNews && data.latestIndianNews.some((item: any) => item.topic) && (
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2"><FaExclamationCircle /> Media Bias Analysis</h3>
          <div className="text-gray-500">[Media bias comparison would go here if topic/source/sentiment data is available]</div>
        </div>
      )}
      {/* --- Implications & Analysis --- */}
      {Array.isArray(data.implications) && (
        <div className="bg-white rounded-lg shadow p-0 mb-8">
          <div className="flex items-center justify-between px-6 py-4 border-b">
            <h3 className="text-lg font-semibold flex items-center gap-2">Implications & Analysis</h3>
            <button onClick={() => setShowImplications(v => !v)} className="ml-2 px-5 py-1.5 rounded bg-primary-600 text-white font-semibold shadow hover:bg-primary-700 transition text-base">
              {showImplications ? "Hide" : "Show"}
            </button>
          </div>
          {showImplications && (
            <div className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {['Political Stability', 'Economic Impact', 'Social Cohesion'].map(type => {
                  const imp = data.implications.find((i: any) => i.type === type);
                  const impact = imp ? imp.impact : null;
                  return (
                    <div key={type} className="p-4 rounded border border-gray-200 bg-gray-50">
                      <div className="font-bold mb-2">{type}</div>
                      {impact ? (
                        <div className="text-gray-700 text-sm">{impact}</div>
                      ) : (
                        <div className="text-gray-400 text-sm italic">No data available</div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
      {/* --- Prediction (Outlook) --- */}
      {Array.isArray(data.predictions) && (
        <div className="bg-white rounded-lg shadow p-0 mb-8">
          <div className="flex items-center justify-between px-6 py-4 border-b">
            <h3 className="text-lg font-semibold flex items-center gap-2">Prediction (Outlook)</h3>
            <button onClick={() => setShowPredictions(v => !v)} className="ml-2 px-5 py-1.5 rounded bg-primary-600 text-white font-semibold shadow hover:bg-primary-700 transition text-base">
              {showPredictions ? "Hide" : "Show"}
            </button>
          </div>
          {showPredictions && (
            <div className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {['Political Landscape', 'Economic Implications'].map(type => {
                  const pred = data.predictions.find((p: any) => p.category === type);
                  const hasData = pred && (pred.likelihood || pred.timeFrame || pred.details);
                  return (
                    <div key={type} className={`p-4 rounded border ${hasData ? 'border-yellow-200 bg-yellow-50' : 'border-gray-200 bg-gray-50'}`}> 
                      <div className="font-bold mb-2">{type}</div>
                      {hasData ? (
                        <>
                          {pred.likelihood && <div>Likelihood: <span className="font-semibold">{pred.likelihood}%</span></div>}
                          {pred.timeFrame && <div>Time Frame: {pred.timeFrame}</div>}
                          {pred.details && <div className="mt-2 text-gray-700 text-sm">{pred.details}</div>}
                        </>
                      ) : (
                        <div className="text-gray-400 text-sm italic">No data available</div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
      {/* --- Fact-Checking: Cross-Media Comparison --- */}
      {data.factChecking && (
        <div className="bg-white rounded-lg shadow p-0 mb-8">
          <div className="flex items-center justify-between px-6 py-4 border-b">
            <h3 className="text-lg font-semibold flex items-center gap-2">Fact-Checking: Cross-Media Comparison</h3>
            <button onClick={() => setShowFactChecking(v => !v)} className="ml-2 px-5 py-1.5 rounded bg-primary-600 text-white font-semibold shadow hover:bg-primary-700 transition text-base">
              {showFactChecking ? "Hide" : "Show"}
            </button>
          </div>
          {showFactChecking && (
            <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <div className="font-medium mb-2">Bangladeshi Agreement</div>
                <div className="text-lg text-blue-700 font-bold">{data.factChecking.bangladeshiAgreement ?? 'No data available'}</div>
              </div>
              <div>
                <div className="font-medium mb-2">International Agreement</div>
                <div className="text-lg text-green-700 font-bold">{data.factChecking.internationalAgreement ?? 'No data available'}</div>
              </div>
            </div>
          )}
        </div>
      )}
      {/* --- Key Sources Used --- */}
      {Array.isArray(data.keySources) && (
        <div className="bg-white rounded-lg shadow p-0 mb-8">
          <div className="flex items-center justify-between px-6 py-4 border-b">
            <h3 className="text-lg font-semibold flex items-center gap-2">Key Sources Used</h3>
            <button onClick={() => setShowKeySources(v => !v)} className="ml-2 px-5 py-1.5 rounded bg-primary-600 text-white font-semibold shadow hover:bg-primary-700 transition text-base">
              {showKeySources ? "Hide" : "Show"}
            </button>
          </div>
          {showKeySources && (
            <div className="p-6">
              <div className="flex flex-wrap gap-2">
                {data.keySources.map((src: string) => (
                  <span
                    key={src}
                    className="inline-block bg-blue-100 text-blue-700 rounded px-3 py-1 text-sm font-semibold"
                  >
                    {src}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
      {/* --- New: User-Driven Custom Reports --- */}
      <div className="bg-white rounded-lg shadow p-0 mb-8">
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h3 className="text-lg font-semibold flex items-center gap-2"><FaRegNewspaper className="text-primary-600 text-xl" /> Export Custom Report</h3>
          <button onClick={() => setShowCustomReport(v => !v)} className="ml-2 px-5 py-1.5 rounded bg-primary-600 text-white font-semibold shadow hover:bg-primary-700 transition text-base">
            {showCustomReport ? "Hide" : "Show"}
          </button>
        </div>
        {showCustomReport && (
          <div className="p-6">
            <button className="btn-primary" onClick={() => {
              const csv = [
                ['Date', 'Headline', 'Source', 'Category', 'Sentiment', 'Fact Checked', 'URL'],
                ...data.latestIndianNews.map((item: any) => [item.date, item.headline, item.source, item.category, item.sentiment, item.fact_check, item.url || ''])
              ].map((row: any[]) => row.map((field: any) => `"${String(field).replace(/"/g, '""')}"`).join(',')).join('\n');
              const blob = new Blob([csv], { type: 'text/csv' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = 'custom_report.csv';
              a.click();
              URL.revokeObjectURL(url);
            }}>
              Export as CSV
            </button>
          </div>
        )}
      </div>
    </div>
  );
}