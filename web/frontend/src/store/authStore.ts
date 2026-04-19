import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AuthState {
  token:   string | null
  setToken: (t: string) => void
  logout:  () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token:    null,
      setToken: (t) => set({ token: t }),
      logout:   () => set({ token: null }),
    }),
    { name: 'auth' },
  ),
)
