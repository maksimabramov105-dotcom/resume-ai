'use client';

import { useState } from 'react';

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
          {!playing ? (
            /* Poster / play button overlay */
            <button
              onClick={() => setPlaying(true)}
              className="group relative w-full aspect-video flex items-center justify-center"
              aria-label="Play demo video"
            >
              {/* Poster image / gradient background */}
              <div className="absolute inset-0 bg-gradient-to-br from-violet-900/40 via-slate-900 to-blue-900/40" />

              {/* Fake UI screenshot layer */}
              <div className="absolute inset-0 flex items-center justify-center opacity-30 select-none">
                <div className="w-[70%] h-[60%] rounded-xl border border-white/10 bg-[#141414] p-4">
                  <div className="h-3 w-24 rounded-full bg-violet-500/40 mb-3" />
                  <div className="space-y-2">
                    {[1, 2, 3].map((i) => (
                      <div key={i} className="flex gap-3 items-center">
                        <div className="h-8 w-8 rounded-lg bg-white/5 flex-shrink-0" />
                        <div className="flex-1 space-y-1.5">
                          <div className="h-2 rounded-full bg-white/10 w-3/4" />
                          <div className="h-2 rounded-full bg-white/5 w-1/2" />
                        </div>
                        <div className="h-6 w-16 rounded-lg bg-violet-500/30 flex-shrink-0" />
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Play button */}
              <div className="relative z-10 flex flex-col items-center gap-4">
                <div className="w-20 h-20 rounded-full bg-white/10 border border-white/20 backdrop-blur-sm flex items-center justify-center group-hover:bg-violet-500/30 group-hover:border-violet-400/50 transition-all duration-300">
                  <svg className="w-8 h-8 text-white ml-1" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M8 5v14l11-7z" />
                  </svg>
                </div>
                <span className="text-white/70 text-sm font-medium">Watch 60s demo</span>
              </div>
            </button>
          ) : (
            /* Actual video */
            <video
              className="w-full aspect-video"
              controls
              autoPlay
              poster="/static/demo-poster.jpg"
            >
              <source src="/static/demo.mp4" type="video/mp4" />
              <p className="text-slate-400 p-8 text-center">
                Your browser doesn&apos;t support video. <a href="/static/demo.mp4" className="text-violet-400 underline">Download the demo</a>.
              </p>
            </video>
          )}
        </div>

        {/* Feature bullets below video */}
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
