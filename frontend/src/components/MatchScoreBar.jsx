const scoreLabels = {
  skills_score: { label: 'Skills', color: 'bg-blue-500' },
  experience_score: { label: 'Experience', color: 'bg-green-500' },
  location_score: { label: 'Location', color: 'bg-purple-500' },
  salary_score: { label: 'Salary', color: 'bg-orange-500' },
}

export default function MatchScoreBar({ score }) {
  return (
    <div className="space-y-2">
      {/* Overall score */}
      <div className="flex items-center gap-3">
        <span className="text-sm font-medium text-gray-600 w-20">Overall</span>
        <div className="flex-1 bg-gray-200 rounded-full h-3">
          <div
            className="bg-blue-600 h-3 rounded-full transition-all"
            style={{ width: `${(score.overall_score * 100).toFixed(0)}%` }}
          />
        </div>
        <span className="text-sm font-bold text-gray-800 w-12 text-right">
          {(score.overall_score * 100).toFixed(0)}%
        </span>
      </div>

      {/* Component scores */}
      {Object.entries(scoreLabels).map(([key, { label, color }]) => (
        <div key={key} className="flex items-center gap-3">
          <span className="text-xs text-gray-500 w-20">{label}</span>
          <div className="flex-1 bg-gray-100 rounded-full h-2">
            <div
              className={`${color} h-2 rounded-full transition-all`}
              style={{ width: `${((score[key] || 0) * 100).toFixed(0)}%` }}
            />
          </div>
          <span className="text-xs text-gray-500 w-12 text-right">
            {((score[key] || 0) * 100).toFixed(0)}%
          </span>
        </div>
      ))}
    </div>
  )
}
