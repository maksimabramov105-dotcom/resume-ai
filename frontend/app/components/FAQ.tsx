"use client";

import { useState } from "react";

const FAQ_ITEMS = [
  {
    q: "Which job boards does ResumeAI support?",
    a: "LinkedIn Easy Apply, Greenhouse, Lever, Workable, Ashby, SmartRecruiters, Adzuna, RemoteOK, The Muse, and Arbeitnow. More boards are added regularly.",
  },
  {
    q: "Is my data safe?",
    a: "Yes. The Chrome Extension sends applications from your own browser using your existing logged-in sessions — we never store your job board passwords. Your resume data is encrypted at rest.",
  },
  {
    q: "How many applications per day?",
    a: "Trial: 30 over 14 days. Starter: 25/day. Pro: 50/day. Unlimited: no cap. The bot spaces applications naturally to avoid detection.",
  },
  {
    q: "What is the $2.99 trial?",
    a: "30 applications over 14 days — enough to get real responses back. Credit card required, so upgrading later is one click. Cancel anytime before the 14 days end and you pay nothing more.",
  },
  {
    q: "Does it write personalized cover letters?",
    a: "Yes. GPT-4 generates a unique cover letter for every application based on your resume and the specific job description. Each letter is different.",
  },
  {
    q: "Does LinkedIn allow this?",
    a: "LinkedIn Easy Apply works through our Chrome Extension that runs in your own browser — it's identical to you clicking buttons manually. Your IP, your session, your account. This is the same model used by Simplify.",
  },
  {
    q: "Can I cancel anytime?",
    a: "Yes. Cancel in one click from your account settings. No retention flows, no 'reason for leaving' forms. Instant.",
  },
  {
    q: "What's the difference from Sonara or LazyApply?",
    a: "ResumeAI is 17% cheaper than Sonara ($19.99 vs $23.95) and uses a Chrome Extension model — meaning no server-side credential storage and no proxy fees that competitors pass on to you.",
  },
] as const;

export default function FAQ() {
  const [open, setOpen] = useState<number | null>(null);

  return (
    <section id="faq" className="py-16 sm:py-24 px-4 bg-slate-50 dark:bg-slate-800">
      <div className="max-w-3xl mx-auto">
        <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white text-center mb-10">
          Frequently asked questions
        </h2>

        <div className="space-y-3">
          {FAQ_ITEMS.map((item, i) => (
            <div
              key={i}
              className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden"
            >
              <button
                onClick={() => setOpen(open === i ? null : i)}
                className="w-full text-left px-5 py-4 flex items-center justify-between gap-4 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
              >
                <span className="font-semibold text-slate-900 dark:text-white text-sm sm:text-base">
                  {item.q}
                </span>
                <span
                  className={`text-slate-400 text-xl leading-none flex-shrink-0 transition-transform ${
                    open === i ? "rotate-45" : ""
                  }`}
                >
                  +
                </span>
              </button>
              {open === i ? (
                <div className="px-5 pb-4 text-slate-600 dark:text-slate-400 text-sm leading-relaxed">
                  {item.a}
                </div>
              ) : null}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
