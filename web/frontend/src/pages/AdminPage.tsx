import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  adminListUsers, adminUpdateRole, adminDeactivateUser, adminActivateUser, adminListOrgs,
} from '../api/client'
import { useAuthStore } from '../store/authStore'
import type { UserRole, UserInfo, OrgInfo } from '../types'
import { ArrowLeft, Search, RefreshCw, Users, Building2, ShieldAlert, Bot, Save } from 'lucide-react'

const ALL_ROLES: UserRole[] = ['admin', 'team_manager', 'creator', 'viewer', 'demo']

export default function AdminPage() {
  const role = useAuthStore((s) => s.role)
  const currentUserId = useAuthStore((s) => s.user?.id)
  const [search, setSearch] = useState('')
  const [filterRole, setFilterRole] = useState('')
  const [tab, setTab] = useState<'users' | 'orgs'>('users')
  const qc = useQueryClient()

  const { data: usersData, isLoading: usersLoading } = useQuery({
    queryKey: ['admin-users', filterRole, search],
    queryFn: () => adminListUsers({ role: filterRole || undefined, search: search || undefined, per_page: 100 }),
    enabled: role === 'admin',
  })

  const { data: orgs, isLoading: orgsLoading } = useQuery({
    queryKey: ['admin-orgs'],
    queryFn: adminListOrgs,
    enabled: role === 'admin' && tab === 'orgs',
  })

  const mutateRole = useMutation({
    mutationFn: ({ userId, newRole }: { userId: number; newRole: UserRole }) =>
      adminUpdateRole(userId, newRole),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-users'] }),
  })

  const mutateDeactivate = useMutation({
    mutationFn: adminDeactivateUser,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-users'] }),
  })

  const mutateActivate = useMutation({
    mutationFn: adminActivateUser,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-users'] }),
  })

  if (role !== 'admin') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-950">
        <div className="text-center space-y-3">
          <ShieldAlert className="w-12 h-12 text-red-500 mx-auto" />
          <p className="text-white font-semibold">Admin access required</p>
          <Link to="/" className="text-indigo-400 text-sm hover:text-indigo-300">← Back to dashboard</Link>
        </div>
      </div>
    )
  }

  const users: UserInfo[] = usersData?.users ?? []

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <header className="flex items-center gap-3 px-6 py-4 bg-gray-900 border-b border-gray-800">
        <Link to="/" className="text-gray-400 hover:text-white"><ArrowLeft className="w-4 h-4" /></Link>
        <ShieldAlert className="w-5 h-5 text-purple-400" />
        <span className="font-semibold">Admin Panel</span>
      </header>

      <div className="max-w-6xl mx-auto p-6 space-y-6">
        {/* Tabs */}
        <div className="flex gap-2">
          {[
            { id: 'users' as const, label: 'Users', icon: Users },
            { id: 'orgs'  as const, label: 'Organizations', icon: Building2 },
          ].map(({ id, label, icon: Icon }) => (
            <button key={id} onClick={() => setTab(id)}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                tab === id ? 'bg-gray-700 text-white' : 'text-gray-400 hover:text-white'
              }`}>
              <Icon className="w-4 h-4" />{label}
            </button>
          ))}
        </div>

        {/* ── Users tab ── */}
        {tab === 'users' && (
          <div className="space-y-4">
            {/* Filters */}
            <div className="flex flex-wrap gap-2">
              <div className="relative flex-1 min-w-48">
                <Search className="absolute left-2.5 top-2.5 w-4 h-4 text-gray-500" />
                <input value={search} onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search email or username…"
                  className="w-full pl-8 pr-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-indigo-500" />
              </div>
              <select value={filterRole} onChange={(e) => setFilterRole(e.target.value)}
                className="px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-sm text-white focus:outline-none focus:ring-1 focus:ring-indigo-500">
                <option value="">All roles</option>
                {ALL_ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
              <button onClick={() => qc.invalidateQueries({ queryKey: ['admin-users'] })}
                className="p-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-400 hover:text-white">
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
              {ALL_ROLES.map((r) => {
                const count = users.filter((u) => u.role === r).length
                return (
                  <div key={r} className="bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 text-center">
                    <p className="text-xs text-gray-500 uppercase tracking-wider">{r}</p>
                    <p className="text-xl font-semibold text-white">{count}</p>
                  </div>
                )
              })}
            </div>

            {/* Table */}
            {usersLoading ? (
              <p className="text-sm text-gray-500 animate-pulse">Loading users…</p>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-gray-800">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="bg-gray-900 text-gray-500 border-b border-gray-800">
                      <th className="text-left px-3 py-2">ID</th>
                      <th className="text-left px-3 py-2">Email</th>
                      <th className="text-left px-3 py-2">Username</th>
                      <th className="text-left px-3 py-2">Role</th>
                      <th className="text-left px-3 py-2">Org</th>
                      <th className="text-left px-3 py-2">Status</th>
                      <th className="text-left px-3 py-2">Created</th>
                      <th className="text-left px-3 py-2">Last login</th>
                      <th className="px-3 py-2">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800">
                    {users.map((u) => (
                      <tr key={u.id} className="hover:bg-gray-900/60 transition-colors">
                        <td className="px-3 py-2 text-gray-500">{u.id}</td>
                        <td className="px-3 py-2 font-mono text-gray-300">{u.email}</td>
                        <td className="px-3 py-2 text-gray-400">{u.username}</td>
                        <td className="px-3 py-2">
                          <select
                            value={u.role}
                            disabled={u.id === currentUserId}
                            onChange={(e) => mutateRole.mutateAsync({ userId: u.id, newRole: e.target.value as UserRole })}
                            className="bg-gray-800 border border-gray-700 rounded px-1.5 py-0.5 text-xs text-white focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:opacity-50"
                          >
                            {ALL_ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                          </select>
                        </td>
                        <td className="px-3 py-2 text-gray-500">{u.org_id ?? '—'}</td>
                        <td className="px-3 py-2">
                          <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${u.is_active ? 'text-emerald-300 bg-emerald-900/30' : 'text-red-300 bg-red-900/30'}`}>
                            {u.is_active ? 'active' : 'inactive'}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-gray-500 whitespace-nowrap">
                          {u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}
                        </td>
                        <td className="px-3 py-2 text-gray-500 whitespace-nowrap">
                          {u.last_login_at ? new Date(u.last_login_at).toLocaleDateString() : 'never'}
                        </td>
                        <td className="px-3 py-2 text-center">
                          {u.id !== currentUserId && (
                            u.is_active ? (
                              <button onClick={() => mutateDeactivate.mutateAsync(u.id)}
                                className="text-xs text-red-400 hover:text-red-300 transition-colors">
                                Deactivate
                              </button>
                            ) : (
                              <button onClick={() => mutateActivate.mutateAsync(u.id)}
                                className="text-xs text-emerald-400 hover:text-emerald-300 transition-colors">
                                Activate
                              </button>
                            )
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="px-3 py-2 text-xs text-gray-600">{usersData?.total ?? 0} users total</p>
              </div>
            )}
          </div>
        )}

        {/* ── Orgs tab ── */}
        {tab === 'orgs' && (
          orgsLoading ? (
            <p className="text-sm text-gray-500 animate-pulse">Loading organizations…</p>
          ) : (
            <div className="overflow-x-auto rounded-xl border border-gray-800">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-gray-900 text-gray-500 border-b border-gray-800">
                    <th className="text-left px-3 py-2">ID</th>
                    <th className="text-left px-3 py-2">Name</th>
                    <th className="text-left px-3 py-2">Slug</th>
                    <th className="text-left px-3 py-2">Owner ID</th>
                    <th className="text-left px-3 py-2">Tier</th>
                    <th className="text-right px-3 py-2">Max members</th>
                    <th className="text-left px-3 py-2">Created</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800">
                  {(orgs as OrgInfo[] ?? []).map((o) => (
                    <tr key={o.id} className="hover:bg-gray-900/60 transition-colors">
                      <td className="px-3 py-2 text-gray-500">{o.id}</td>
                      <td className="px-3 py-2 text-gray-300 font-medium">{o.name}</td>
                      <td className="px-3 py-2 font-mono text-gray-500">{o.slug}</td>
                      <td className="px-3 py-2 text-gray-500">{o.owner_id}</td>
                      <td className="px-3 py-2">
                        <span className="px-1.5 py-0.5 rounded text-xs bg-gray-800 text-gray-400">{o.subscription_tier}</span>
                      </td>
                      <td className="px-3 py-2 text-right text-gray-400">{o.max_members}</td>
                      <td className="px-3 py-2 text-gray-500 whitespace-nowrap">
                        {o.created_at ? new Date(o.created_at).toLocaleDateString() : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        )}
      </div>
    </div>
  )
}