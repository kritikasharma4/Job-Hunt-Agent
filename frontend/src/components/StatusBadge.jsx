const statusStyles = {
  pending: 'bg-gray-100 text-gray-700',
  interview: 'bg-blue-100 text-blue-700',
  offer: 'bg-green-100 text-green-700',
  accepted: 'bg-emerald-100 text-emerald-700',
  rejected: 'bg-red-100 text-red-700',
  withdrawn: 'bg-yellow-100 text-yellow-700',
}

export default function StatusBadge({ status }) {
  const style = statusStyles[status] || statusStyles.pending
  return (
    <span className={`inline-block px-3 py-1 rounded-full text-xs font-medium capitalize ${style}`}>
      {status}
    </span>
  )
}
