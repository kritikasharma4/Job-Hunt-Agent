import { useState } from 'react'
import { jobsApi, applicationsApi } from '../api/client'
import SearchForm from '../components/SearchForm'
import JobCard from '../components/JobCard'

export default function JobSearchPage() {
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [applyMessage, setApplyMessage] = useState(null)

  const handleSearch = async (params) => {
    setLoading(true)
    setError(null)
    setResults(null)
    try {
      const res = await jobsApi.search(params)
      setResults(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Search failed. Make sure you have a profile set up.')
    }
    setLoading(false)
  }

  const handleApply = async (jobId) => {
    setApplyMessage(null)
    try {
      await applicationsApi.create({ job_id: jobId })
      setApplyMessage({ type: 'success', text: 'Application submitted!' })
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to submit application'
      setApplyMessage({ type: 'error', text: msg })
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Job Search</h2>

      <SearchForm onSearch={handleSearch} loading={loading} />

      {error && (
        <div className="mt-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">{error}</div>
      )}

      {applyMessage && (
        <div className={`mt-4 p-3 rounded-lg text-sm ${
          applyMessage.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
        }`}>
          {applyMessage.text}
        </div>
      )}

      {loading && (
        <div className="mt-8 text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <p className="mt-2 text-gray-500">Searching and scoring jobs... This may take a moment.</p>
        </div>
      )}

      {results && (
        <div className="mt-6">
          <div className="flex justify-between items-center mb-4">
            <p className="text-sm text-gray-500">
              Found <strong>{results.total_fetched}</strong> jobs, <strong>{results.total_matched}</strong> match your profile
            </p>
          </div>

          {results.matches.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
              <p className="text-gray-500">No matching jobs found. Try broadening your search.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {results.matches.map((match) => (
                <JobCard key={match.job.job_id} match={match} onApply={handleApply} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
