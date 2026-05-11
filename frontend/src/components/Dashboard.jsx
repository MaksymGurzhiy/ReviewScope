import { useState } from 'react'
import { Play, FileText, TrendingUp, MessageSquare, Star } from 'lucide-react'
import axios from 'axios'
import SentimentChart from './SentimentChart'
import TopicsDisplay from './TopicsDisplay'
import KeywordsCloud from './KeywordsCloud'
import InsightsPanel from './InsightsPanel'

const API_URL = 'http://localhost:8000'

function Dashboard({
  fileData,
  analysisResults,
  onStartAnalysis,
  onAnalysisComplete,
}) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const startAnalysis = async () => {
    setLoading(true)
    setError(null)
    onStartAnalysis()
    try {
      const response = await axios.post(
        `${API_URL}/api/analyze/${fileData.file_id}`,
        { analyze_sentiment: true, analyze_topics: true, extract_keywords: true }
      )
      if (response.data.success) {
        onAnalysisComplete(response.data.results)
      } else {
        setError(response.data.message || 'Analysis failed')
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Analysis failed. Check backend logs.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* File info bar */}
      <div className="card p-5">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-11 h-11 rounded-xl bg-blue-50 dark:bg-blue-950 flex items-center justify-center flex-shrink-0">
              <FileText className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-900 dark:text-white">
                {fileData.file_id}
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {fileData.statistics.total_reviews} reviews loaded
              </p>
            </div>
          </div>

          {!analysisResults && !loading && (
            <button onClick={startAnalysis} className="btn-primary">
              <Play className="w-4 h-4" />
              Start Analysis
            </button>
          )}
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-3 gap-3 mt-5">
          <StatCard label="Total Reviews" value={fileData.statistics.total_reviews} icon={<MessageSquare className="w-4 h-4" />} />
          <StatCard label="With Ratings" value={fileData.statistics.reviews_with_rating} icon={<TrendingUp className="w-4 h-4" />} />
          <StatCard label="Avg Rating" value={fileData.statistics.avg_rating?.toFixed(2) || 'N/A'} icon={<Star className="w-4 h-4" />} />
        </div>
      </div>

      {/* Loading skeleton */}
      {loading && <AnalysisSkeleton />}

      {/* Error */}
      {error && (
        <div className="card p-5 border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20">
          <p className="font-semibold text-red-800 dark:text-red-300 mb-1">Analysis Error</p>
          <p className="text-red-600 dark:text-red-400 text-sm">{error}</p>
        </div>
      )}

      {/* Results */}
      {analysisResults && !loading && (
        <div className="space-y-6">
          <InsightsPanel
            insights={analysisResults.insights}
            recommendations={analysisResults.recommendations}
          />

          {analysisResults.sentiment && (
            <SentimentChart sentiment={analysisResults.sentiment} />
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {analysisResults.topics && (
              <TopicsDisplay topics={analysisResults.topics} />
            )}
            {analysisResults.keywords && (
              <KeywordsCloud keywords={analysisResults.keywords} />
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function StatCard({ label, value, icon }) {
  return (
    <div className="rounded-xl bg-gray-50 dark:bg-gray-800 p-3.5">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">{label}</span>
        <span className="text-gray-400 dark:text-gray-500">{icon}</span>
      </div>
      <p className="text-xl font-bold text-gray-900 dark:text-white">{value}</p>
    </div>
  )
}

function AnalysisSkeleton() {
  return (
    <div className="space-y-6">
      <div className="card p-6 text-center">
        <div className="flex flex-col items-center gap-4 py-6">
          <div className="w-12 h-12 rounded-full border-[3px] border-gray-200 dark:border-gray-700 border-t-blue-600 animate-spin" />
          <div>
            <p className="text-base font-semibold text-gray-900 dark:text-white mb-1">
              Analyzing reviews...
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Running BERT sentiment, BERTopic modeling, and KeyBERT extraction
            </p>
          </div>
        </div>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card p-6"><div className="skeleton h-5 w-40 mb-4" /><div className="skeleton h-48 w-full" /></div>
        <div className="card p-6"><div className="skeleton h-5 w-40 mb-4" /><div className="skeleton h-48 w-full" /></div>
      </div>
    </div>
  )
}

export default Dashboard
