'use client'

import posthog from 'posthog-js'
import { PostHogProvider } from 'posthog-js/react'
import { useEffect } from 'react'

const PH_KEY = process.env.NEXT_PUBLIC_POSTHOG_KEY ?? ''

export function PHProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    if (!PH_KEY || posthog.__loaded) return
    posthog.init(PH_KEY, {
      api_host: 'https://us.i.posthog.com',
      capture_pageview: true,
      capture_pageleave: true,
      autocapture: true,
      session_recording: {
        maskAllInputs: false,
        maskInputOptions: { password: true, email: false },
      },
    })
  }, [])

  return <PostHogProvider client={posthog}>{children}</PostHogProvider>
}

export { posthog }
