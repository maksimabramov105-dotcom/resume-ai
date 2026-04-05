import { create } from 'zustand'
import { getUser } from '../services/api'

interface User {
  telegram_id: number
  username: string | null
  full_name: string | null
  credits_resume: number
  credits_cover_letter: number
  credits_interview: number
  credits_assistant: number
  subscription_type: string
  total_resumes_generated: number
  total_assistant_messages: number
  total_spent_rub: number
  referral_code: string | null
}

interface UserState {
  user: User | null
  loading: boolean
  error: string | null
  fetchUser: () => Promise<void>
  decrementCredit: (field: keyof User) => void
}

export const useUserStore = create<UserState>((set) => ({
  user: null,
  loading: true,
  error: null,

  fetchUser: async () => {
    try {
      set({ loading: true, error: null })
      const { data } = await getUser()
      set({ user: data, loading: false })
    } catch (err: any) {
      set({ error: err.message, loading: false })
    }
  },

  decrementCredit: (field) => {
    set((state) => {
      if (!state.user) return state
      const current = state.user[field] as number
      return { user: { ...state.user, [field]: Math.max(0, current - 1) } }
    })
  },
}))
