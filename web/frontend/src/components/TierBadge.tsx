// web/frontend/src/components/TierBadge.tsx
// Shows the organization's active subscription tier

interface TierBadgeProps {
  tier: 'free' | 'demo' | 'pro' | 'enterprise' | string
  className?: string
}

const TIER_STYLES: Record<string, string> = {
  free:       'bg-gray-700 text-gray-300',
  demo:       'bg-amber-600/20 text-amber-400 border border-amber-600/30',
  pro:        'bg-indigo-600 text-white',
  enterprise: 'bg-amber-600 text-white',
}

const TIER_LABELS: Record<string, string> = {
  free:       'Free',
  demo:       'Demo',
  pro:        'Pro',
  enterprise: 'Enterprise',
}

export default function TierBadge({ tier, className = '' }: TierBadgeProps) {
  const style = TIER_STYLES[tier] || TIER_STYLES.free
  const label = TIER_LABELS[tier] || tier

  return (
    <span
      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold ${style} ${className}`}
    >
      {tier === 'pro' && (
        <span className="w-1.5 h-1.5 rounded-full bg-indigo-300 animate-pulse" />
      )}
      {tier === 'enterprise' && (
        <span className="w-1.5 h-1.5 rounded-full bg-amber-300 animate-pulse" />
      )}
      {tier === 'demo' && (
        <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
      )}
      {label}
    </span>
  )
}
