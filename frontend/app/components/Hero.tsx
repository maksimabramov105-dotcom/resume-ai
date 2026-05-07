"use client"

import Link from "next/link";
import StatsBar from "./StatsBar";
import { posthog } from "../providers";

export default function Hero() {
  return (
    <section className="bg-gradient-to-b from-slate-50 to-white dark:from-slate-900 dark:to-slate-800 py-16 sm:py-24 px-4">
      <div className="max-w-4xl mx-auto text-center">
        {/* Social proof badge */}
        <div className="inline-flex items-center gap-2 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-sm font-medium px-4 py-1.5 rounded-full mb-6">
          ⭐ 14 job seekers already using this
        </div>

        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-slate-900 dark:text-white leading-tight mb-5">
          Apply to 300 jobs while you sleep.
        </h1>

        <p className="text-lg sm:text-xl text-slate-600 dark:text-slate-300 max-w-2xl mx-auto mb-8">
          ResumeAI auto-fills Greenhouse, Lever, Workable and LinkedIn Easy Apply — with your resume, tailored for each role. Set it up in 3 minutes.
        </p>

        {/* Primary CTA */}
        <div className="flex flex-col sm:flex-row gap-3 justify-center mb-4">
          <a
            href="/app"
            onClick={() => posthog.capture("cta_clicked", { cta: "hero_webapp", position: "hero" })}
            className="inline-flex items-center justify-center gap-2 bg-amber-500 hover:bg-amber-600 text-white text-lg font-bold px-8 py-4 rounded-xl shadow-lg transition-all hover:shadow-xl hover:-translate-y-0.5 min-h-[56px]"
          >
            Start free — get 3 free auto-applies/day
          </a>
        </div>

        <p className="text-sm text-slate-500 dark:text-slate-400 mb-3">
          No credit card. No spam. Cancel anytime.
        </p>

        <p className="mb-10">
          <a
            href="https://t.me/topbestworkerbot"
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => posthog.capture("cta_clicked", { cta: "hero_telegram", position: "hero" })}
            className="text-slate-600 dark:text-slate-300 hover:text-blue-600 dark:hover:text-blue-400 font-medium transition-colors"
          >
            Open in Telegram →
          </a>
        </p>

        {/* Social proof stats */}
        <StatsBar />

        {/* Platform logos row */}
        <div className="mt-10">
          <p className="text-xs text-slate-400 uppercase tracking-widest mb-4 font-medium">
            Works with
          </p>
          <div className="flex flex-wrap justify-center gap-3 sm:gap-4">
            {[
              "LinkedIn Easy Apply",
              "Greenhouse",
              "Lever",
              "Workable",
              "Adzuna",
              "RemoteOK",
              "The Muse",
              "Arbeitnow",
            ].map((board) => (
              <span
                key={board}
                className="bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 text-slate-700 dark:text-slate-300 text-xs font-medium px-3 py-1.5 rounded-full shadow-sm"
              >
                {board}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
