'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { api } from '../../../lib/api';
import { useToast } from '../components/Toast';
import type { Campaign } from '../../../lib/types';

const STATUS_COLORS: Record<string, string> = {
  running:   'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
  paused:    'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30',
  completed: 'bg-gray-500/20 text-gray-400 border border-gray-500/30',
};

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const { showToast } = useToast();

  const load = async () => {
    const data = await api.get<Campaign[]>('/campaigns');
    if (data) setCampaigns(data as Campaign[]);
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const toggleStatus = async (c: Campaign) => {
    const newStatus = c.status === 'running' ? 'paused' : 'running';
    const res = await api.patch(`/campaigns/${c.id}`, { status: newStatus });
    if (res !== null) {
      setCampaigns(prev => prev.map(x => x.id === c.id ? { ...x, status: newStatus } : x));
      showToast(`Campaign ${newStatus === 'running' ? 'resumed' : 'paused'}`, 'success');
    } else {
      showToast('Failed to update campaign', 'error');
    }
  };

  const deleteCampaign = async (id: number) => {
    if (!confirm('Delete this campaign?')) return;
    await api.del(`/campaigns/${id}`);
    setCampaigns(prev => prev.filter(c => c.id !== id));
    showToast('Campaign deleted', 'info');
  };

  return (
    <div className="max-w-[1100px] mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Campaigns</h1>
          <p className="text-gray-500 text-sm mt-0.5">Manage your auto-apply campaigns</p>
        </div>
        <Link
          href="/app/campaigns/new"
          className="bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-500 hover:to-blue-500 text-white font-semibold px-5 py-2.5 rounded-xl text-sm transition-all"
        >
          + New Campaign
        </Link>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-20 bg-[#141414] border border-white/[0.07] rounded-2xl animate-pulse" />
          ))}
        </div>
      ) : campaigns.length === 0 ? (
        <div className="bg-[#141414] border border-white/[0.07] rounded-2xl p-16 text-center">
          <p className="text-5xl mb-4">🚀</p>
          <p className="text-white font-semibold mb-2">No campaigns yet</p>
          <p className="text-gray-500 text-sm mb-6">Create your first campaign to start applying automatically</p>
          <Link
            href="/app/campaigns/new"
            className="bg-gradient-to-r from-violet-600 to-blue-600 text-white font-semibold px-6 py-3 rounded-xl text-sm inline-block"
          >
            Create Campaign
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {campaigns.map(c => (
            <div
              key={c.id}
              className="bg-[#141414] border border-white/[0.07] rounded-2xl px-5 py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-[11px] font-semibold uppercase tracking-wide px-2 py-0.5 rounded-full ${STATUS_COLORS[c.status]}`}>
                    {c.status}
                  </span>
                  <h3 className="text-sm font-semibold text-white truncate">{c.name}</h3>
                </div>
                <p className="text-xs text-gray-500">
                  {c.source} · {c.keywords || 'any keywords'}
                  {c.location ? ` · ${c.location}` : ''}
                </p>
                <p className="text-xs text-gray-600 mt-0.5">
                  {c.applications_sent} applications sent
                </p>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                {c.status !== 'completed' && (
                  <button
                    onClick={() => toggleStatus(c)}
                    className="text-xs font-medium px-3.5 py-1.5 rounded-lg border border-white/[0.07] text-gray-400 hover:text-white hover:bg-white/[0.06] transition-all"
                  >
                    {c.status === 'running' ? '⏸ Pause' : '▶ Resume'}
                  </button>
                )}
                <button
                  onClick={() => deleteCampaign(c.id)}
                  className="text-xs font-medium px-3.5 py-1.5 rounded-lg border border-white/[0.07] text-gray-500 hover:text-red-400 hover:border-red-500/40 transition-all"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
