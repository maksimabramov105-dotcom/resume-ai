'use client';

import { useCallback, useEffect, useState } from 'react';
import { api } from '../../../../lib/api';
import { useToast } from '../../components/Toast';

// ── Types ─────────────────────────────────────────────────────────────────────

interface ReferralStats {
  code: string;
  link: string;
  invited: number;
  converted: number;
  pending: number;
}

// ── Loading skeleton ──────────────────────────────────────────────────────────

function Skeleton({ className }: { className?: string }) {
  return (
    <div className={`animate-pulse bg-white/[0.05] rounded-xl ${className ?? ''}`} />
  );
}

function ReferralSkeleton() {
  return (
    <div className="space-y-5">
      <Skeleton className="h-14 w-full" />
      <div className="grid grid-cols-3 gap-3">
        <Skeleton className="h-20" />
        <Skeleton className="h-20" />
        <Skeleton className="h-20" />
      </div>
      <Skeleton className="h-40 w-full" />
    </div>
  );
}

// ── Steps ─────────────────────────────────────────────────────────────────────

const HOW_IT_WORKS = [
  {
    step: 1,
    icon: '🔗',
    title: 'Share your link',
    description: 'Send your unique referral link to friends who are job searching.',
  },
  {
    step: 2,
    icon: '👤',
    title: 'Friend signs up',
    description: 'When they create an account using your link, the referral is recorded.',
  },
  {
    step: 3,
    icon: '🎁',
    title: 'Both get 1 free month',
    description: 'You and your friend each receive one month of Pro access — automatically.',
  },
];

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ReferPage() {
  const { showToast } = useToast();

  const [stats, setStats] = useState<ReferralStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<ReferralStats>('/referral/stats');
      if (data) {
        setStats(data);
      } else {
        setError('Could not load your referral stats. Please try again.');
      }
    } catch (e: any) {
      setError(e?.message ?? 'Something went wrong. Please try again later.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchStats(); }, [fetchStats]);

  const copyLink = async () => {
    if (!stats?.link) return;
    try {
      await navigator.clipboard.writeText(stats.link);
      showToast('Referral link copied!', 'success');
    } catch {
      showToast('Could not copy — please copy manually', 'error');
    }
  };

  const shareViaTelegram = () => {
    if (!stats?.link) return;
    const text = encodeURIComponent(
      `Join me on AutoApply — the AI that applies to jobs for you. Use my link and we both get 1 free month! ${stats.link}`
    );
    window.open(`https://t.me/share/url?url=${encodeURIComponent(stats.link)}&text=${text}`, '_blank');
  };

  return (
    <div className="max-w-[720px] mx-auto px-4 sm:px-6 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Referral Program</h1>
        <p className="text-gray-500 text-sm mt-1">Invite friends and earn free Pro months together</p>
      </div>

      {/* Loading */}
      {loading && <ReferralSkeleton />}

      {/* Error */}
      {!loading && error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-2xl p-8 text-center space-y-4">
          <div className="text-3xl">😔</div>
          <p className="text-red-300 text-sm font-medium">{error}</p>
          <button
            onClick={fetchStats}
            className="px-5 py-2 rounded-xl text-sm font-semibold bg-white/[0.07] hover:bg-white/[0.1] text-white transition-all border border-white/[0.07]"
          >
            Try again
          </button>
        </div>
      )}

      {/* Content */}
      {!loading && !error && stats && (
        <div className="space-y-6">

          {/* Referral code badge */}
          <div className="bg-gradient-to-r from-violet-600/20 to-blue-600/20 border border-violet-500/25 rounded-2xl px-6 py-5 flex items-center justify-between gap-4">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-widest text-gray-500 mb-1">Your referral code</p>
              <p className="text-2xl font-bold text-white tracking-wider font-mono">{stats.code}</p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-violet-600 to-blue-600 flex items-center justify-center flex-shrink-0 text-2xl">
              🎁
            </div>
          </div>

          {/* Referral link input */}
          <div className="bg-[#141414] border border-white/[0.07] rounded-2xl p-5 space-y-3">
            <p className="text-white text-sm font-semibold">Your referral link</p>
            <div className="flex gap-2">
              <div className="flex-1 bg-[#0a0a0a] border border-white/[0.07] rounded-xl px-4 py-2.5 text-sm text-gray-400 font-mono truncate select-all">
                {stats.link}
              </div>
              <button
                onClick={copyLink}
                className="flex-shrink-0 px-4 py-2.5 rounded-xl text-sm font-semibold bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-500 hover:to-blue-500 text-white transition-all flex items-center gap-2 shadow-lg shadow-violet-900/20"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                Copy
              </button>
            </div>

            {/* Share buttons */}
            <div className="flex gap-2 pt-1">
              <button
                onClick={copyLink}
                className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium border border-white/[0.07] text-gray-400 hover:text-white hover:border-white/[0.15] bg-white/[0.03] hover:bg-white/[0.06] transition-all"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                </svg>
                Copy link
              </button>
              <button
                onClick={shareViaTelegram}
                className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium bg-[#2AABEE]/10 hover:bg-[#2AABEE]/20 text-[#2AABEE] border border-[#2AABEE]/20 hover:border-[#2AABEE]/35 transition-all"
              >
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.894 8.221l-1.97 9.28c-.145.658-.537.818-1.084.508l-3-2.21-1.447 1.394c-.16.16-.295.295-.605.295l.213-3.053 5.56-5.023c.242-.213-.054-.333-.373-.12L7.844 14.49l-2.95-.924c-.64-.203-.654-.64.136-.954l11.52-4.44c.535-.194 1.003.131.344 2.049z"/>
                </svg>
                Share via Telegram
              </button>
            </div>
          </div>

          {/* Stats row */}
          <div className="grid grid-cols-3 gap-3">
            {[
              {
                label: 'Invited',
                value: stats.invited,
                color: 'text-blue-400',
                bg: 'bg-blue-500/10 border-blue-500/20',
                icon: '👥',
              },
              {
                label: 'Converted',
                value: stats.converted,
                color: 'text-emerald-400',
                bg: 'bg-emerald-500/10 border-emerald-500/20',
                icon: '✅',
              },
              {
                label: 'Pending',
                value: stats.pending,
                color: 'text-amber-400',
                bg: 'bg-amber-500/10 border-amber-500/20',
                icon: '⏳',
              },
            ].map(({ label, value, color, bg, icon }) => (
              <div
                key={label}
                className={`${bg} border rounded-2xl p-4 text-center`}
              >
                <div className="text-xl mb-1">{icon}</div>
                <p className={`text-2xl font-bold ${color}`}>{value}</p>
                <p className="text-gray-500 text-xs mt-0.5 font-medium">{label}</p>
              </div>
            ))}
          </div>

          {/* Rewards note */}
          {stats.converted > 0 && (
            <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-2xl px-5 py-3.5 flex items-center gap-3">
              <span className="text-xl">🎉</span>
              <p className="text-emerald-300 text-sm">
                You have earned{' '}
                <span className="font-bold">{stats.converted} free month{stats.converted !== 1 ? 's' : ''}</span>
                {' '}of Pro access — thank you for spreading the word!
              </p>
            </div>
          )}

          {/* How it works */}
          <div className="bg-[#141414] border border-white/[0.07] rounded-2xl p-5">
            <h2 className="text-white font-semibold text-sm mb-5">How it works</h2>
            <div className="space-y-0">
              {HOW_IT_WORKS.map((item, idx) => (
                <div key={item.step} className="flex gap-4">
                  {/* Step connector */}
                  <div className="flex flex-col items-center">
                    <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-600/30 to-blue-600/30 border border-violet-500/25 flex items-center justify-center flex-shrink-0 text-base">
                      {item.icon}
                    </div>
                    {idx < HOW_IT_WORKS.length - 1 && (
                      <div className="w-px flex-1 bg-white/[0.05] my-2" />
                    )}
                  </div>

                  {/* Content */}
                  <div className={`pb-5 ${idx === HOW_IT_WORKS.length - 1 ? 'pb-0' : ''}`}>
                    <p className="text-white text-sm font-semibold leading-tight">{item.title}</p>
                    <p className="text-gray-500 text-xs mt-1 leading-relaxed">{item.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Terms note */}
          <p className="text-gray-700 text-xs text-center">
            Free months are credited after your friend's first paid subscription. One reward per unique signup.
          </p>
        </div>
      )}
    </div>
  );
}
