import { Users, User } from 'lucide-react'

interface EvaluationStatusBadgeProps {
  status: string
}

export function EvaluationStatusBadge({ status }: EvaluationStatusBadgeProps) {
  const styles =
    status === 'COMPLETED'
      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
      : status === 'PARTIAL'
      ? 'bg-amber-50 text-amber-700 border-amber-200'
      : status === 'FAILED'
      ? 'bg-rose-50 text-rose-700 border-rose-200'
      : 'bg-blue-50 text-blue-700 border-blue-200'

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${styles}`}>
      {status}
    </span>
  )
}

interface PresentationTypeBadgeProps {
  type: 'INDIVIDUAL' | 'GROUP' | string
  memberCount?: number
}

export function PresentationTypeBadge({ type, memberCount }: PresentationTypeBadgeProps) {
  const isGroup = type === 'GROUP'
  return (
    <span
      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium border ${
        isGroup
          ? 'bg-purple-50 text-purple-700 border-purple-200'
          : 'bg-blue-50 text-blue-700 border-blue-200'
      }`}
    >
      {isGroup ? <Users className="w-3 h-3" /> : <User className="w-3 h-3" />}
      {isGroup ? (memberCount != null ? `Group · ${memberCount}` : 'Group') : 'Individual'}
    </span>
  )
}

