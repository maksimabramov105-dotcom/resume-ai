"use client";

import { useState } from "react";
import { posthog } from "../providers";

const TELEGRAM_URL = "https://t.me/topbestworkerbot";

const PLANS = [
  {
    id: "trial",
    name: "Trial",
    price: "$2.99",
    period: "for 14 days",
    apps: "30 applications",
    highlight: false,
    features: [
      "30 applications in 14 days",
      "Greenhouse, Lever, Workable",
      "AI cover letter per job",
      "Application tracker",
      "Cancel anytime",
    ],
    cta: "Start $2.99 Trial",
    badge: null,
    href: "/app",
  },
  {
    id: "starter",
    name: "Starter",
    price: "$12.99",
    period: "/ month",
    apps: "25 apps/day",
    highlight: false,
    features: [
      "25 applications/day",
      "All supported platforms",
      "AI cover letter per job",
      "Application tracker",
      "Email support",
    ],
    cta: "Get Starter",
    badge: null,
    href: "/app#pricing",
  },
  {
    id: "pro",
    name: "Pro",
    price: "$19.99",
    period: "/ month",
    apps: "50 apps/day",
    highlight: true,
    features: [
      "50 applications/day",
      "All supported platforms",
      "AI cover letter per job",
      "Priority queue",
      "Application tracker",
      "Priority support",
    ],
    cta: "Get Pro",
    badge: "Most popular",
    href: "/app#pricing",
  },
  {
    id: "unlimited",
    name: "Unlimited",
    price: "$29.99",
    period: "/ month",
    apps: "Unlimited",
    highlight: false,
    features: [
      "Unlimited applications/day",
      "All supported platforms",
      "AI cover letter per job",
      "First in queue",
      "Application tracker",
      "Dedicated support",
    ],
    cta: "Get Unlimited",
    badge: null,
    href: "/app#pricing",
  },
] as const;

export default function Pricing() {
  const [annual, setAnnual] = useState(false);

  function getPrice(base: string): string {
    if (!annual || base === "$2.99") return base;
    const num = parseFloat(base.replace("$", ""));
    return `$${(num * 0.8).toFixed(2)}`;
  }

  return (
    <section id="pricing" className="py-16 sm:py-24 px-4 bg-white dark:bg-slate-900">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-10">
          <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white mb-3">
            Simple, transparent pricing
          </h2>
          <p className="text-slate-500 dark:text-slate-400 text-lg mb-6">
            Start with $2.99 — cancel anytime.
          </p>

          {/* Annual toggle */}
          <div className="inline-flex items-center gap-3 bg-slate-100 dark:bg-slate-800 p-1 rounded-xl">
            <button
              onClick={() => setAnnual(false)}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                !annual
                  ? "bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm"
                  : "text-slate-500 dark:text-slate-400"
              }`}
            >
              Monthly
            </button>
            <button
              onClick={() => setAnnual(true)}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors flex items-center gap-1.5 ${
                annual
                  ? "bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm"
                  : "text-slate-500 dark:text-slate-400"
              }`}
            >
              Annual
              <span className="bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300 text-xs font-bold px-1.5 py-0.5 rounded">
                -20%
              </span>
            </button>
          </div>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {PLANS.map((plan) => (
            <div
              key={plan.id}
              className={`relative rounded-2xl p-6 border flex flex-col ${
                plan.highlight
                  ? "bg-blue-600 text-white border-blue-600 shadow-2xl scale-[1.02]"
                  : "bg-white dark:bg-slate-800 text-slate-900 dark:text-white border-slate-200 dark:border-slate-700 shadow-sm"
              }`}
            >
              {plan.badge !== null ? (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-amber-400 text-slate-900 text-xs font-bold px-3 py-1 rounded-full whitespace-nowrap">
                  {plan.badge}
                </div>
              ) : null}

              <div className="mb-4">
                <div
                  className={`text-xs font-semibold uppercase tracking-wider mb-1 ${
                    plan.highlight ? "text-blue-200" : "text-slate-500 dark:text-slate-400"
                  }`}
                >
                  {plan.name}
                </div>
                <div className="flex items-baseline gap-1">
                  <span className="text-3xl font-extrabold">{getPrice(plan.price)}</span>
                  <span
                    className={`text-sm ${
                      plan.highlight ? "text-blue-200" : "text-slate-500 dark:text-slate-400"
                    }`}
                  >
                    {plan.period}
                  </span>
                </div>
                <div
                  className={`text-sm mt-1 ${
                    plan.highlight ? "text-blue-100" : "text-slate-500 dark:text-slate-400"
                  }`}
                >
                  {plan.apps}
                </div>
              </div>

              <ul className="space-y-2 flex-1 mb-6">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm">
                    <span
                      className={`mt-0.5 text-base leading-none ${
                        plan.highlight ? "text-blue-200" : "text-blue-500"
                      }`}
                    >
                      ✓
                    </span>
                    {f}
                  </li>
                ))}
              </ul>

              <a
                href={plan.href}
                onClick={() => posthog.capture('cta_clicked', { cta: 'pricing', tier: plan.name })}
                className={`block text-center font-semibold py-3 rounded-xl transition-colors ${
                  plan.highlight
                    ? "bg-white text-blue-600 hover:bg-blue-50"
                    : "bg-amber-500 hover:bg-amber-600 text-white"
                }`}
              >
                {plan.cta}
              </a>
              <p className={`text-center text-xs mt-2 ${plan.highlight ? "text-blue-200" : "text-slate-400 dark:text-slate-500"}`}>
                or{" "}
                <a
                  href={TELEGRAM_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline hover:opacity-80"
                >
                  use Telegram bot
                </a>
              </p>
            </div>
          ))}
        </div>

        <p className="text-center text-sm text-slate-400 dark:text-slate-500 mt-8">
          All plans include a 7-day money-back guarantee. No questions asked.
        </p>
      </div>
    </section>
  );
}
