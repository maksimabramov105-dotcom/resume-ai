'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { api } from '../../../lib/api';
import { useAuth } from '../components/AuthContext';
import type { Campaign, Stats } from '../../../lib/types';

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="bg-[#141414] border border-white/[0.07] rounded-2xl p-5">
      <p className="text-xs text-gray-500 font-medium uppercase tracking-wide mb-1">{label}</p>
      <p className="text-3xl font-bold text-white">{value}</p>
      {sub && <p className="text-xs text-gray-600 mt-0.5">{sub}</p>}
    </div>
  );
}

const STATUS_COLORS: Record<string, string> = {
  running:   'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
  paused:    'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30',
  completed: 'bg-gray-500/20 text-gray-400 border border-gray-500/30',
};

export default function DashboardPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState<Stats | null>(null);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [emailUnverified, setEmailUnverified] = useState(false);

  useEffect(() => {
    Promise.all([
      api.get<any>('/dashboard'),
      api.get<any[]>('/campaigns'),
    ]).then(([s, c]) => {
      try {
        // Detect email-not-verified 403
        if (s?.detail === 'email_not_verified') {
          setEmailUnverified(true);
        } else if (s && !s.detail) {
          setStats({
            total_applications: s.applications_total ?? s.total_applications ?? 0,
            applications_today: s.applications_today ?? 0,
            active_campaigns: s.active_campaigns ?? 0,
            interviews: s.by_status?.interview ?? s.by_status?.interviewing ?? s.interviews ?? 0,
            response_rate: s.response_rate ?? 0,
          });
        }
        if (Array.isArray(c)) {
          const normalized: Campaign[] = c.map((r: any) => ({
            id: r.id,
            name: r.job_title ?? r.name ?? '',
            status: r.status === 'active' ? 'running' : (r.status ?? 'paused'),
            source: Array.isArray(r.platforms)
              ? (r.platforms[0] ?? 'all')
              : (r.platforms ?? r.source ?? 'all'),
            keywords: r.keywords ?? r.job_title ?? '',
            location: r.location ?? '',
            applications_sent: r.applications_sent ?? 0,
            created_at: r.created_at ?? '',
            updated_at: r.last_run ?? r.updated_at ?? r.created_at ?? '',
          }));
          setCampaigns(normalized.slice(0, 3));
        }
      } catch (e) {
        console.error('[dashboard] normalization error:', e);
      }
      setLoading(false);
    }).catch(err => {
      console.error('[dashboard] fetch error:', err);
      setLoading(false);
    });
  }, []);

  const usedPct = user
    ? Math.min(100, Math.round((user.applications_count / (user.applications_limit || 1)) * 100))
    : 0;

  return (
    <div className="max-w-[1100px] mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-gray-500 text-sm mt-0.5">
            Welcome back{user?.email ? `, ${user.email.split('@')[0]}` : ''} 👋
          </p>
        </div>
        <Link
          href="/app/campaigns/new"
          className="bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-500 hover:to-blue-500 text-white font-semibold px-5 py-2.5 rounded-xl text-sm transition-all"
        >
          + New Campaign
        </Link>
      </div>

      {/* Email verification banner */}
      {emailUnverified && (
        <div className="mb-6 bg-yellow-500/10 border border-yellow-500/30 rounded-2xl px-5 py-4 flex items-start gap-3">
          <span className="text-yellow-400 text-lg shrink-0">⚠️</span>
          <div>
            <p className="text-sm font-semibold text-yellow-300">Please verify your email</p>
            <p className="text-xs text-yellow-500 mt-0.5">
              Check your inbox for a verification link. Stats will appear once your email is confirmed.
            </p>
          </div>
        </div>
      )}

      {/* Stats grid */}
      {loading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-[#141414] border border-white/[0.07] rounded-2xl p-5 animate-pulse h-24" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <StatCard label="Total Applied" value={stats?.total_applications ?? 0} />
          <StatCard label="Today" value={stats?.applications_today ?? 0} />
          <StatCard label="Active Campaigns" value={stats?.active_campaigns ?? 0} />
          <StatCard label="Interviews" value={stats?.interviews ?? 0} sub={stats ? `${stats.response_rate}% response rate` : ''} />
        </div>
      )}

      {/* Usage bar */}
      {user && (
        <div className="bg-[#141414] border border-white/[0.07] rounded-2xl p-5 mb-8">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-400 font-medium">Monthly Usage</span>
            <span className="text-sm text-gray-500">
              {user.applications_count} / {user.applications_limit === 999999 ? '∞' : user.applications_limit}
            </span>
          </div>
          <div className="h-2 bg-[#1a1a1a] rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-violet-600 to-blue-600 rounded-full transition-all"
              style={{ width: `${usedPct}%` }}
            />
          </div>
          {usedPct >= 90 && (
            <p className="text-xs text-yellow-400 mt-2">
              ⚠️ Almost at limit —{' '}
              <Link href="/app/pricing" className="underline">upgrade your plan</Link>
            </p>
          )}
        </div>
      )}

      {/* Recent campaigns */}
      <div className="bg-[#141414] border border-white/[0.07] rounded-2xl p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-semibold text-white">Recent Campaigns</h2>
          <Link href="/app/campaigns" className="text-xs text-gray-500 hover:text-gray-300 transition-colors">
            View all →
          </Link>
        </div>

        {loading ? (
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-14 bg-[#1a1a1a] rounded-xl animate-pulse" />
            ))}
          </div>
        ) : campaigns.length === 0 ? (
          <div className="text-center py-10">
            <p className="text-gray-600 text-sm mb-4">No campaigns yet</p>
            <Link
              href="/app/campaigns/new"
              className="bg-gradient-to-r from-violet-600 to-blue-600 text-white font-semibold px-5 py-2.5 rounded-xl text-sm"
            >
              Create your first campaign
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {campaigns.map(c => (
              <div key={c.id} className="flex items-center justify-between bg-[#1a1a1a] rounded-xl px-4 py-3">
                <div>
                  <p className="text-sm font-medium text-white">{c.name}</p>
                  <p className="text-xs text-gray-600 mt-0.5">
                    {c.source} · {c.keywords || 'any keywords'}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-sm text-gray-400 font-medium">{c.applications_sent}</span>
                  <span className={`text-[11px] font-semibold uppercase tracking-wide px-2 py-0.5 rounded-full ${STATUS_COLORS[c.status]}`}>
                    {c.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
