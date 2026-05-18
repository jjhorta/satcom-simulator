/**
 * aiStore — tracks only the server-reported config status.
 * The API key is NEVER stored in the browser.
 * UI reads key_is_set + masked_key from the backend config endpoint.
 */
import { create } from 'zustand'

interface AiStatus {
  keyIsSet:    boolean
  maskedKey:   string
  model:       string
  baseUrl:     string
  systemPrompt: string
  setStatus: (patch: Partial<Omit<AiStatus, 'setStatus'>>) => void
}

export const useAiStore = create<AiStatus>()((set) => ({
  keyIsSet:     false,
  maskedKey:    '',
  model:        'gpt-4o',
  baseUrl:      'https://api.openai.com/v1',
  systemPrompt: '',
  setStatus:    (patch) => set(patch),
}))

/** Returns true if the backend has an API key configured */
export function isAiConfigured(s: Pick<AiStatus, 'keyIsSet'>): boolean {
  return s.keyIsSet
}
