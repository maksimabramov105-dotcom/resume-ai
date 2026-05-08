'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

// ── Types ─────────────────────────────────────────────────────────────────────

interface ApplicationRow {
  id: number;
  campaign_id: number;
  company_name: string;
  vacancy_title: string;
  vacancy_url: string;
  platform: string;
  company_country: string | null;
  status: string;          // system status: sent, viewed, rejected, offer, interview, pending_review
  user_status: string;     // user status: active, archived
  sent_at: string;
  withdrawn_at: string | null;
  // P10 — career-ops fields
  engine: string | null;        // 'api_boards' | 'career_ops'
  match_score: number | null;   // 0-10 composite match score
  cv_pdf_path: string | null;   // absolute server path to generated PDF
}

interface ApiResponse {
  items: ApplicationRow[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
  tab_counts: { active: number; archived: number; all: number; pending_review: number };
}

interface Filters {
  date_from: string;
  date_to: string;
  country: string;
  source: string;
  role_keyword: string;
  status: string;
  free_text: string;
}

const EMPTY_FILTERS: Filters = {
  date_from: '',
  date_to: '',
  country: '',
  source: '',
  role_keyword: '',
  status: '',
  free_text: '',
};

// ── Constants ─────────────────────────────────────────────────────────────────

const SOURCES = ['', 'Adzuna', 'Arbeitnow', 'RemoteOK', 'TheMuse', 'career_ops'];
const APP_STATUSES = ['', 'sent', 'viewed', 'interview', 'offer', 'rejected', 'pending_review'];

const STATUS_STYLES: Record<string, string> = {
  sent:           'bg-gray-500/20 text-gray-400 border border-gray-500/30',
  viewed:         'bg-blue-500/20 text-blue-400 border border-blue-500/30',
  interview:      'bg-violet-500/20 text-violet-400 border border-violet-500/30',
  offer:          'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
  rejected:       'bg-red-500/20 text-red-400 border border-red-500/30',
  pending_review: 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
  queued:         'bg-gray-500/15 text-gray-500 border border-gray-500/20',
};

const STATUS_LABELS: Record<string, string> = {
  sent: 'Sent', viewed: 'Viewed', interview: 'Interview',
  offer: 'Offer', rejected: 'Rejected', pending_review: 'Pending Review',
  queued: 'Queued',
};

// Engine badges
const ENGINE_BADGE: Record<string, { label: string; cls: string }> = {
  career_ops: { label: '🎯 Quality', cls: 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/25' },
  api_boards:  { label: '⚡ Speed',   cls: 'bg-blue-500/15 text-blue-400 border border-blue-500/25' },
};

// ── API helpers ───────────────────────────────────────────────────────────────

function getToken(): string {
  if (typeof window === 'undefined') return '';
  return localStorage.getItem('auth_token') ?? '';
}

async function apiFetch<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const token = getToken();
  const res = await fetch(`/api${path}`, {
    ...opts,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(opts.headers ?? {}),
    },
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail?.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

// ── Toast ─────────────────────────────────────────────────────────────────────

function Toast({ msg, onDone }: { msg: string; onDone: () => void }) {
  useEffect(() => {
    const t = setTimeout(onDone, 3000);
    return () => clearTimeout(t);
  }, [onDone]);
  return (
    <div className="fixed bottom-6 right-6 z-50 bg-[#1a1a1a] border border-white/10 rounded-xl px-5 py-3 text-sm text-white shadow-xl animate-fade-in">
      {msg}
    </div>
  );
}

// ── Confirm dialog ────────────────────────────────────────────────────────────

function ConfirmDialog({
  message,
  onConfirm,
  onCancel,
}: {
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-[#1a1a1a] border border-white/10 rounded-2xl p-6 max-w-sm w-full mx-4 shadow-2xl">
        <p className="text-white text-sm mb-6 leading-relaxed">{message}</p>
        <div className="flex gap-3 justify-end">
          <button
            onClick={onCancel}
            className="px-4 py-2 rounded-lg text-sm text-gray-400 hover:text-white border border-white/10 hover:border-white/20 transition-all"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-red-600/80 hover:bg-red-600 text-white transition-all"
          >
            Withdraw
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ApplicationsPage() {
  const [tab, setTab] = useState<'active' | 'archived' | 'all' | 'pending_review'>('active');
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const [pendingFilters, setPendingFilters] = useState<Filters>(EMPTY_FILTERS);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [page, setPage] = useState(1);

  const [data, setData] = useState<ApiResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<{ id: number; company: string } | null>(null);
  const [actionLoading, setActionLoading] = useState<number | null>(null);

  const prefsDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Load saved prefs on mount ────────────────────────────────────────────
  useEffect(() => {
    apiFetch<Record<string, string>>('/user/view-prefs')
      .then(prefs => {
        if (prefs && typeof prefs === 'object') {
          const savedTab = prefs.tab as typeof tab | undefined;
          if (savedTab && ['active', 'archived', 'all'].includes(savedTab)) {
            setTab(savedTab);
          }
          const savedFiltersOpen = prefs.filtersOpen === 'true';
          setFiltersOpen(savedFiltersOpen);
          const restoredFilters: Partial<Filters> = {};
          for (const key of Object.keys(EMPTY_FILTERS) as (keyof Filters)[]) {
            if (typeof prefs[key] === 'string') {
              restoredFilters[key] = prefs[key];
            }
          }
          if (Object.keys(restoredFilters).length > 0) {
            const merged = { ...EMPTY_FILTERS, ...restoredFilters };
            setFilters(merged);
            setPendingFilters(merged);
          }
        }
      })
      .catch(() => {/* best-effort */});
  }, []);

  // ── Fetch applications ────────────────────────────────────────────────────
  const fetchApps = useCallback(
    async (currentTab: typeof tab, currentFilters: Filters, currentPage: number) => {
      setLoading(true);
      try {
        const params = new URLSearchParams();
        if (currentTab === 'pending_review') {
          params.set('status', 'pending_review');
        } else if (currentTab !== 'all') {
          params.set('user_status', currentTab);
        }
        params.set('page', String(currentPage));
        params.set('per_page', '50');
        if (currentFilters.date_from) params.set('date_from', currentFilters.date_from);
        if (currentFilters.date_to) params.set('date_to', currentFilters.date_to);
        if (currentFilters.country) params.set('country', currentFilters.country);
        if (currentFilters.source) params.set('source', currentFilters.source);
        if (currentFilters.role_keyword) params.set('role_keyword', currentFilters.role_keyword);
        if (currentFilters.status) params.set('status', currentFilters.status);
        if (currentFilters.free_text) params.set('free_text', currentFilters.free_text);
        const result = await apiFetch<ApiResponse>(`/applications?${params.toString()}`);
        setData(result);
      } catch (e) {
        console.error('[applications] fetch error:', e);
        setData(null);
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    fetchApps(tab, filters, page);
  }, [tab, filters, page, fetchApps]);

  // ── Save prefs (debounced, best-effort) ──────────────────────────────────
  const savePrefs = useCallback((newTab: typeof tab, newFilters: Filters, newFiltersOpen: boolean) => {
    if (prefsDebounceRef.current) clearTimeout(prefsDebounceRef.current);
    prefsDebounceRef.current = setTimeout(() => {
      const prefs: Record<string, string> = {
        tab: newTab,
        filtersOpen: String(newFiltersOpen),
        ...Object.fromEntries(
          (Object.entries(newFilters) as [keyof Filters, string][])
            .filter(([, v]) => v !== '')
            .map(([k, v]) => [k, v]),
        ),
      };
      apiFetch('/user/view-prefs', {
        method: 'PUT',
        body: JSON.stringify(prefs),
      }).catch(() => {/* best-effort */});
    }, 800);
  }, []);

  // ── Tab change ────────────────────────────────────────────────────────────
  const handleTabChange = (newTab: typeof tab) => {
    setTab(newTab);
    setPage(1);
    savePrefs(newTab, filters, filtersOpen);
  };

  // ── Career-ops HITL review actions ───────────────────────────────────────
  const handleSubmitReview = async (app: ApplicationRow) => {
    setActionLoading(app.id);
    try {
      await apiFetch(`/applications/${app.id}/review`, {
        method: 'POST',
        body: JSON.stringify({ action: 'submit' }),
      });
      setToast('Application submitted successfully!');
      fetchApps(tab, filters, page);
    } catch (e: any) {
      setToast(e.message ?? 'Error submitting application');
    } finally {
      setActionLoading(null);
    }
  };

  const handleDiscardReview = async (app: ApplicationRow) => {
    setActionLoading(app.id);
    try {
      await apiFetch(`/applications/${app.id}/review`, {
        method: 'POST',
        body: JSON.stringify({ action: 'discard' }),
      });
      setToast('Application discarded');
      fetchApps(tab, filters, page);
    } catch (e: any) {
      setToast(e.message ?? 'Error discarding application');
    } finally {
      setActionLoading(null);
    }
  };

  // ── Apply filters ─────────────────────────────────────────────────────────
  const handleApplyFilters = () => {
    setFilters(pendingFilters);
    setPage(1);
    savePrefs(tab, pendingFilters, filtersOpen);
  };

  // ── Reset filters ─────────────────────────────────────────────────────────
  const handleResetFilters = () => {
    setPendingFilters(EMPTY_FILTERS);
    setFilters(EMPTY_FILTERS);
    setPage(1);
    savePrefs(tab, EMPTY_FILTERS, filtersOpen);
  };

  // ── Actions ───────────────────────────────────────────────────────────────
  const handleWithdraw = (app: ApplicationRow) => {
    setConfirm({ id: app.id, company: app.company_name });
  };

  const confirmWithdraw = async () => {
    if (!confirm) return;
    setActionLoading(confirm.id);
    setConfirm(null);
    try {
      await apiFetch(`/applications/${confirm.id}/withdraw`, { method: 'POST' });
      setToast('Application withdrawn');
      fetchApps(tab, filters, page);
    } catch (e: any) {
      setToast(e.message ?? 'Error withdrawing application');
    } finally {
      setActionLoading(null);
    }
  };

  const handleArchive = async (app: ApplicationRow) => {
    setActionLoading(app.id);
    try {
      await apiFetch(`/applications/${app.id}/archive`, { method: 'POST' });
      setToast('Application archived');
      fetchApps(tab, filters, page);
    } catch (e: any) {
      setToast(e.message ?? 'Error archiving application');
    } finally {
      setActionLoading(null);
    }
  };

  const handleRestore = async (app: ApplicationRow) => {
    setActionLoading(app.id);
    try {
      await apiFetch(`/applications/${app.id}/restore`, { method: 'POST' });
      setToast('Application restored to active');
      fetchApps(tab, filters, page);
    } catch (e: any) {
      setToast(e.message ?? 'Error restoring application');
    } finally {
      setActionLoading(null);
    }
  };

  const formatDate = (s: string) => {
    if (!s) return '—';
    try {
      return new Date(s).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    } catch {
      return s;
    }
  };

  const tabCounts = data?.tab_counts ?? { active: 0, archived: 0, all: 0, pending_review: 0 };
  const items = data?.items ?? [];
  const totalPages = data?.pages ?? 1;

  // ── Empty state messages per tab ─────────────────────────────────────────
  const emptyMessages: Record<string, string> = {
    active: 'No active applications. Once your campaigns run, applications will appear here.',
    archived: 'No archived applications yet. Withdraw or archive applications to move them here.',
    all: 'No applications found. Adjust your filters or start a campaign.',
    pending_review: 'No applications awaiting review. Start a Quality (career-ops) campaign to generate AI-scored PDFs for review.',
  };

  return (
    <div className="max-w-[1200px] mx-auto px-4 sm:px-6 py-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Applications</h1>
        <p className="text-gray-500 text-sm mt-0.5">Track and manage all your job applications</p>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 mb-4 border-b border-white/[0.07] pb-0 flex-wrap">
        {([
          { key: 'active',         label: 'Active' },
          { key: 'pending_review', label: '🎯 Pending Review' },
          { key: 'archived',       label: 'Archived' },
          { key: 'all',            label: 'All' },
        ] as const).map(({ key, label }) => (
          <button
            key={key}
            onClick={() => handleTabChange(key)}
            className={`relative px-4 py-2.5 text-sm font-medium transition-all rounded-t-lg
              ${tab === key
                ? 'text-white border-b-2 border-blue-500 -mb-px bg-white/[0.03]'
                : 'text-gray-500 hover:text-gray-300 hover:bg-white/[0.02]'
              }`}
          >
            {label}
            <span className={`ml-2 text-xs px-1.5 py-0.5 rounded-full font-semibold
              ${tab === key
                ? key === 'pending_review'
                  ? 'bg-emerald-600/30 text-emerald-300'
                  : 'bg-blue-600/30 text-blue-300'
                : 'bg-white/[0.06] text-gray-500'
              }`}>
              {tabCounts[key] ?? 0}
            </span>
          </button>
        ))}
      </div>

      {/* Filter bar */}
      <div className="mb-5 bg-[#141414] border border-white/[0.07] rounded-2xl overflow-hidden">
        <button
          onClick={() => {
            const next = !filtersOpen;
            setFiltersOpen(next);
            savePrefs(tab, filters, next);
          }}
          className="w-full flex items-center justify-between px-5 py-3.5 text-sm text-gray-400 hover:text-white transition-colors"
        >
          <span className="flex items-center gap-2 font-medium">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2a1 1 0 01-.293.707L13 13.414V19a1 1 0 01-.553.894l-4 2A1 1 0 017 21v-7.586L3.293 6.707A1 1 0 013 6V4z" />
            </svg>
            Filters
            {Object.values(filters).some(v => v !== '') && (
              <span className="bg-blue-600 text-white text-[10px] px-1.5 py-0.5 rounded-full font-bold">
                {Object.values(filters).filter(v => v !== '').length}
              </span>
            )}
          </span>
          <svg
            className={`w-4 h-4 transition-transform ${filtersOpen ? 'rotate-180' : ''}`}
            fill="none" stroke="currentColor" viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {filtersOpen && (
          <div className="px-5 pb-5 border-t border-white/[0.07]">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mt-4">
              {/* Date range */}
              <div className="flex gap-2 items-center">
                <div className="flex-1">
                  <label className="text-[11px] text-gray-500 uppercase tracking-wide mb-1 block">From</label>
                  <input
                    type="date"
                    value={pendingFilters.date_from}
                    onChange={e => setPendingFilters(f => ({ ...f, date_from: e.target.value }))}
                    className="w-full bg-[#0d0d0d] border border-white/[0.07] rounded-lg px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-blue-500/50 transition-colors"
                  />
                </div>
                <span className="text-gray-600 mt-5">→</span>
                <div className="flex-1">
                  <label className="text-[11px] text-gray-500 uppercase tracking-wide mb-1 block">To</label>
                  <input
                    type="date"
                    value={pendingFilters.date_to}
                    onChange={e => setPendingFilters(f => ({ ...f, date_to: e.target.value }))}
                    className="w-full bg-[#0d0d0d] border border-white/[0.07] rounded-lg px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-blue-500/50 transition-colors"
                  />
                </div>
              </div>

              {/* Country */}
              <div>
                <label className="text-[11px] text-gray-500 uppercase tracking-wide mb-1 block">Country</label>
                <input
                  type="text"
                  placeholder="e.g. US, DE, UK…"
                  value={pendingFilters.country}
                  onChange={e => setPendingFilters(f => ({ ...f, country: e.target.value }))}
                  className="w-full bg-[#0d0d0d] border border-white/[0.07] rounded-lg px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-blue-500/50 transition-colors"
                />
              </div>

              {/* Source */}
              <div>
                <label className="text-[11px] text-gray-500 uppercase tracking-wide mb-1 block">Source</label>
                <select
                  value={pendingFilters.source}
                  onChange={e => setPendingFilters(f => ({ ...f, source: e.target.value }))}
                  className="w-full bg-[#0d0d0d] border border-white/[0.07] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500/50 transition-colors"
                >
                  {SOURCES.map(s => (
                    <option key={s} value={s}>{s || 'All sources'}</option>
                  ))}
                </select>
              </div>

              {/* Status */}
              <div>
                <label className="text-[11px] text-gray-500 uppercase tracking-wide mb-1 block">Status</label>
                <select
                  value={pendingFilters.status}
                  onChange={e => setPendingFilters(f => ({ ...f, status: e.target.value }))}
                  className="w-full bg-[#0d0d0d] border border-white/[0.07] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500/50 transition-colors"
                >
                  {APP_STATUSES.map(s => (
                    <option key={s} value={s}>{s ? STATUS_LABELS[s] ?? s : 'All statuses'}</option>
                  ))}
                </select>
              </div>

              {/* Role keyword */}
              <div>
                <label className="text-[11px] text-gray-500 uppercase tracking-wide mb-1 block">Role</label>
                <input
                  type="text"
                  placeholder="e.g. Engineer, Manager…"
                  value={pendingFilters.role_keyword}
                  onChange={e => setPendingFilters(f => ({ ...f, role_keyword: e.target.value }))}
                  className="w-full bg-[#0d0d0d] border border-white/[0.07] rounded-lg px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-blue-500/50 transition-colors"
                />
              </div>

              {/* Free text */}
              <div>
                <label className="text-[11px] text-gray-500 uppercase tracking-wide mb-1 block">Free text</label>
                <input
                  type="text"
                  placeholder="Search company or role…"
                  value={pendingFilters.free_text}
                  onChange={e => setPendingFilters(f => ({ ...f, free_text: e.target.value }))}
                  className="w-full bg-[#0d0d0d] border border-white/[0.07] rounded-lg px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-blue-500/50 transition-colors"
                />
              </div>
            </div>

            <div className="flex gap-3 mt-4 justify-end">
              <button
                onClick={handleResetFilters}
                className="px-4 py-2 rounded-lg text-sm text-gray-400 hover:text-white border border-white/[0.07] hover:border-white/20 transition-all"
              >
                Reset
              </button>
              <button
                onClick={handleApplyFilters}
                className="px-5 py-2 rounded-lg text-sm font-semibold bg-blue-600 hover:bg-blue-500 text-white transition-all"
              >
                Apply
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Table */}
      {loading ? (
        <div className="space-y-2">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="h-14 bg-[#141414] border border-white/[0.07] rounded-xl animate-pulse" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="bg-[#141414] border border-white/[0.07] rounded-2xl p-16 text-center">
          <p className="text-gray-400 text-sm font-medium mb-1">No applications found</p>
          <p className="text-gray-600 text-xs max-w-xs mx-auto">{emptyMessages[tab]}</p>
        </div>
      ) : (
        <div className="bg-[#141414] border border-white/[0.07] rounded-2xl overflow-hidden">
          {/* Table header */}
          <div className="hidden lg:grid grid-cols-[2fr_2fr_1fr_1fr_1fr_auto] gap-3 px-5 py-3 border-b border-white/[0.07] text-[11px] font-semibold text-gray-500 uppercase tracking-wide">
            <span>Company</span>
            <span>Role</span>
            <span>Source</span>
            <span>Country</span>
            <span>Status</span>
            <span>Actions</span>
          </div>

          {/* Rows */}
          {items.map(app => (
            <div
              key={app.id}
              className="grid grid-cols-1 lg:grid-cols-[2fr_2fr_1fr_1fr_1fr_auto] gap-2 lg:gap-3 px-5 py-4 border-b border-white/[0.04] last:border-0 hover:bg-white/[0.02] transition-colors items-start lg:items-center"
            >
              {/* Company */}
              <div>
                <span className="text-[10px] text-gray-600 uppercase tracking-wide lg:hidden">Company</span>
                <p className="text-sm font-medium text-white truncate">{app.company_name || '—'}</p>
                <p className="text-[11px] text-gray-600 lg:hidden">{formatDate(app.sent_at)}</p>
              </div>

              {/* Role */}
              <div>
                <span className="text-[10px] text-gray-600 uppercase tracking-wide lg:hidden">Role</span>
                <p className="text-sm text-gray-400 truncate">{app.vacancy_title || '—'}</p>
              </div>

              {/* Source + engine badge */}
              <div className="hidden lg:flex flex-col gap-1">
                <p className="text-sm text-gray-500">{app.platform || '—'}</p>
                {app.engine && ENGINE_BADGE[app.engine] && (
                  <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full w-fit ${ENGINE_BADGE[app.engine].cls}`}>
                    {ENGINE_BADGE[app.engine].label}
                  </span>
                )}
                {app.match_score != null && (
                  <span className="text-[10px] text-gray-600">Match: {app.match_score.toFixed(1)}/10</span>
                )}
              </div>

              {/* Country */}
              <div className="hidden lg:block">
                <p className="text-sm text-gray-500">{app.company_country || '—'}</p>
              </div>

              {/* Status */}
              <div className="flex items-center gap-2">
                <span className={`text-[11px] font-semibold uppercase tracking-wide px-2 py-0.5 rounded-full whitespace-nowrap ${STATUS_STYLES[app.status] ?? STATUS_STYLES.sent}`}>
                  {STATUS_LABELS[app.status] ?? app.status}
                </span>
                <span className="text-[11px] text-gray-600 lg:hidden">{app.platform}</span>
              </div>

              {/* Date (desktop only) */}
              <div className="hidden lg:block">
                <span className="text-xs text-gray-600 whitespace-nowrap">{formatDate(app.sent_at)}</span>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-1.5 flex-wrap lg:flex-nowrap">
                {/* View */}
                {app.vacancy_url ? (
                  <a
                    href={app.vacancy_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-2.5 py-1.5 rounded-lg text-[11px] font-medium bg-white/[0.05] hover:bg-white/[0.09] text-gray-300 hover:text-white transition-all flex items-center gap-1"
                    title="View vacancy"
                  >
                    View
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                        d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                  </a>
                ) : (
                  <span className="px-2.5 py-1.5 rounded-lg text-[11px] text-gray-700 bg-white/[0.02] cursor-not-allowed">View</span>
                )}

                {/* career-ops HITL review actions (pending_review only) */}
                {app.status === 'pending_review' && (
                  <>
                    <button
                      onClick={() => handleSubmitReview(app)}
                      disabled={actionLoading === app.id}
                      className="px-2.5 py-1.5 rounded-lg text-[11px] font-semibold bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 hover:text-emerald-300 transition-all disabled:opacity-40"
                      title="Submit this application"
                    >
                      {actionLoading === app.id ? '…' : '✓ Submit'}
                    </button>
                    <button
                      onClick={() => handleDiscardReview(app)}
                      disabled={actionLoading === app.id}
                      className="px-2.5 py-1.5 rounded-lg text-[11px] font-medium bg-red-600/10 hover:bg-red-600/20 text-red-400 hover:text-red-300 transition-all disabled:opacity-40"
                      title="Discard this application"
                    >
                      {actionLoading === app.id ? '…' : 'Discard'}
                    </button>
                  </>
                )}

                {/* Withdraw (active tab, non-pending_review only) */}
                {app.user_status === 'active' && app.status !== 'pending_review' && (
                  <button
                    onClick={() => handleWithdraw(app)}
                    disabled={actionLoading === app.id}
                    className="px-2.5 py-1.5 rounded-lg text-[11px] font-medium bg-red-600/10 hover:bg-red-600/20 text-red-400 hover:text-red-300 transition-all disabled:opacity-40"
                    title="Withdraw application"
                  >
                    {actionLoading === app.id ? '…' : 'Withdraw'}
                  </button>
                )}

                {/* Archive (active) / Restore (archived) */}
                {app.user_status === 'active' ? (
                  <button
                    onClick={() => handleArchive(app)}
                    disabled={actionLoading === app.id}
                    className="px-2.5 py-1.5 rounded-lg text-[11px] font-medium bg-white/[0.05] hover:bg-white/[0.09] text-gray-400 hover:text-white transition-all disabled:opacity-40"
                    title="Archive application"
                  >
                    {actionLoading === app.id ? '…' : 'Archive'}
                  </button>
                ) : (
                  <button
                    onClick={() => handleRestore(app)}
                    disabled={actionLoading === app.id}
                    className="px-2.5 py-1.5 rounded-lg text-[11px] font-medium bg-emerald-600/10 hover:bg-emerald-600/20 text-emerald-400 hover:text-emerald-300 transition-all disabled:opacity-40"
                    title="Restore to active"
                  >
                    {actionLoading === app.id ? '…' : 'Restore'}
                  </button>
                )}

                {/* Message Company stub */}
                <button
                  onClick={() => setToast('Coming soon — message company feature is in development')}
                  className="px-2.5 py-1.5 rounded-lg text-[11px] font-medium bg-white/[0.03] text-gray-600 cursor-not-allowed hover:bg-white/[0.05] transition-all"
                  title="Message company (coming soon)"
                >
                  💬
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {!loading && totalPages > 1 && (
        <div className="flex items-center justify-center gap-4 mt-5">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="px-4 py-2 rounded-lg text-sm text-gray-400 hover:text-white border border-white/[0.07] hover:border-white/20 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
          >
            ← Prev
          </button>
          <span className="text-sm text-gray-500">
            Page <span className="text-white font-medium">{page}</span> of{' '}
            <span className="text-white font-medium">{totalPages}</span>
          </span>
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="px-4 py-2 rounded-lg text-sm text-gray-400 hover:text-white border border-white/[0.07] hover:border-white/20 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
          >
            Next →
          </button>
        </div>
      )}

      {!loading && data && (
        <p className="text-xs text-gray-600 mt-3 text-right">
          {data.total} application{data.total !== 1 ? 's' : ''} total
        </p>
      )}

      {/* Confirm withdraw dialog */}
      {confirm && (
        <ConfirmDialog
          message={`Withdraw your application to ${confirm.company}? This will move it to Archived and mark it as withdrawn.`}
          onConfirm={confirmWithdraw}
          onCancel={() => setConfirm(null)}
        />
      )}

      {/* Toast */}
      {toast && <Toast msg={toast} onDone={() => setToast(null)} />}
    </div>
  );
}
