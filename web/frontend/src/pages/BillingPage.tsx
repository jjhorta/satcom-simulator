// web/frontend/src/pages/BillingPage.tsx
// Pricing page: 3 vertical columns showing tier name, price, features clearly

import { useState, useEffect } from 'react'
import { useAuthStore } from '../store/authStore'
import { getSubscription, createCheckoutSession } from '../api/client'
import TierBadge from '../components/TierBadge'
import RoleBadge from '../components/RoleBadge'
import {
  Check, X as XIcon, Zap, Building2, Satellite, Brain,
  Download, TrendingUp, Globe, Shield, Cpu, Infinity,
} from 'lucide-react'

// ── Types ───────────────────────────────────────────────────────────────────

interface PlanFeature {
  text: string
  included: boolean
  icon?: any
  highlight?: boolean
}

interface Plan {
  id: string
  name: string
  tagline: string
  price: string
  period: string
  annualPrice?: string
  annualPeriod?: string
  description: string
  color: string
  borderColor: string
  bgColor: string
  icon: any
  features: PlanFeature[]
  cta: string
  priceId?: string
  popular?: boolean
  disabled?: boolean
}

// ── Plan definitions ─────────────────────────────────────────────────────────

const PLANS: Plan[] = [
  {
    id: 'free',
    name: 'Free',
    tagline: 'Try before you buy',
    price: '€0',
    period: '',
    description: '3 free heatmap simulations to explore the platform. No credit card required.',
    color: 'text-gray-400',
    borderColor: 'border-gray-800',
    bgColor: 'bg-gray-900/50',
    icon: null,
    features: [
      { text: '3 free simulations to try the platform', included: true, icon: TrendingUp, highlight: true },
      { text: 'Heatmap mode (10° resolution)', included: true, icon: Globe },
      { text: 'PNG export with watermark', included: true, icon: Download },
      { text: 'View shared reports & simulations', included: true },
      { text: 'Multi-shell constellations', included: false, icon: XIcon },
      { text: 'TCO analysis', included: false, icon: XIcon },
      { text: 'AI-powered analysis', included: false, icon: XIcon },
      { text: 'Plotly interactive export', included: false, icon: XIcon },
      { text: 'Team management', included: false, icon: XIcon },
    ],
    cta: 'Free Trial',
    disabled: false,
  },
  {
    id: 'pro',
    name: 'Pro',
    tagline: 'Upgrade from Demo — unlock everything',
    price: '€299',
    period: '/month',
    annualPrice: '€2,990',
    annualPeriod: '/year',
    description: 'Everything you need to design, simulate, and analyse satellite constellations professionally.',
    color: 'text-indigo-400',
    borderColor: 'border-indigo-500',
    bgColor: 'bg-indigo-900/10',
    icon: Zap,
    features: [
      { text: 'Up to 250 satellites, 72 orbital planes', included: true, icon: Satellite, highlight: true },
      { text: '500 simulations per month', included: true, icon: TrendingUp },
      { text: '3 concurrent simulation jobs', included: true },
      { text: 'Multi-shell (up to 5 shells)', included: true, icon: Globe },
      { text: 'Full RF link budget analysis', included: true },
      { text: 'Complete TCO business model', included: true, icon: TrendingUp },
      { text: 'AI analysis (10 per month)', included: true, icon: Brain },
      { text: 'Export: PNG, CSV, GIF, HTML (Plotly)', included: true, icon: Download },
      { text: '90-day job retention', included: true },
    ],
    cta: 'Subscribe',
    priceId: 'price_pro_monthly',
    popular: true,
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    tagline: 'For teams & mission-critical ops',
    price: '€999',
    period: '/month',
    annualPrice: '€9,990',
    annualPeriod: '/year',
    description: 'Unlimited simulations, API access, dedicated support, and on-premise deployment options.',
    color: 'text-amber-400',
    borderColor: 'border-amber-600',
    bgColor: 'bg-amber-900/10',
    icon: Building2,
    features: [
      { text: 'Unlimited satellites & planes', included: true, icon: Infinity, highlight: true },
      { text: 'Unlimited simulations per month', included: true, icon: Infinity },
      { text: '10 concurrent simulation jobs', included: true },
      { text: 'Multi-shell (unlimited shells)', included: true },
      { text: 'End-to-end latency / ISL routing', included: true, icon: Globe },
      { text: 'Unlimited AI analysis', included: true, icon: Brain },
      { text: 'JSON API + webhooks', included: true, icon: Cpu },
      { text: 'Priority support + 99.9% SLA', included: true, icon: Shield },
      { text: 'SSO / SAML authentication', included: true, icon: Shield },
      { text: 'On-premise & white-label', included: true },
      { text: '365-day job retention', included: true },
    ],
    cta: 'Subscribe',
    priceId: 'price_enterprise_monthly',
  },
]

// ── Component ───────────────────────────────────────────────────────────────

export default function BillingPage() {
  const auth = useAuthStore()
  const tier = auth.tier
  const role = auth.role
  const [subscription, setSubscription] = useState<any>(null)
  const [annual, setAnnual] = useState(false)
  const [promoCode, setPromoCode] = useState('')
  const [promoStatus, setPromoStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
  const [promoMessage, setPromoMessage] = useState('')

  useEffect(() => {
    getSubscription()
      .then(setSubscription)
      .catch(() => {})
  }, [])

  const handleSubscribe = async (plan: Plan) => {
    if (plan.id === 'free') {
      // Free trial: just navigate to new simulation
      window.location.href = '/new-simulation'
      return
    }
    const priceId = annual && plan.id === 'pro'
      ? 'price_pro_annual'
      : annual && plan.id === 'enterprise'
      ? 'price_enterprise_annual'
      : plan.priceId!
    const result = await createCheckoutSession(priceId)
    if (result?.url) window.location.href = result.url
  }

  const handleRedeem = async () => {
    if (!promoCode.trim()) return
    setPromoStatus('loading')
    try {
      const { default: axios } = await import('axios')
      const result = await axios.post('/api/billing/redeem', { code: promoCode.trim() })
      setPromoStatus('success')
      setPromoMessage(result.data.message)
      setPromoCode('')
    } catch (err: any) {
      setPromoStatus('error')
      setPromoMessage(err.response?.data?.detail || 'Invalid code')
    }
  }

  const handlePortal = async () => {
    const { default: axios } = await import('axios')
    const res = await axios.get('/api/billing/portal')
    if (res.data?.url) window.location.href = res.data.url
  }

  const currentTier = tier
  const isSubscribed = subscription?.subscription_status === 'active'

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* ── Header ──────────────────────────────────────────────────── */}
      <div className="border-b border-gray-800 bg-gray-900/50">
        <div className="max-w-6xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">Billing & Plan</h1>
              <p className="text-gray-400 mt-1">
                {auth.orgName ?? auth.email?.split('@')[0] ?? 'Team'} · <RoleBadge role={auth.role ?? 'viewer'} /> · <TierBadge tier={auth.tier ?? 'free'} />
              </p>
            </div>
            {isSubscribed && (
              <button
                onClick={handlePortal}
                className="px-4 py-2 rounded-lg border border-gray-700 text-sm text-gray-300
                           hover:bg-gray-800 hover:text-white transition-colors"
              >
                Manage Subscription
              </button>
            )}
          </div>

          {/* Usage bar */}
          {subscription && (
            <div className="mt-4 flex items-center gap-4 text-sm text-gray-500">
              {role === 'viewer' && !subscription.demo_jobs_remaining ? (
                <span className="text-indigo-400">
                  Free tier: 3 trial simulations available
                </span>
              ) : subscription.jobs_remaining !== undefined && subscription.jobs_remaining >= 0 ? (
                <span>
                  Simulations this month:{' '}
                  <span className="text-gray-300 font-semibold">{subscription.jobs_used || 0}</span>
                  /<span className="text-gray-400">{subscription.jobs_limit || '∞'}</span>
                  <span className="text-gray-600 ml-2">
                    ({subscription.jobs_remaining} remaining)
                  </span>
                </span>
              ) : subscription.demo_jobs_remaining !== undefined ? (
                <span className="text-amber-400">
                  Demo: {subscription.demo_jobs_remaining} simulations remaining
                </span>
              ) : (
                <span className="text-green-400">Unlimited simulations</span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ── Annual / Monthly toggle ────────────────────────────────── */}
      <div className="max-w-6xl mx-auto px-6 pt-8 pb-4">
        <div className="flex items-center justify-center gap-3">
          <span className={`text-sm ${!annual ? 'text-white font-semibold' : 'text-gray-500'}`}>
            Monthly
          </span>
          <button
            onClick={() => setAnnual(!annual)}
            className={`relative w-12 h-6 rounded-full transition-colors ${
              annual ? 'bg-indigo-600' : 'bg-gray-700'
            }`}
          >
            <span
              className={`absolute top-0.5 w-5 h-5 rounded-full bg-white transition-transform ${
                annual ? 'translate-x-6' : 'translate-x-0.5'
              }`}
            />
          </button>
          <span className={`text-sm ${annual ? 'text-white font-semibold' : 'text-gray-500'}`}>
            Annual <span className="text-green-400 text-xs">(save ~17%)</span>
          </span>
        </div>
      </div>

      {/* ── Plan cards ─────────────────────────────────────────────── */}
      <div className="max-w-6xl mx-auto px-6 pb-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-stretch">
          {PLANS.map((plan) => {
            const isCurrent = plan.id === currentTier
            const isDemoTier = currentTier === 'demo' && plan.id === 'pro'
            const displayPrice = annual && plan.annualPrice ? plan.annualPrice : plan.price
            const displayPeriod = annual && plan.annualPeriod ? plan.annualPeriod : plan.period
            const Icon = plan.icon

            return (
              <div
                key={plan.id}
                className={`relative flex flex-col rounded-2xl border transition-all duration-200 ${
                  isCurrent
                    ? `${plan.borderColor} ring-1 ${plan.borderColor.replace('border', 'ring')}`
                    : plan.popular
                    ? 'border-indigo-500/50 hover:border-indigo-400'
                    : 'border-gray-800 hover:border-gray-700'
                } ${plan.bgColor}`}
              >
                {/* Badges */}
                {plan.popular && !isCurrent && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full
                                  bg-indigo-600 text-white text-xs font-semibold shadow-lg">
                    MOST POPULAR
                  </div>
                )}
                {isCurrent && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full
                                  bg-green-600 text-white text-xs font-semibold shadow-lg">
                    CURRENT PLAN
                  </div>
                )}

                {/* Header */}
                <div className="p-6 pb-4">
                  <div className="flex items-center gap-2 mb-1">
                    {Icon && <Icon className={`w-5 h-5 ${plan.color}`} />}
                    <h3 className={`text-lg font-bold ${plan.color}`}>{plan.name}</h3>
                  </div>
                  <p className="text-xs text-gray-500 mb-4">{plan.tagline}</p>
                  <div className="flex items-baseline gap-1">
                    <span className="text-4xl font-bold">{displayPrice}</span>
                    <span className="text-sm text-gray-500">{displayPeriod}</span>
                  </div>
                  {annual && plan.annualPrice && (
                    <p className="text-xs text-green-400 mt-1">
                      vs {plan.price}{plan.period} — save ~17%
                    </p>
                  )}
                  <p className="text-xs text-gray-500 mt-3 leading-relaxed">{plan.description}</p>
                </div>

                {/* Features */}
                <div className="flex-1 px-6 pb-4 space-y-2.5">
                  {plan.features.map((feat, i) => (
                    <div key={i} className="flex items-start gap-2.5">
                      {feat.icon ? (
                        feat.icon === XIcon ? (
                          <XIcon className="w-4 h-4 text-gray-600 mt-0.5 shrink-0" />
                        ) : (
                          <feat.icon className={`w-4 h-4 ${
                            feat.highlight ? 'text-indigo-400' : 'text-green-400'
                          } mt-0.5 shrink-0`} />
                        )
                      ) : (
                        <div className={`w-4 h-4 mt-0.5 shrink-0 rounded-full flex items-center justify-center ${
                          feat.included ? 'bg-green-500/20' : 'bg-gray-800'
                        }`}>
                          {feat.included ? (
                            <Check className="w-3 h-3 text-green-400" />
                          ) : (
                            <XIcon className="w-3 h-3 text-gray-600" />
                          )}
                        </div>
                      )}
                      <span className={`text-xs leading-relaxed ${
                        feat.highlight ? 'text-white font-medium' : 'text-gray-400'
                      }`}>
                        {feat.text}
                      </span>
                    </div>
                  ))}
                </div>

                {/* CTA */}
                <div className="px-6 pb-6 mt-auto">
                  <button
                    onClick={() => handleSubscribe(plan)}
                    disabled={isCurrent || (isDemoTier && plan.id === 'pro')}
                    className={`w-full py-2.5 rounded-xl font-semibold transition-all ${
                      isCurrent || (isDemoTier && plan.id === 'pro')
                        ? 'bg-gray-800 text-gray-400 cursor-not-allowed'
                        : plan.popular
                        ? 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/20'
                        : plan.id === 'free'
                        ? 'bg-gray-800 hover:bg-gray-700 text-gray-200'
                        : 'bg-gray-800 hover:bg-gray-700 text-gray-200'
                    }`}
                  >
                    {isDemoTier && plan.id === 'pro'
                      ? 'Try Pro (Demo Active)'
                      : isCurrent
                      ? 'Current Plan'
                      : plan.cta}
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* ── Promo Code ─────────────────────────────────────────────── */}
      <div className="max-w-6xl mx-auto px-6 pb-12">
        <div className="p-6 rounded-2xl border border-gray-800 bg-gray-900/30">
          <h3 className="text-lg font-semibold mb-1">Have a promo code?</h3>
          <p className="text-sm text-gray-500 mb-4">
            Enter your code to unlock features or extend your trial.
          </p>
          <div className="flex gap-2 max-w-md">
            <input
              type="text"
              value={promoCode}
              onChange={(e) => setPromoCode(e.target.value.toUpperCase())}
              placeholder="ENTER CODE"
              className="flex-1 px-4 py-2.5 rounded-xl bg-gray-800 border border-gray-700 text-white
                         placeholder-gray-600 font-mono tracking-wider text-sm
                         focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
            <button
              onClick={handleRedeem}
              disabled={promoStatus === 'loading' || !promoCode.trim()}
              className="px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500
                         text-white font-semibold disabled:opacity-50 transition-colors"
            >
              {promoStatus === 'loading' ? 'Applying...' : 'Apply'}
            </button>
          </div>
          {promoStatus === 'success' && (
            <p className="mt-3 text-sm text-green-400 flex items-center gap-1.5">
              <Check className="w-4 h-4" /> {promoMessage}
            </p>
          )}
          {promoStatus === 'error' && (
            <p className="mt-3 text-sm text-red-400">❌ {promoMessage}</p>
          )}
        </div>
      </div>

      {/* ── FAQ ────────────────────────────────────────────────────── */}
      <div className="max-w-3xl mx-auto px-6 pb-16">
        <h3 className="text-lg font-semibold mb-4 text-center">Frequently Asked Questions</h3>
        <div className="space-y-3">
          {[
            {
              q: 'Can I cancel anytime?',
              a: 'Yes. No questions asked. Your jobs remain accessible until the end of the billing period.',
            },
            {
              q: 'What happens when my demo expires?',
              a: 'You become a Viewer — you keep access to shared reports but cannot create new simulations. Your existing jobs are preserved for 14 days.',
            },
            {
              q: 'Can I switch from monthly to annual?',
              a: 'Yes. Use the Stripe Customer Portal to switch. The annual plan saves ~17%.',
            },
            {
              q: 'Do you offer academic discounts?',
              a: 'Yes. Email us with your .edu address for a special academic rate.',
            },
            {
              q: 'Is my data secure?',
              a: 'All data is encrypted at rest. Enterprise tier offers on-premise deployment and SSO/SAML.',
            },
          ].map((faq, i) => (
            <details key={i} className="group">
              <summary className="cursor-pointer text-sm text-gray-300 hover:text-white font-medium py-2
                                     list-none flex items-center justify-between">
                {faq.q}
                <span className="text-gray-600 group-open:rotate-180 transition-transform">▼</span>
              </summary>
              <p className="text-sm text-gray-500 mt-1 pb-2">{faq.a}</p>
            </details>
          ))}
        </div>
      </div>
    </div>
  )
}
