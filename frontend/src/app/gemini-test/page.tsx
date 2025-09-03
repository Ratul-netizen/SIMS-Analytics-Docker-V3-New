"use client"

import { useState } from "react";
import axios from "axios";
import { FaRobot, FaSpinner, FaCheckCircle, FaExclamationTriangle } from "react-icons/fa";

// Utility to get backend base URL
const getApiBase = () => {
  if (typeof window !== 'undefined') {
    const { protocol, hostname, port } = window.location;
    
    // If running on localhost, use port 5000 for backend
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return `${protocol}//${hostname}:5000`;
    }
    
    // For VM deployment, use the same hostname but port 5000
    return `${protocol}//${hostname}:5000`;
  }
  return '';
};

interface GeminiAnalysis {
  sentiment: string;
  category: string;
  summary: string;
  entities: string[];
  fact_check: {
    status: string;
    sources: any[];
    web_search_results: any[];
  };
  geopolitical_implications: string;
  media_bias_assessment: string;
  gemini_raw_response: string;
}

interface AnalysisResponse {
  success: boolean;
  analysis: GeminiAnalysis;
  title: string;
  text_length: number;
  ai_provider: string;
  error?: string;
}

const sentimentColorMap: Record<string, string> = {
  positive: "bg-green-100 text-green-700 border-green-300",
  negative: "bg-red-100 text-red-700 border-red-300",
  neutral: "bg-blue-100 text-blue-700 border-blue-300",
  cautious: "bg-yellow-100 text-yellow-700 border-yellow-300",
};

const categoryColorMap: Record<string, string> = {
  politics: "bg-blue-100 text-blue-700 border-blue-300",
  sports: "bg-orange-100 text-orange-700 border-orange-300",
  technology: "bg-pink-100 text-pink-700 border-pink-300",
  crime: "bg-red-100 text-red-700 border-red-300",
  health: "bg-green-100 text-green-700 border-green-300",
  education: "bg-purple-100 text-purple-700 border-purple-300",
  business: "bg-yellow-100 text-yellow-700 border-yellow-300",
  entertainment: "bg-indigo-100 text-indigo-700 border-indigo-300",
  environment: "bg-emerald-100 text-emerald-700 border-emerald-300",
  others: "bg-gray-100 text-gray-700 border-gray-300",
};

const factCheckColorMap: Record<string, string> = {
  verified: "bg-green-100 text-green-700 border-green-300",
  unverified: "bg-gray-100 text-gray-700 border-gray-300",
};

export default function GeminiTestPage() {
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = async () => {
    if (!text.trim()) {
      setError("Please enter some text to analyze");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await axios.post(`${getApiBase()}/api/gemini-analyze`, {
        title: title || "Test Article",
        text: text.trim()
      });

      setResult(response.data as AnalysisResponse);
          } catch (err: any) {
        console.error('Gemini API Error:', err);
        if (err.response?.status === 503) {
          setError("Gemini 2.5 Flash is not available. Please check the backend configuration and GEMINI_API_KEY.");
        } else if (err.response?.data?.error) {
          setError(err.response.data.error);
        } else {
          setError(`Analysis failed: ${err.message || 'Unknown error'}`);
        }
    } finally {
      setLoading(false);
    }
  };

  const sampleText = `Bangladesh and India have signed a new trade agreement aimed at boosting bilateral economic cooperation. The agreement, signed in Dhaka, is expected to increase trade volume by 30% over the next three years. Prime Minister Sheikh Hasina and Indian External Affairs Minister S. Jaishankar were present at the signing ceremony. The deal covers sectors including textiles, pharmaceuticals, and agricultural products. Both countries expressed optimism about strengthening their economic ties and regional stability.`;

  const loadSample = () => {
    setTitle("Bangladesh-India Trade Agreement Signed");
    setText(sampleText);
    setError(null);
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      {/* Header */}
      <div className="bg-white rounded-lg shadow p-6 mb-8">
        <h1 className="text-3xl font-bold flex items-center gap-3 mb-4">
          <FaRobot className="text-blue-600" />
          Manual Fact Analysis Test
        </h1>
        <p className="text-gray-600">
          Test the Google Gemini 2.5 Flash integration for SIMS Analytics. This system uses only Gemini AI 
          (no fallback models) to analyze sentiment, category, entities, fact-checking, and geopolitical implications.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Input Section */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Input Article</h2>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Article Title (Optional)
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Enter article title..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Article Text *
              </label>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Enter or paste the news article text here..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 h-64 resize-none"
              />
              <div className="text-sm text-gray-500 mt-1">
                Character count: {text.length}
              </div>
            </div>
            
            <div className="flex flex-wrap gap-3">
              <button
                onClick={handleAnalyze}
                disabled={loading || !text.trim()}
                className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {loading ? (
                  <>
                    <FaSpinner className="animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <FaRobot />
                    Analyze with Gemini 2.5 Flash
                  </>
                )}
              </button>
              
              <button
                onClick={loadSample}
                className="bg-gray-600 text-white px-6 py-2 rounded-md hover:bg-gray-700"
              >
                Load Sample Text
              </button>
              
              <button
                onClick={() => {
                  setTitle("");
                  setText("");
                  setResult(null);
                  setError(null);
                }}
                className="bg-red-600 text-white px-6 py-2 rounded-md hover:bg-red-700"
              >
                Clear All
              </button>
            </div>
          </div>
        </div>

        {/* Results Section */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Analysis Results</h2>
          
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
              <div className="flex items-center gap-2 text-red-700">
                <FaExclamationTriangle />
                <span className="font-medium">Error</span>
              </div>
              <p className="text-red-600 mt-2">{error}</p>
            </div>
          )}
          
          {loading && (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <FaSpinner className="animate-spin text-4xl text-blue-500 mx-auto mb-4" />
                <p className="text-gray-600">Analyzing with Gemini 2.5 Flash...</p>
                <p className="text-sm text-gray-500 mt-2">
                  This may take a few moments as we search the web for supporting information.
                </p>
              </div>
            </div>
          )}
          
          {result && result.success && (
            <div className="space-y-6">
              {/* Analysis Overview */}
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <div className="flex items-center gap-2 text-green-700 mb-2">
                  <FaCheckCircle />
                  <span className="font-medium">Analysis Complete</span>
                </div>
                <div className="text-sm text-green-600">
                  <p>Provider: {result.ai_provider}</p>
                  <p>Text analyzed: {result.text_length} characters</p>
                </div>
              </div>
              
              {/* Core Analysis */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <h3 className="font-medium text-gray-700 mb-2">Sentiment</h3>
                  <span className={`px-3 py-1 rounded-full text-sm font-medium border ${sentimentColorMap[result.analysis.sentiment] || sentimentColorMap.neutral}`}>
                    {result.analysis.sentiment}
                  </span>
                </div>
                
                <div>
                  <h3 className="font-medium text-gray-700 mb-2">Category</h3>
                  <span className={`px-3 py-1 rounded-full text-sm font-medium border ${categoryColorMap[result.analysis.category] || categoryColorMap.others}`}>
                    {result.analysis.category}
                  </span>
                </div>
                
                <div className="sm:col-span-2">
                  <h3 className="font-medium text-gray-700 mb-2">Fact Check Status</h3>
                  <span className={`px-3 py-1 rounded-full text-sm font-medium border ${factCheckColorMap[result.analysis.fact_check.status] || factCheckColorMap.unverified}`}>
                    {result.analysis.fact_check.status.replace('_', ' ')}
                  </span>
                </div>
              </div>
              
              {/* Fact Check Sources */}
              {result.analysis.fact_check.sources && result.analysis.fact_check.sources.length > 0 && (
                <div>
                  <h3 className="font-medium text-gray-700 mb-3">Fact Check Sources ({result.analysis.fact_check.sources.length})</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {result.analysis.fact_check.sources.map((source: any, index: number) => (
                      <div
                        key={index}
                        className="bg-blue-50 border border-blue-200 rounded-lg p-4 hover:bg-blue-100 transition"
                      >
                                                 <div className="flex items-start justify-between mb-2">
                           <div className="font-medium text-blue-800 text-sm">
                             {source.source_name || 'Unknown Source'}
                           </div>
                           <div className="flex flex-col items-end gap-1">
                             <span className={`px-2 py-1 rounded text-xs font-medium ${
                               source.source_country?.toLowerCase().includes('bd') || source.source_country?.toLowerCase().includes('bangladesh')
                                 ? 'bg-green-100 text-green-700'
                                 : 'bg-orange-100 text-orange-700'
                             }`}>
                               {source.source_country || 'Unknown'}
                             </span>
                             {source.verification_status && (
                               <span className={`px-2 py-1 rounded text-xs font-medium ${
                                 source.verification_status === 'gemini-verified' 
                                   ? 'bg-emerald-100 text-emerald-700'
                                   : source.verification_status === 'backend-verified'
                                   ? 'bg-blue-100 text-blue-700'
                                   : 'bg-gray-100 text-gray-700'
                               }`}>
                                 {source.verification_status === 'gemini-verified' && '🟢 Gemini ✓'}
                                 {source.verification_status === 'backend-verified' && '🔵 System ✓'}
                                 {source.verification_status === 'unverified' && '⚪ Unverified'}
                               </span>
                             )}
                           </div>
                         </div>
                        {source.source_url && (
                          <a 
                            href={source.source_url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:text-blue-800 underline text-sm break-all"
                          >
                            🔗 {new URL(source.source_url).hostname}
                          </a>
                        )}
                        {!source.source_url && (
                          <div className="text-gray-400 text-sm italic">No URL available</div>
                        )}
                      </div>
                    ))}
                  </div>
                                     <div className="mt-3 text-sm text-gray-600">
                     <p>💡 <strong>Sources Legend:</strong></p>
                     <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-2">
                       <div>
                         <p><strong>Source Origin:</strong></p>
                         <p>🟢 <span className="bg-green-100 text-green-700 px-2 py-0.5 rounded text-xs">BD/Bangladesh</span> - Local Bangladeshi sources</p>
                         <p>🟠 <span className="bg-orange-100 text-orange-700 px-2 py-0.5 rounded text-xs">International</span> - Global/Regional sources</p>
                       </div>
                       <div>
                         <p><strong>Verification Status:</strong></p>
                         <p>🟢 <span className="bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded text-xs">Gemini ✓</span> - AI verified the URL works</p>
                         <p>🔵 <span className="bg-blue-100 text-blue-700 px-2 py-0.5 rounded text-xs">System ✓</span> - Backend validated the URL</p>
                         <p>⚪ <span className="bg-gray-100 text-gray-700 px-2 py-0.5 rounded text-xs">Unverified</span> - URL not validated</p>
                       </div>
                     </div>
                   </div>
                </div>
              )}
              
              {/* No Sources Found */}
              {(!result.analysis.fact_check.sources || result.analysis.fact_check.sources.length === 0) && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                  <div className="text-yellow-800 font-medium mb-1">⚠️ No Fact-Check Sources Found</div>
                  <p className="text-yellow-700 text-sm">
                    Gemini could not find reliable sources to verify this story. This could mean:
                  </p>
                  <ul className="text-yellow-700 text-sm mt-2 ml-4 list-disc">
                    <li>The story is very recent and hasn't been covered widely yet</li>
                    <li>The story may be from limited or unreliable sources</li>
                    <li>Web search didn't return relevant verification sources</li>
                  </ul>
                </div>
              )}
              
              {/* Summary */}
              {result.analysis.summary && (
                <div>
                  <h3 className="font-medium text-gray-700 mb-2">Summary</h3>
                  <p className="text-gray-600 bg-gray-50 p-3 rounded-md">
                    {result.analysis.summary}
                  </p>
                </div>
              )}
              
              {/* Entities */}
              {result.analysis.entities && result.analysis.entities.length > 0 && (
                <div>
                  <h3 className="font-medium text-gray-700 mb-2">Key Entities</h3>
                  <div className="flex flex-wrap gap-2">
                    {result.analysis.entities.map((entity, index) => (
                      <span
                        key={index}
                        className="bg-blue-100 text-blue-700 px-2 py-1 rounded text-sm"
                      >
                        {entity}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Geopolitical Implications */}
              {result.analysis.geopolitical_implications && (
                <div>
                  <h3 className="font-medium text-gray-700 mb-2">Geopolitical Implications</h3>
                  <p className="text-gray-600 bg-blue-50 p-3 rounded-md">
                    {result.analysis.geopolitical_implications}
                  </p>
                </div>
              )}
              
              {/* Media Bias Assessment */}
              {result.analysis.media_bias_assessment && (
                <div>
                  <h3 className="font-medium text-gray-700 mb-2">Media Bias Assessment</h3>
                  <p className="text-gray-600 bg-yellow-50 p-3 rounded-md">
                    {result.analysis.media_bias_assessment}
                  </p>
                </div>
              )}
              
              {/* Raw Response Preview */}
              {result.analysis.gemini_raw_response && (
                <div>
                  <h3 className="font-medium text-gray-700 mb-2">Raw Response (Preview)</h3>
                  <pre className="text-xs text-gray-600 bg-gray-50 p-3 rounded-md overflow-auto max-h-32">
                    {result.analysis.gemini_raw_response}
                  </pre>
                </div>
              )}
            </div>
          )}
          
          {!loading && !result && !error && (
            <div className="text-center py-12 text-gray-500">
              <FaRobot className="text-4xl mx-auto mb-4 opacity-50" />
              <p>Enter some text and click "Analyze" to see Gemini 2.5 Flash results.</p>
            </div>
          )}
        </div>
      </div>
      
      {/* Navigation */}
      <div className="mt-8 text-center">
        <a
          href="/"
          className="inline-flex items-center gap-2 bg-gray-600 text-white px-6 py-2 rounded-md hover:bg-gray-700 transition-colors"
        >
          ← Back to Dashboard
        </a>
      </div>
    </div>
  );
} 