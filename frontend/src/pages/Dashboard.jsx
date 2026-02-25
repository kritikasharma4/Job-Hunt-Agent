import { useState, useEffect } from 'react'
import { matchesApi } from '../api/client'
import StatsCard from '../components/StatsCard'
import StatusBadge from '../components/StatusBadge'
import { Link } from 'react-router-dom'

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    matchesApi.stats()
      .then((res) => setStats(res.data))
      .catch((err) => {
        if (err.response?.status === 400) {
          setStats(null)
        } else {
          setError('Failed to load dashboard')
        }
      })
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return <div className="text-gray-500">Loading dashboard...</div>
  }

  if (error) {
    return <div className="text-red-500">{error}</div>
  }

  if (!stats || (stats.total_searches === 0 && stats.total_applications === 0)) {
    return (
      <div className="text-center py-20">
        <h2 className="text-2xl font-bold text-gray-800 mb-4">Welcome to Job Hunt Agent</h2>
        <p className="text-gray-500 mb-8">Get started by setting up your profile and searching for jobs.</p>
        <div className="flex gap-4 justify-center">
          <Link
            to="/profile"
            className="bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors"
          >
            Set Up Profile
          </Link>
          <Link
            to="/search"
            className="bg-white text-blue-600 border border-blue-600 px-6 py-3 rounded-lg font-medium hover:bg-blue-50 transition-colors"
          >
            Search Jobs
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Dashboard</h2>

      {/* Stats cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatsCard label="Searches" value={stats.total_searches} color="blue" />
        <StatsCard label="Jobs Found" value={stats.total_jobs_found} color="purple" />
        <StatsCard label="Matches" value={stats.total_matches} color="green" />
        <StatsCard label="Applications" value={stats.total_applications} color="orange" />
      </div>

      {/* Average score */}
      {stats.avg_match_score > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8">
          <h3 className="text-lg font-semibold text-gray-800 mb-2">Average Match Score</h3>
          <div className="flex items-center gap-4">
            <div className="flex-1 bg-gray-200 rounded-full h-4">
              <div
                className="bg-blue-600 h-4 rounded-full"
                style={{ width: `${(stats.avg_match_score * 100).toFixed(0)}%` }}
              />
            </div>
            <span className="text-xl font-bold text-blue-600">
              {(stats.avg_match_score * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      )}

      {/* Applications by status */}
      {Object.keys(stats.applications_by_status).length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Applications by Status</h3>
          <div className="flex flex-wrap gap-4">
            {Object.entries(stats.applications_by_status).map(([status, count]) => (
              <div key={status} className="flex items-center gap-2">
                <StatusBadge status={status} />
                <span className="text-lg font-bold text-gray-700">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent matches */}
      {stats.recent_matches?.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-gray-800">Recent Matches</h3>
            <Link to="/search" className="text-sm text-blue-600 hover:underline">View all</Link>
          </div>
          <div className="space-y-3">
            {stats.recent_matches.map((match) => (
              <div key={match.id} className="flex justify-between items-center py-2 border-b border-gray-100 last:border-0">
                <div>
                  <p className="font-medium text-gray-800">{match.job.title}</p>
                  <p className="text-sm text-gray-500">{match.job.company}</p>
                </div>
                <span className="text-lg font-bold text-blue-600">
                  {(match.score.overall_score * 100).toFixed(0)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
