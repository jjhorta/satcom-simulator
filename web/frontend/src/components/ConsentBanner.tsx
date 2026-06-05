import { useState, useEffect } from 'react'
import { Cookie, X } from 'lucide-react'

const CLARITY_ID = 'wwc9bke5iv'

function loadClarity() {
  if (typeof window === 'undefined' || (window as unknown as Record<string, unknown>).clarity_loaded) return
  try {
    const c = window as unknown as Record<string, unknown>
    const a = 'clarity' in c ? c['clarity'] as (...args: unknown[]) => void : function(...args: unknown[]) {
      const q = ((c['clarity_q'] || []) as unknown[][])
      q.push(args)
      c['clarity_q'] = q
    }
    c['clarity'] = a
    const t = document.createElement('script')
    t.async = true
    t.src = `https://www.clarity.ms/tag/${CLARITY_ID}`
    const y = document.getElementsByTagName('script')[0]
    y?.parentNode?.insertBefore(t, y)
    ;(window as unknown as Record<string, unknown>).clarity_loaded = true
  } catch { /* ignore */ }
}

export default function ConsentBanner() {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const consent = localStorage.getItem('consent-analytics')
    if (consent === 'accepted') {
      loadClarity()
    } else if (!consent) {
      setVisible(true)
    }
  }, [])

  const accept = () => {
    localStorage.setItem('consent-analytics', 'accepted')
    loadClarity()
    setVisible(false)
  }

  const reject = () => {
    localStorage.setItem('consent-analytics', 'rejected')
    setVisible(false)
  }

  if (!visible) return null

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 p-4">
      <div className="max-w-2xl mx-auto bg-gray-900 border border-gray-800 rounded-2xl p-5 shadow-2xl">
        <div className="flex items-start gap-3">
          <Cookie className="w-5 h-5 text-indigo-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <p className="text-sm text-gray-300 font-medium mb-1">We value your privacy</p>
            <p className="text-xs text-gray-500 leading-relaxed">
              We use Microsoft Clarity to understand how you interact with the platform — 
              anonymized click maps and session recordings to improve the experience. 
              No personal data is collected. <a href="/privacy" target="_blank" className="text-indigo-400 hover:text-indigo-300 underline">Learn more</a>
            </p>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <button onClick={reject}
              className="px-3 py-1.5 text-xs text-gray-400 hover:text-white border border-gray-700 rounded-lg hover:border-gray-500 transition-colors">
              Reject
            </button>
            <button onClick={accept}
              className="px-3 py-1.5 text-xs font-medium bg-indigo-600 text-white rounded-lg hover:bg-indigo-500 transition-colors">
              Accept
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
