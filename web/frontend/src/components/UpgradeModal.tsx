// web/frontend/src/components/UpgradeModal.tsx
// Modal shown when a user hits their tier's limits

import { X, Satellite, TrendingUp, Brain, Download, Globe, Check } from 'lucide-react'

interface UpgradeModalProps {
  open: boolean
  onClose: () => void
  reason?: string
  suggestedTier?: 'pro' | 'enterprise'
}

const FEATURES: Record<string, Array<{ icon?: any; text: string }>> = {
  pro: [
    { icon: Satellite, text: 'Up to 250 satellites, 72 orbital planes' },
    { icon: TrendingUp, text: '500 simulations per month, 3 concurrent jobs' },
    { icon: Brain, text: 'AI-powered analysis (10 per month)' },
    { icon: Download, text: 'Export: PNG, CSV, GIF, HTML (Plotly)' },
    { icon: Globe, text: 'Multi-shell constellations (up to 5 shells)' },
    { text: 'Full TCO analysis' },
    { text: '90-day job retention' },
  ],
  enterprise: [
    { icon: Satellite, text: 'Unlimited satellites & planes' },
    { icon: TrendingUp, text: 'Unlimited simulations & concurrent jobs' },
    { icon: Brain, text: 'Unlimited AI analysis' },
    { icon: Download, text: 'All export formats + JSON API' },
    { icon: Globe, text: 'End-to-end latency / ISL routing' },
    { text: 'Priority support + 99.9% SLA' },
    { text: 'SSO/SAML + on-premise option' },
  ],
}

export default function UpgradeModal({
  open,
  onClose,
  reason,
  suggestedTier = 'pro',
}: UpgradeModalProps) {
  if (!open) return null

  const price = suggestedTier === 'enterprise' ? '€999' : '€299'
  const annualPrice = suggestedTier === 'enterprise' ? '€9,990' : '€2,990'
  const features = FEATURES[suggestedTier]

  const handleSubscribe = async () => {
    const priceId =
      suggestedTier === 'enterprise' ? 'price_enterprise_monthly' : 'price_pro_monthly'
    try {
      const { default: axios } = await import('axios')
      const res = await axios.post('/api/billing/create-checkout', { price_id: priceId })
      if (res.data?.url) window.location.href = res.data.url
    } catch {
      // silent
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-gray-900 rounded-2xl border border-gray-700 shadow-2xl max-w-lg w-full mx-4 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
          <div>
            <h2 className="text-lg font-semibold text-white">
              Upgrade to {suggestedTier === 'enterprise' ? 'Enterprise' : 'Pro'}
            </h2>
            {reason && (
              <p className="text-xs text-amber-400 mt-1">{reason}</p>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Features */}
        <div className="px-6 py-5 space-y-3">
          {features.map((feat, i) => (
            <div key={i} className="flex items-start gap-3 text-sm text-gray-300">
              {feat.icon ? (
                <feat.icon className="w-4 h-4 text-indigo-400 mt-0.5 shrink-0" />
              ) : (
                <Check className="w-4 h-4 text-green-400 mt-0.5 shrink-0" />
              )}
              <span>{feat.text}</span>
            </div>
          ))}
        </div>

        {/* CTA */}
        <div className="px-6 py-5 border-t border-gray-800 bg-gray-900/50 text-center">
          <p className="text-3xl font-bold text-white mb-1">
            {price}<span className="text-sm font-normal text-gray-400">/month</span>
          </p>
          <p className="text-xs text-gray-500 mb-4">
            Or {annualPrice}/year <span className="text-green-400">(save ~17%)</span>
          </p>
          <button
            onClick={handleSubscribe}
            className="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500
                       text-white font-semibold shadow-lg shadow-indigo-600/20 transition-colors"
          >
            Upgrade Now
          </button>
          <p className="text-xs text-gray-600 mt-2">
            Cancel anytime. No questions asked.
          </p>
        </div>
      </div>
    </div>
  )
}
