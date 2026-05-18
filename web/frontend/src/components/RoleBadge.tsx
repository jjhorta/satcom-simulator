import type { UserRole } from '../types'

const ROLE_STYLES: Record<UserRole, string> = {
  admin:          'bg-purple-600 text-white',
  team_manager:   'bg-indigo-600 text-white',
  creator:        'bg-blue-600 text-white',
  viewer:         'bg-gray-600 text-gray-200',
  demo:           'bg-amber-500 text-white',
}

const ROLE_LABELS: Record<UserRole, string> = {
  admin:          'Admin',
  team_manager:   'Team Manager',
  creator:        'Creator',
  viewer:         'Viewer',
  demo:           'Demo',
}

export default function RoleBadge({ role, className = '' }: { role: string; className?: string }) {
  const key = role as UserRole
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${
        ROLE_STYLES[key] ?? 'bg-gray-700 text-gray-300'
      } ${className}`}
    >
      {ROLE_LABELS[key] ?? role}
    </span>
  )
}
