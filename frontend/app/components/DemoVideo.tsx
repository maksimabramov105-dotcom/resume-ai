'use client';

import { useState } from 'react';

/**
 * DemoVideo — YouTube embed with a custom play-button poster overlay.
 *
 * How to set your video:
 *   NEXT_PUBLIC_DEMO_VIDEO_ID=<YouTube video ID>   (e.g. dQw4w9WgXcQ)
 *
 * When no env var is set the component shows the poster with a "coming soon"
 * call-to-action that deep-links into the Telegram bot.
 */

const VIDEO_ID = process.env.NEXT_PUBLIC_DEMO_VIDEO_ID ?? '';

export default function DemoVideo() {
  const [playing, setPlaying] = useState(false);

  return (
    <section className="py-16 sm:py-24 px-4 bg-slate-950">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-10">
          <span className="inline-block bg-violet-500/15 text-violet-400 text-xs font-semibold px-3 py-1 rounded-full border border-violet-500/25 mb-4">
            See it in action
          </span>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-white mb-3">
            60 seconds to your first application
          </h2>
          <p className="text-slate-400 text-lg max-w-xl mx-auto">
            Watch how ResumeAI Bot finds jobs, tailors your CV, and applies — while you sleep.
          </p>
        </div>

        {/* Video container */}
        <div className="relative rounded-2xl overflow-hidden border border-white/[0.07] bg-[#0f0f0f] shadow-2xl shadow-violet-900/20">
          {playing && VIDEO_ID ? (
            /* ── YouTube iframe ── */
            <div className="relative w-full aspect-video">
              <iframe
                className="absolute inset-0 w-full h-full"
                src={`https://www.youtube.com/embed/${VIDEO_ID}?autoplay=1&rel=0&modestbranding=1`}
                title="ResumeAI Bot demo"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
              />
            </div>
          ) : (
            /* ── Poster / play overlay ── */
            <button
              onClick={() => VIDEO_ID ? setPlaying(true) : undefined}
              className="group relative w-full aspect-video flex items-center justify-center cursor-pointer"
              aria-label="Play demo video"
              type="button"
            >
              {/* Background gradient */}
              <div className="absolute inset-0 bg-gradient-to-br from-violet-900/40 via-slate-900 to-blue-900/40" />

              {/* Animated app UI mockup */}
              <div className="absolute inset-0 flex items-center justify-center opacity-30 select-none pointer-events-none">
                <div className="w-[70%] h-[60%] rounded-xl border border-white/10 bg-[#141414] p-4 overflow-hidden">
                  <div className="h-3 w-24 rounded-full bg-violet-500/40 mb-3" />
                  <div className="space-y-2">
                    {[
                      { w: '3/4', w2: '1/2', dot: 'bg-green-500/60' },
                      { w: '2/3', w2: '2/5', dot: 'bg-violet-500/60' },
                      { w: '4/5', w2: '3/5', dot: 'bg-blue-500/60' },
                    ].map(({ w, w2, dot }, i) => (
                      <div key={i} className="flex gap-3 items-center">
                        <div className={`h-8 w-8 rounded-lg flex-shrink-0 ${dot} opacity-60`} />
                        <div className="flex-1 space-y-1.5">
                          <div className={`h-2 rounded-full bg-white/10 w-${w}`} />
                          <div className={`h-2 rounded-full bg-white/5 w-${w2}`} />
                        </div>
                        <div className="h-6 w-16 rounded-lg bg-violet-500/30 flex-shrink-0" />
                      </div>
                    ))}
                  </div>
                  {/* Simulated "sending" activity bar */}
                  <div className="mt-4 h-1.5 w-full rounded-full bg-white/5">
                    <div className="h-full w-2/3 rounded-full bg-gradient-to-r from-violet-500 to-blue-500 animate-pulse" />
                  </div>
                </div>
              </div>

              {/* Play button */}
              <div className="relative z-10 flex flex-col items-center gap-4">
                <div className={`w-20 h-20 rounded-full border backdrop-blur-sm flex items-center justify-center transition-all duration-300 ${
                  VIDEO_ID
                    ? 'bg-white/10 border-white/20 group-hover:bg-violet-500/30 group-hover:border-violet-400/50'
                    : 'bg-white/5 border-white/10'
                }`}>
                  {VIDEO_ID ? (
                    <svg className="w-8 h-8 text-white ml-1" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M8 5v14l11-7z" />
                    </svg>
                  ) : (
                    <svg className="w-7 h-7 text-white/40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 10.5l4.72-4.72M9 12H3m6 0a3 3 0 100-6 3 3 0 000 6zm6 0a3 3 0 100-6 3 3 0 000 6z" />
                    </svg>
                  )}
                </div>

                {VIDEO_ID ? (
                  <span className="text-white/70 text-sm font-medium group-hover:text-white transition-colors">
                    Watch 60s demo
                  </span>
                ) : (
                  <div className="text-center px-4">
                    <p className="text-white/50 text-sm font-medium mb-3">Demo video coming soon</p>
                    <a
                      href="https://t.me/ResumeAIRobot"
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="inline-flex items-center gap-2 bg-violet-600 hover:bg-violet-500 text-white text-sm font-semibold px-5 py-2.5 rounded-full transition-colors"
                    >
                      Try it free in Telegram →
                    </a>
                  </div>
                )}
              </div>
            </button>
          )}
        </div>

        {/* Feature bullets */}
        <div className="mt-8 grid grid-cols-3 gap-4 text-center">
          {[
            { icon: '⚡', label: 'Under 3 min setup' },
            { icon: '🤖', label: 'Fully automated' },
            { icon: '🎯', label: 'Tailored per job' },
          ].map(({ icon, label }) => (
            <div key={label} className="bg-[#141414] border border-white/[0.07] rounded-xl p-3">
              <div className="text-2xl mb-1">{icon}</div>
              <div className="text-xs text-slate-400 font-medium">{label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
