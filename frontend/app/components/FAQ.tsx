"use client";

import { useState } from "react";

const FAQ_ITEMS = [
  {
    q: "Is this against LinkedIn's terms of service?",
    a: "LinkedIn Easy Apply is designed for fast application — we fill the forms in your own browser using your own account. We don't scrape, don't store your LinkedIn credentials, and don't bypass any security. Thousands of people use autofill tools like this every day.",
  },
  {
    q: "Will employers know I used a bot?",
    a: "No. Applications are sent from your own IP, your own browser session, with your real resume. To employers, it looks exactly like a manual application — because technically it is one, just faster.",
  },
  {
    q: "What job boards do you support?",
    a: "Currently: Greenhouse, Lever, Workable, Ashby, SmartRecruiters, and LinkedIn Easy Apply. We're adding Indeed Apply and Glassdoor in May 2025.",
  },
  {
    q: "What happens to my resume and personal data?",
    a: "Your resume is stored encrypted on our servers (AES-256). We never sell or share your data. You can delete your account and all data at any time with /delete in the Telegram bot.",
  },
  {
    q: "Can I try before paying?",
    a: "Yes. Free tier: 10 applications/day, no credit card needed. Or start the $2.99 trial for 30 applications over 14 days — the fastest way to see if it works for you.",
  },
  {
    q: "What if I get no responses?",
    a: "Volume helps — most users see their first response within 20-50 applications. We also optimize your resume for ATS keywords before applying. If you're not getting responses, message @yourtelegramhandle and we'll review your resume personally.",
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
