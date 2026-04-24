'use client';

import { useEffect, useState } from 'react';
import { api } from '../../../lib/api';
import type { Application } from '../../../lib/types';

const STATUS_STYLES: Record<string, string> = {
  sent:      'bg-gray-500/20 text-gray-400 border border-gray-500/30',
  viewed:    'bg-blue-500/20 text-blue-400 border border-blue-500/30',
  interview: 'bg-violet-500/20 text-violet-400 border border-violet-500/30',
  offer:     'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
  rejected:  'bg-red-500/20 text-red-400 border border-red-500/30',
};

const STATUS_LABELS: Record<string, string> = {
  sent: 'Sent', viewed: 'Viewed', interview: 'Interview', offer: 'Offer', rejected: 'Rejected',
};

const ALL_STATUSES = ['all', 'sent', 'viewed', 'interview', 'offer', 'rejected'];

export default function ApplicationsPage() {
  const [apps, setApps] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');

  useEffect(() => {
    api.get<Application[]>('/applications').then(data => {
      if (data) setApps(data as Application[]);
      setLoading(false);
    });
  }, []);

  const filtered = apps.filter(a => {
    const matchStatus = filter === 'all' || a.status === filter;
    const matchSearch = !search ||
      a.company.toLowerCase().includes(search.toLowerCase()) ||
      a.position.toLowerCase().includes(search.toLowerCase());
    return matchStatus && matchSearch;
  });

  const formatDate = (s: string) => new Date(s).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

  return (
    <div className="max-w-[1100px] mx-auto px-6 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Applications</h1>
        <p className="text-gray-500 text-sm mt-0.5">Track all your job applications</p>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search company or position…"
          className="flex-1 bg-[#141414] border border-white/[0.07] rounded-xl px-4 py-2.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-violet-500/50 transition-colors"
        />
        <div className="flex gap-1.5 flex-wrap">
          {ALL_STATUSES.map(s => (
            <button
              key={s}
              onClick={() => setFilter(s)}
              className={`px-3 py-2 rounded-lg text-xs font-medium capitalize transition-all
                ${filter === s
                  ? 'bg-gradient-to-r from-violet-600 to-blue-600 text-white'
                  : 'bg-[#141414] border border-white/[0.07] text-gray-500 hover:text-gray-300'
                }`}
            >
              {s === 'all' ? 'All' : STATUS_LABELS[s]}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div className="space-y-2">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="h-14 bg-[#141414] border border-white/[0.07] rounded-xl animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-[#141414] border border-white/[0.07] rounded-2xl p-16 text-center">
          <p className="text-gray-500 text-sm">No applications found</p>
        </div>
      ) : (
        <div className="bg-[#141414] border border-white/[0.07] rounded-2xl overflow-hidden">
          {/* Header */}
          <div className="grid grid-cols-[1fr_1fr_auto_auto] gap-4 px-5 py-3 border-b border-white/[0.07] text-xs font-medium text-gray-500 uppercase tracking-wide">
            <span>Company</span>
            <span>Position</span>
            <span>Date</span>
            <span>Status</span>
          </div>
          {/* Rows */}
          {filtered.map(a => (
            <div
              key={a.id}
              className="grid grid-cols-[1fr_1fr_auto_auto] gap-4 px-5 py-3.5 border-b border-white/[0.04] last:border-0 hover:bg-white/[0.02] transition-colors items-center"
            >
              <a
                href={a.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm font-medium text-white hover:text-violet-400 transition-colors truncate"
              >
                {a.company}
              </a>
              <span className="text-sm text-gray-400 truncate">{a.position}</span>
              <span className="text-xs text-gray-600 whitespace-nowrap">{formatDate(a.applied_at)}</span>
              <span className={`text-[11px] font-semibold uppercase tracking-wide px-2 py-0.5 rounded-full whitespace-nowrap ${STATUS_STYLES[a.status]}`}>
                {STATUS_LABELS[a.status]}
              </span>
            </div>
          ))}
        </div>
      )}

      {!loading && (
        <p className="text-xs text-gray-600 mt-3 text-right">
          {filtered.length} of {apps.length} applications
        </p>
      )}
    </div>
  );
}
