"use client"

import Link from "next/link";
import StatsBar from "./StatsBar";
import { posthog } from "../providers";

export default function Hero() {
  return (
    <section className="bg-gradient-to-b from-slate-50 to-white dark:from-slate-900 dark:to-slate-800 py-16 sm:py-24 px-4">
      <div className="max-w-4xl mx-auto text-center">
        {/* Trust badge */}
        <div className="inline-flex items-center gap-2 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-sm font-medium px-4 py-1.5 rounded-full mb-6">
          <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
          Bot is live — applying jobs right now
        </div>

        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-slate-900 dark:text-white leading-tight mb-5">
          Auto-Apply to{" "}
          <span className="gradient-text">300+ Jobs</span>{" "}
          Per Day
        </h1>

        <p className="text-lg sm:text-xl text-slate-600 dark:text-slate-300 max-w-2xl mx-auto mb-8">
          Upload your resume once. Our AI applies to Greenhouse, Lever, Workable,
          LinkedIn Easy Apply, and 6 more job boards — while you sleep.
        </p>

        {/* Primary CTA */}
        <div className="flex flex-col sm:flex-row gap-3 justify-center mb-4">
          <a
            href="https://t.me/topbestworkerbot"
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => posthog.capture("cta_clicked", { cta: "hero_telegram", position: "hero" })}
            className="inline-flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-lg font-bold px-8 py-4 rounded-xl shadow-lg transition-all hover:shadow-xl hover:-translate-y-0.5 min-h-[56px]"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.562 8.248l-2.01 9.478c-.148.66-.537.818-1.084.508l-3-2.21-1.447 1.394c-.16.16-.295.295-.605.295l.213-3.053 5.56-5.023c.242-.213-.054-.333-.373-.12L7.34 14.105l-2.95-.924c-.64-.202-.652-.64.136-.948l11.527-4.447c.533-.194 1 .13.83.924l-.321-.462z"/>
            </svg>
            Try Free in Telegram
          </a>
          <a
            href="#pricing"
            className="inline-flex items-center justify-center text-slate-600 dark:text-slate-300 hover:text-blue-600 dark:hover:text-blue-400 font-medium px-6 py-4 rounded-xl border border-slate-200 dark:border-slate-600 transition-colors min-h-[56px]"
          >
            See plans →
          </a>
        </div>

        <p className="text-sm text-slate-500 dark:text-slate-400 mb-10">
          No spam. No data selling. Cancel anytime.
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
