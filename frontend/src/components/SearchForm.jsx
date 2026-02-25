import { useState } from 'react'

export default function SearchForm({ onSearch, loading }) {
  const [query, setQuery] = useState('')
  const [location, setLocation] = useState('')
  const [sources, setSources] = useState(['jsearch'])
  const [minScore, setMinScore] = useState(0.3)
  const [experienceLevel, setExperienceLevel] = useState('')
  const [employmentType, setEmploymentType] = useState('')
  const [datePosted, setDatePosted] = useState('all')
  const [remoteOnly, setRemoteOnly] = useState(false)

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!query.trim()) return
    onSearch({
      query: query.trim(),
      location: location.trim() || null,
      sources,
      min_score: minScore,
      experience_level: experienceLevel || null,
      employment_type: employmentType || null,
      date_posted: datePosted !== 'all' ? datePosted : null,
      remote_only: remoteOnly,
    })
  }

  const toggleSource = (source) => {
    setSources((prev) =>
      prev.includes(source)
        ? prev.filter((s) => s !== source)
        : [...prev, source]
    )
  }

  const selectClass =
    'w-full border border-gray-300 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none bg-white'

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-6">
      {/* Row 1: Query + Location */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Job Title / Keywords</label>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. Python Developer, Data Scientist"
            className="w-full border border-gray-300 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Location</label>
          <input
            type="text"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="e.g. San Francisco, Remote"
            className="w-full border border-gray-300 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          />
        </div>
      </div>

      {/* Row 2: Experience Level + Employment Type + Date Posted */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Experience Level</label>
          <select value={experienceLevel} onChange={(e) => setExperienceLevel(e.target.value)} className={selectClass}>
            <option value="">All Levels</option>
            <option value="entry">Entry Level / Fresher</option>
            <option value="mid">Mid Level (2-5 years)</option>
            <option value="senior">Senior (5+ years)</option>
            <option value="lead">Lead / Manager</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Employment Type</label>
          <select value={employmentType} onChange={(e) => setEmploymentType(e.target.value)} className={selectClass}>
            <option value="">Any Type</option>
            <option value="fulltime">Full-time</option>
            <option value="parttime">Part-time</option>
            <option value="contract">Contract</option>
            <option value="intern">Internship</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Date Posted</label>
          <select value={datePosted} onChange={(e) => setDatePosted(e.target.value)} className={selectClass}>
            <option value="all">Any Time</option>
            <option value="today">Today</option>
            <option value="3days">Last 3 Days</option>
            <option value="week">Last Week</option>
            <option value="month">Last Month</option>
          </select>
        </div>
      </div>

      {/* Row 3: Sources, Remote, Min Score, Submit */}
      <div className="flex flex-wrap items-end gap-6 mt-4">
        {/* Sources */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Sources</label>
          <div className="flex gap-3">
            {[
              { id: 'jsearch', label: 'JSearch (Real Jobs)' },
              { id: 'demo', label: 'Demo' },
            ].map(({ id, label }) => (
              <label key={id} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={sources.includes(id)}
                  onChange={() => toggleSource(id)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">{label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Remote Only */}
        <div>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={remoteOnly}
              onChange={(e) => setRemoteOnly(e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm font-medium text-gray-700">Remote Only</span>
          </label>
        </div>

        {/* Min Score */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Min Score: {(minScore * 100).toFixed(0)}%
          </label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={minScore}
            onChange={(e) => setMinScore(parseFloat(e.target.value))}
            className="w-32"
          />
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="ml-auto bg-blue-600 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? 'Searching...' : 'Search Jobs'}
        </button>
      </div>
    </form>
  )
}
