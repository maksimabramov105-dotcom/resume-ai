'use client';

import { useEffect, useState } from 'react';
import { api } from '../../../lib/api';
import { useToast } from '../components/Toast';
import type { TrackerCard } from '../../../lib/types';

const COLUMNS: { key: TrackerCard['status']; label: string; color: string }[] = [
  { key: 'wishlist',  label: 'Wishlist',   color: 'text-gray-400' },
  { key: 'applied',   label: 'Applied',    color: 'text-blue-400' },
  { key: 'phone',     label: 'Phone',      color: 'text-yellow-400' },
  { key: 'interview', label: 'Interview',  color: 'text-violet-400' },
  { key: 'offer',     label: 'Offer',      color: 'text-emerald-400' },
  { key: 'rejected',  label: 'Rejected',   color: 'text-red-400' },
];

function AddCardModal({
  onClose,
  onAdd,
}: {
  onClose: () => void;
  onAdd: (card: Partial<TrackerCard>) => void;
}) {
  const [company, setCompany] = useState('');
  const [position, setPosition] = useState('');
  const [status, setStatus] = useState<TrackerCard['status']>('wishlist');
  const [url, setUrl] = useState('');
  const [notes, setNotes] = useState('');

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-[#1a1a1a] border border-white/[0.1] rounded-2xl p-6 w-full max-w-md">
        <h3 className="text-base font-semibold text-white mb-5">Add Job</h3>
        <div className="space-y-3">
          <input value={company} onChange={e => setCompany(e.target.value)} placeholder="Company"
            className="w-full bg-[#0a0a0a] border border-white/[0.07] rounded-xl px-4 py-2.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-violet-500/50" />
          <input value={position} onChange={e => setPosition(e.target.value)} placeholder="Position"
            className="w-full bg-[#0a0a0a] border border-white/[0.07] rounded-xl px-4 py-2.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-violet-500/50" />
          <select value={status} onChange={e => setStatus(e.target.value as TrackerCard['status'])}
            className="w-full bg-[#0a0a0a] border border-white/[0.07] rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-violet-500/50">
            {COLUMNS.map(c => <option key={c.key} value={c.key}>{c.label}</option>)}
          </select>
          <input value={url} onChange={e => setUrl(e.target.value)} placeholder="Job URL (optional)"
            className="w-full bg-[#0a0a0a] border border-white/[0.07] rounded-xl px-4 py-2.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-violet-500/50" />
          <textarea value={notes} onChange={e => setNotes(e.target.value)} placeholder="Notes…" rows={3}
            className="w-full bg-[#0a0a0a] border border-white/[0.07] rounded-xl px-4 py-2.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-violet-500/50 resize-none" />
        </div>
        <div className="flex gap-3 mt-5">
          <button onClick={onClose}
            className="flex-1 border border-white/[0.07] text-gray-400 hover:text-white py-2.5 rounded-xl text-sm font-medium transition-all">
            Cancel
          </button>
          <button
            onClick={() => { if (company && position) onAdd({ company, position, status, url, notes }); }}
            className="flex-1 bg-gradient-to-r from-violet-600 to-blue-600 text-white font-semibold py-2.5 rounded-xl text-sm">
            Add
          </button>
        </div>
      </div>
    </div>
  );
}

export default function TrackerPage() {
  const [cards, setCards] = useState<TrackerCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const { showToast } = useToast();

  useEffect(() => {
    api.get<TrackerCard[]>('/tracker').then(data => {
      if (Array.isArray(data)) setCards(data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  async function addCard(partial: Partial<TrackerCard>) {
    const res = await api.post<TrackerCard>('/tracker', partial);
    if (res?.id) {
      setCards(prev => [...prev, res as TrackerCard]);
      setShowAdd(false);
      showToast('Job added to tracker', 'success');
    } else {
      showToast('Failed to add job', 'error');
    }
  }

  async function moveCard(id: number, newStatus: TrackerCard['status']) {
    await api.patch(`/tracker/${id}`, { status: newStatus });
    setCards(prev => prev.map(c => c.id === id ? { ...c, status: newStatus } : c));
  }

  async function deleteCard(id: number) {
    await api.del(`/tracker/${id}`);
    setCards(prev => prev.filter(c => c.id !== id));
    showToast('Removed from tracker', 'info');
  }

  return (
    <div className="px-6 py-8">
      <div className="flex items-center justify-between mb-8 max-w-[1400px] mx-auto">
        <div>
          <h1 className="text-2xl font-bold text-white">Job Tracker</h1>
          <p className="text-gray-500 text-sm mt-0.5">Track your job search progress</p>
        </div>
        <button
          onClick={() => setShowAdd(true)}
          className="bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-500 hover:to-blue-500 text-white font-semibold px-5 py-2.5 rounded-xl text-sm transition-all"
        >
          + Add Job
        </button>
      </div>

      {/* Kanban board */}
      <div className="overflow-x-auto pb-4">
        <div className="flex gap-4 min-w-[900px] max-w-[1400px] mx-auto">
          {COLUMNS.map(col => {
            const colCards = cards.filter(c => c.status === col.key);
            return (
              <div key={col.key} className="flex-1 min-w-[180px]">
                <div className="flex items-center gap-2 mb-3 px-1">
                  <h3 className={`text-xs font-semibold uppercase tracking-wide ${col.color}`}>{col.label}</h3>
                  <span className="text-xs text-gray-600 bg-white/[0.05] px-1.5 py-0.5 rounded-full">{colCards.length}</span>
                </div>

                <div className="space-y-2 min-h-[200px]">
                  {loading ? (
                    <div className="h-20 bg-[#141414] border border-white/[0.07] rounded-xl animate-pulse" />
                  ) : colCards.length === 0 ? (
                    <div className="h-20 border border-dashed border-white/[0.05] rounded-xl flex items-center justify-center">
                      <span className="text-xs text-gray-700">Empty</span>
                    </div>
                  ) : (
                    colCards.map(card => (
                      <div
                        key={card.id}
                        className="bg-[#141414] border border-white/[0.07] hover:border-violet-500/30 rounded-xl p-3.5 group transition-all"
                      >
                        <p className="text-sm font-medium text-white mb-0.5 truncate">{card.company}</p>
                        <p className="text-xs text-gray-500 truncate">{card.position}</p>
                        {card.notes && (
                          <p className="text-xs text-gray-600 mt-1.5 line-clamp-2">{card.notes}</p>
                        )}
                        {card.url && (
                          <a
                            href={card.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[11px] text-violet-400 hover:text-violet-300 mt-1.5 block transition-colors"
                            onClick={e => e.stopPropagation()}
                          >
                            Open job →
                          </a>
                        )}

                        {/* Move buttons */}
                        <div className="flex gap-1 mt-2.5 opacity-0 group-hover:opacity-100 transition-opacity flex-wrap">
                          {COLUMNS.filter(c => c.key !== col.key).slice(0, 3).map(target => (
                            <button
                              key={target.key}
                              onClick={() => moveCard(card.id, target.key)}
                              className="text-[10px] px-2 py-0.5 rounded-md border border-white/[0.07] text-gray-600 hover:text-gray-300 transition-colors"
                            >
                              → {target.label}
                            </button>
                          ))}
                          <button
                            onClick={() => deleteCard(card.id)}
                            className="text-[10px] px-2 py-0.5 rounded-md border border-red-500/20 text-red-500/60 hover:text-red-400 transition-colors"
                          >
                            ✕
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {showAdd && <AddCardModal onClose={() => setShowAdd(false)} onAdd={addCard} />}
    </div>
  );
}
