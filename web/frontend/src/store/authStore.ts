import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { UserRole, UserInfo } from '../types'

interface AuthState {
  token:    string | null
  user:     UserInfo | null
  // Convenience accessors
  email:    string | null
  username: string | null
  role:     UserRole | null
  orgId:    number | null
  orgName:  string | null
  // Actions
  setToken: (t: string) => void
  setUser:  (u: UserInfo) => void
  logout:   () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token:    null,
      user:     null,
      email:    null,
      username: null,
      role:     null,
      orgId:    null,
      orgName:  null,

      setToken: (t) => set({ token: t }),

      setUser: (u) => set({
        user:     u,
        email:    u.email,
        username: u.username,
        role:     u.role,
        orgId:    u.org_id ?? null,
        orgName:  u.org_name ?? null,
      }),

      logout: () => set({
        token: null, user: null,
        email: null, username: null, role: null, orgId: null, orgName: null,
      }),
    }),
    { name: 'auth' },
  ),
)
