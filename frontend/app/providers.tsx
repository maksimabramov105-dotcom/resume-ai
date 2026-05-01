'use client'

import posthog from 'posthog-js'
import { PostHogProvider } from 'posthog-js/react'
import { useEffect } from 'react'
import { usePathname, useSearchParams } from 'next/navigation'

const PH_KEY = process.env.NEXT_PUBLIC_POSTHOG_KEY ?? ''

/** Persist UTM params from URL into sessionStorage so they survive SPA navigation. */
function captureUTM() {
  if (typeof window === 'undefined') return
  const params = new URLSearchParams(window.location.search)
  const utmKeys = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term', 'ref', 'gclid', 'fbclid']
  const stored: Record<string, string> = JSON.parse(sessionStorage.getItem('_utm') ?? '{}')
  let updated = false
  for (const k of utmKeys) {
    const v = params.get(k)
    if (v && !stored[k]) { stored[k] = v; updated = true }
  }
  if (updated) sessionStorage.setItem('_utm', JSON.stringify(stored))
  return stored
}

/** Return stored UTM properties (empty object if none). */
export function getStoredUTM(): Record<string, string> {
  if (typeof window === 'undefined') return {}
  try { return JSON.parse(sessionStorage.getItem('_utm') ?? '{}') } catch { return {} }
}

export function PHProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const searchParams = useSearchParams()

  useEffect(() => {
    // Capture UTM params on every navigation before PostHog init
    const utm = captureUTM()

    if (!PH_KEY || posthog.__loaded) return

    posthog.init(PH_KEY, {
      api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST ?? 'https://us.i.posthog.com',
      // Don't fire $pageview automatically — we fire it manually below with UTM props
      capture_pageview: false,
      capture_pageleave: true,
      autocapture: true,
      persistence: 'cookie',          // survives cross-tab navigation
      bootstrap: { distinctID: undefined },
      session_recording: {
        maskAllInputs: false,
        maskInputOptions: { password: true },
      },
    })

    // Fire initial pageview with UTM properties attached
    posthog.capture('$pageview', { ...utm })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Fire $pageview on every SPA route change
  useEffect(() => {
    if (!posthog.__loaded) return
    const utm = getStoredUTM()
    posthog.capture('$pageview', {
      $current_url: window.location.href,
      ...utm,
    })
  }, [pathname, searchParams])

  return <PostHogProvider client={posthog}>{children}</PostHogProvider>
}

export { posthog }
