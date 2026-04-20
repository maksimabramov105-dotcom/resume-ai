'use client'

import { useEffect, useRef } from 'react'
import { posthog } from '../providers'

export default function ScrollTracker() {
  const fired = useRef({ 50: false, 100: false })

  useEffect(() => {
    const handler = () => {
      const scrolled = window.scrollY + window.innerHeight
      const total = document.documentElement.scrollHeight
      const pct = (scrolled / total) * 100

      if (pct >= 50 && !fired.current[50]) {
        fired.current[50] = true
        posthog.capture('page_scrolled', { depth: 50 })
      }
      if (pct >= 99 && !fired.current[100]) {
        fired.current[100] = true
        posthog.capture('page_scrolled', { depth: 100 })
      }
    }

    window.addEventListener('scroll', handler, { passive: true })
    return () => window.removeEventListener('scroll', handler)
  }, [])

  return null
}
