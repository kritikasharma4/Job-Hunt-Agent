import { useState, useEffect } from 'react'
import { applicationsApi } from '../api/client'
import StatusBadge from '../components/StatusBadge'

const STATUSES = ['all', 'pending', 'interview', 'offer', 'accepted', 'rejected', 'withdrawn']
const VALID_STATUSES = ['pending', 'interview', 'offer', 'accepted', 'rejected', 'withdrawn']

export default function ApplicationsPage() {
  const [applications, setApplications] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')
  const [error, setError] = useState(null)

  const fetchApplications = async () => {
    setLoading(true)
    try {
      const params = filter !== 'all' ? { status: filter } : {}
      const res = await applicationsApi.list(params)
      setApplications(res.data)
    } catch (err) {
      setError('Failed to load applications')
    }
    setLoading(false)
  }

  useEffect(() => {
    fetchApplications()
  }, [filter])

  const handleStatusChange = async (applicationId, newStatus) => {
    try {
      await applicationsApi.updateStatus(applicationId, { status: newStatus })
      fetchApplications()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update status')
    }
  }

  const handleDelete = async (applicationId) => {
    try {
      await applicationsApi.delete(applicationId)
      fetchApplications()
    } catch (err) {
      setError('Failed to delete application')
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Applications</h2>

      {/* Status filter tabs */}
      <div className="flex gap-2 mb-6 flex-wrap">
        {STATUSES.map((status) => (
          <button
            key={status}
            onClick={() => setFilter(status)}
            className={`px-4 py-2 rounded-lg text-sm font-medium capitalize transition-colors ${
              filter === status
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
            }`}
          >
            {status}
          </button>
        ))}
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">{error}</div>
      )}

      {loading ? (
        <div className="text-gray-500">Loading applications...</div>
      ) : applications.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
          <p className="text-gray-500">No applications found. Search for jobs and apply!</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Job Title</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Company</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Applied</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {applications.map((app) => (
                <tr key={app.application_id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <p className="font-medium text-gray-800">{app.job_title}</p>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">{app.company}</td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {app.applied_date ? new Date(app.applied_date).toLocaleDateString() : 'N/A'}
                  </td>
                  <td className="px-6 py-4">
                    <select
                      value={app.status}
                      onChange={(e) => handleStatusChange(app.application_id, e.target.value)}
                      className="text-sm border border-gray-200 rounded-lg px-2 py-1 focus:ring-2 focus:ring-blue-500 outline-none"
                    >
                      {VALID_STATUSES.map((s) => (
                        <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
                      ))}
                    </select>
                  </td>
                  <td className="px-6 py-4">
                    <button
                      onClick={() => handleDelete(app.application_id)}
                      className="text-red-500 hover:text-red-700 text-sm"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
