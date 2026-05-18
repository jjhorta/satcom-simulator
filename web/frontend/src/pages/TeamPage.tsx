import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getTeamMembers, inviteTeamMember } from '../api/client'
import { useAuthStore } from '../store/authStore'
import RoleBadge from '../components/RoleBadge'
import type { UserRole } from '../types'
import { ArrowLeft, Users, Mail, Copy, Check, UserPlus } from 'lucide-react'

const INVITABLE_ROLES: UserRole[] = ['creator', 'viewer', 'demo']

export default function TeamPage() {
  const { role, orgId, orgName } = useAuthStore()
  const [inviteEmail, setInviteEmail]   = useState('')
  const [inviteRole,  setInviteRole]    = useState<UserRole>('creator')
  const [inviteLink,  setInviteLink]    = useState<string | null>(null)
  const [copied,      setCopied]        = useState(false)
  const [inviteError, setInviteError]   = useState('')
  const qc = useQueryClient()

  const canManage = role === 'admin' || role === 'team_manager'

  const { data, isLoading } = useQuery({
    queryKey: ['team-members'],
    queryFn: getTeamMembers,
    enabled: !!orgId,
  })

  const mutateInvite = useMutation({
    mutationFn: () => inviteTeamMember(inviteEmail, inviteRole),
    onSuccess: (res) => {
      setInviteLink(res.link)
      setInviteEmail('')
      setInviteError('')
      qc.invalidateQueries({ queryKey: ['team-members'] })
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setInviteError(typeof detail === 'string' ? detail : 'Failed to create invitation.')
    },
  })

  async function copyLink() {
    if (!inviteLink) return
    await navigator.clipboard.writeText(inviteLink)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const members = data?.members ?? []

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <header className="flex items-center gap-3 px-6 py-4 bg-gray-900 border-b border-gray-800">
        <Link to="/" className="text-gray-400 hover:text-white"><ArrowLeft className="w-4 h-4" /></Link>
        <Users className="w-5 h-5 text-indigo-400" />
        <span className="font-semibold">Team{orgName ? ` — ${orgName}` : ''}</span>
      </header>

      <div className="max-w-3xl mx-auto p-6 space-y-6">
        {/* Members list */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
            <p className="text-sm font-medium text-gray-300">Members ({members.length})</p>
          </div>
          {isLoading ? (
            <p className="px-4 py-6 text-sm text-gray-500 animate-pulse">Loading members…</p>
          ) : members.length === 0 ? (
            <p className="px-4 py-6 text-sm text-gray-600">No members yet. Invite someone below.</p>
          ) : (
            <div className="divide-y divide-gray-800">
              {members.map((m) => (
                <div key={m.id} className="flex items-center justify-between px-4 py-3">
                  <div>
                    <p className="text-sm text-white font-medium">{m.email}</p>
                    <p className="text-xs text-gray-500">{m.username}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <RoleBadge role={m.role} />
                    <span className={`text-xs ${m.is_active ? 'text-emerald-400' : 'text-red-400'}`}>
                      {m.is_active ? 'active' : 'inactive'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Invite form */}
        {canManage && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
            <p className="text-sm font-medium text-gray-300 flex items-center gap-2">
              <UserPlus className="w-4 h-4 text-indigo-400" />
              Invite a member
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="sm:col-span-2">
                <label className="block text-xs text-gray-500 mb-1">Email address</label>
                <input
                  type="email"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder="colleague@example.com"
                  className="w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Role</label>
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value as UserRole)}
                  className="w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-sm text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                >
                  {INVITABLE_ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>
            </div>

            {inviteError && (
              <p className="text-xs text-red-400 bg-red-900/30 px-3 py-2 rounded-lg">{inviteError}</p>
            )}

            <button
              disabled={!inviteEmail.trim() || mutateInvite.isPending}
              onClick={() => mutateInvite.mutate()}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium
                         bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 transition-colors"
            >
              <Mail className="w-3.5 h-3.5" />
              {mutateInvite.isPending ? 'Sending…' : 'Generate invite link'}
            </button>

            {inviteLink && (
              <div className="bg-gray-800 border border-gray-700 rounded-lg p-3 flex items-center gap-2">
                <p className="flex-1 text-xs font-mono text-gray-300 truncate">{inviteLink}</p>
                <button onClick={copyLink}
                  className="flex items-center gap-1 text-xs text-gray-400 hover:text-white transition-colors flex-shrink-0">
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  {copied ? 'Copied' : 'Copy'}
                </button>
              </div>
            )}
          </div>
        )}

        {!orgId && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 text-center text-sm text-gray-500">
            You are not a member of any organization. Register or accept an invitation to join one.
          </div>
        )}
      </div>
    </div>
  )
}
