"use client";

import { useState, useEffect } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

const FALLBACK = {
  resumes_created: 247,
  cover_letters: 143,
  applications_sent: 74,
  total_users: 74,
};

type Stats = typeof FALLBACK;

const STAT_LABELS: { key: keyof Stats; label: string }[] = [
  { key: "total_users", label: "job seekers" },
  { key: "resumes_created", label: "resumes optimized" },
  { key: "applications_sent", label: "applications sent" },
];

function formatNum(n: number): string {
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n);
}

export default function StatsBar() {
  const [stats, setStats] = useState<Stats>(FALLBACK);

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_URL}/api/stats`, {
      signal: controller.signal,
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data) setStats({ ...FALLBACK, ...data });
      })
      .catch(() => {});
    return () => controller.abort();
  }, []);

  return (
    <div className="flex flex-wrap justify-center gap-6 sm:gap-10">
      {STAT_LABELS.map(({ key, label }) => (
        <div key={key} className="text-center">
          <div className="text-2xl sm:text-3xl font-extrabold text-blue-600 dark:text-blue-400">
            {formatNum(stats[key])}+
          </div>
          <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{label}</div>
        </div>
      ))}
    </div>
  );
}
