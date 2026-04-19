import { create } from 'zustand'
import { persist } from 'zustand/middleware'

const DEFAULT_SYSTEM_PROMPT =
  `You are an expert satellite communications engineer and business analyst.
The user will share simulation logs and outputs from a LEO constellation simulator.
Analyse the results, highlight key findings (coverage gaps, link budget margins, cost drivers),
and provide concise, actionable insights for an executive audience.
Be precise with numbers. Keep your response well-structured using markdown headings.`

interface AiConfig {
  model:        string
  baseUrl:      string
  token:        string
  systemPrompt: string
  setConfig:    (patch: Partial<Omit<AiConfig, 'setConfig'>>) => void
}

export const useAiStore = create<AiConfig>()(
  persist(
    (set) => ({
      model:        'gpt-4o',
      baseUrl:      'https://api.openai.com/v1',
      token:        '',
      systemPrompt: DEFAULT_SYSTEM_PROMPT,
      setConfig:    (patch) => set(patch),
    }),
    { name: 'ai-settings' },
  ),
)

/** Returns true if the minimum required fields are set */
export function isAiConfigured(cfg: Omit<AiConfig, 'setConfig'>): boolean {
  return cfg.baseUrl.trim() !== '' && cfg.token.trim() !== '' && cfg.model.trim() !== ''
}
