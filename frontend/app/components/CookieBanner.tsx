'use client'

import { useState, useEffect } from 'react'
import posthog from 'posthog-js'

const COOKIE_KEY = '_cookie_consent'

export function CookieBanner() {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const stored = localStorage.getItem(COOKIE_KEY)
    if (!stored) setVisible(true)
    if (stored === 'accepted') {
      if (posthog.__loaded) posthog.opt_in_capturing()
      if (typeof (window as any).gtag === 'function') {
        ;(window as any).gtag('consent', 'update', { analytics_storage: 'granted' })
      }
    }
    if (stored === 'declined' && posthog.__loaded) {
      posthog.opt_out_capturing()
    }
  }, [])

  const accept = () => {
    localStorage.setItem(COOKIE_KEY, 'accepted')
    if (posthog.__loaded) posthog.opt_in_capturing()
    // Grant GA4 analytics
    if (typeof window !== 'undefined' && typeof (window as any).gtag === 'function') {
      ;(window as any).gtag('consent', 'update', { analytics_storage: 'granted' })
    }
    setVisible(false)
  }

  const decline = () => {
    localStorage.setItem(COOKIE_KEY, 'declined')
    if (posthog.__loaded) posthog.opt_out_capturing()
    // GA4 stays denied (default set in layout.tsx)
    setVisible(false)
  }

  if (!visible) return null

  return (
    <div
      role="dialog"
      aria-label="Cookie consent"
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        zIndex: 9999,
        background: '#0F172A',
        color: '#F1F5F9',
        padding: '16px 24px',
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        gap: '12px',
        boxShadow: '0 -4px 24px rgba(0,0,0,0.3)',
        fontSize: '14px',
        lineHeight: '1.5',
      }}
    >
      <span style={{ flex: '1 1 260px' }}>
        We use cookies for analytics and to improve your experience.{' '}
        <a
          href="/privacy.html"
          style={{ color: '#60A5FA', textDecoration: 'underline' }}
        >
          Privacy Policy
        </a>
      </span>
      <div style={{ display: 'flex', gap: '10px', flexShrink: 0 }}>
        <button
          onClick={decline}
          style={{
            padding: '8px 18px',
            borderRadius: '8px',
            border: '1px solid #475569',
            background: 'transparent',
            color: '#94A3B8',
            cursor: 'pointer',
            fontWeight: 500,
            fontSize: '13px',
          }}
        >
          Decline
        </button>
        <button
          onClick={accept}
          style={{
            padding: '8px 18px',
            borderRadius: '8px',
            border: 'none',
            background: '#2563EB',
            color: '#fff',
            cursor: 'pointer',
            fontWeight: 600,
            fontSize: '13px',
          }}
        >
          Accept
        </button>
      </div>
    </div>
  )
}
