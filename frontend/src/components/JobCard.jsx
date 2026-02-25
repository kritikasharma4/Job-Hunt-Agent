import MatchScoreBar from './MatchScoreBar'

export default function JobCard({ match, onApply }) {
  const { job, score } = match

  const locationStr = job.location?.remote
    ? 'Remote'
    : [job.location?.city, job.location?.state].filter(Boolean).join(', ') || 'N/A'

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 hover:shadow-md transition-shadow">
      <div className="flex justify-between items-start mb-4">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-800">{job.title}</h3>
          <p className="text-gray-600">{job.company}</p>
          <div className="flex gap-3 mt-2 text-sm text-gray-500">
            <span>{locationStr}</span>
            {job.source && (
              <span className="bg-gray-100 px-2 py-0.5 rounded text-xs capitalize">
                {job.source}
              </span>
            )}
            {job.level && (
              <span className="bg-blue-50 text-blue-600 px-2 py-0.5 rounded text-xs capitalize">
                {job.level}
              </span>
            )}
          </div>
        </div>
        <div className="text-right ml-4">
          <div className="text-2xl font-bold text-blue-600">
            {(score.overall_score * 100).toFixed(0)}%
          </div>
          <p className="text-xs text-gray-500">match</p>
        </div>
      </div>

      <MatchScoreBar score={score} />

      {/* Skills */}
      <div className="mt-4 flex flex-wrap gap-2">
        {score.matching_skills?.slice(0, 5).map((skill) => (
          <span key={skill} className="bg-green-50 text-green-700 px-2 py-1 rounded text-xs">
            {skill}
          </span>
        ))}
        {score.missing_skills?.slice(0, 3).map((skill) => (
          <span key={skill} className="bg-red-50 text-red-600 px-2 py-1 rounded text-xs">
            {skill}
          </span>
        ))}
      </div>

      {/* Actions */}
      <div className="mt-4 flex gap-3">
        {job.url && (
          <a
            href={job.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-blue-600 hover:underline"
          >
            View Job
          </a>
        )}
        {onApply && (
          <button
            onClick={() => onApply(job.job_id)}
            className="ml-auto bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            Apply
          </button>
        )}
      </div>
    </div>
  )
}
