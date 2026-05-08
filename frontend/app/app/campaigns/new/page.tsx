'use client';

import { useState, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '../../../../lib/api';
import { useToast } from '../../components/Toast';

const SOURCES = [
  { value: 'all',       label: 'All Sources' },
  { value: 'adzuna',   label: 'Adzuna' },
  { value: 'linkedin', label: 'LinkedIn' },
  { value: 'themuse',  label: 'The Muse' },
  { value: 'remoteok', label: 'Remote OK' },
  { value: 'arbeitnow',label: 'Arbeitnow' },
];

const SALARY_OPTS = ['Any', '50000', '80000', '100000', '150000', '200000+'];

export default function NewCampaignPage() {
  const router = useRouter();
  const { showToast } = useToast();
  const [loading, setLoading] = useState(false);

  const [form, setForm] = useState({
    name: '',
    source: 'all',
    keywords: '',
    location: '',
    salary_from: '',
    experience: '',
    cover_letter: true,
    daily_limit: 50,
    engine: 'api_boards' as 'api_boards' | 'career_ops',
  });

  const set = (key: string, val: unknown) => setForm(f => ({ ...f, [key]: val }));

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!form.name || !form.keywords) {
      showToast('Campaign name and keywords are required', 'error');
      return;
    }
    setLoading(true);
    const res = await api.post<{ id?: number; detail?: string }>('/campaigns', form);
    setLoading(false);
    if (res?.id) {
      showToast('Campaign created!', 'success');
      router.push('/app/campaigns');
    } else {
      showToast(res?.detail ?? 'Failed to create campaign', 'error');
    }
  }

  return (
    <div className="max-w-[680px] mx-auto px-6 py-8">
      <div className="mb-8">
        <button
          onClick={() => router.back()}
          className="text-gray-500 hover:text-gray-300 text-sm mb-4 flex items-center gap-1 transition-colors"
        >
          ← Back
        </button>
        <h1 className="text-2xl font-bold text-white">New Campaign</h1>
        <p className="text-gray-500 text-sm mt-0.5">Set up automated job applications</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Campaign name */}
        <div className="bg-[#141414] border border-white/[0.07] rounded-2xl p-5">
          <label className="block text-xs font-medium text-gray-400 mb-2">Campaign Name</label>
          <input
            type="text"
            value={form.name}
            onChange={e => set('name', e.target.value)}
            placeholder="e.g. Senior Frontend Engineer"
            className="w-full bg-[#1a1a1a] border border-white/[0.07] rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-violet-500/50 transition-colors"
          />
        </div>

        {/* Engine selector */}
        <div className="bg-[#141414] border border-white/[0.07] rounded-2xl p-5">
          <label className="block text-xs font-medium text-gray-400 mb-1">Application Engine</label>
          <p className="text-xs text-gray-600 mb-3">Choose your quality/speed tradeoff</p>
          <div className="grid grid-cols-2 gap-3">
            {/* Speed */}
            <button
              type="button"
              onClick={() => set('engine', 'api_boards')}
              className={`relative rounded-xl border p-4 text-left transition-all ${
                form.engine === 'api_boards'
                  ? 'border-violet-500/50 bg-violet-500/10'
                  : 'border-white/[0.07] hover:border-white/20'
              }`}
            >
              <div className="text-sm font-semibold text-white mb-1">⚡ Speed</div>
              <div className="text-xs text-gray-400 leading-relaxed">
                Up to 50 applications/day via Adzuna, RemoteOK, Arbeitnow &amp; The Muse.
                Instant — no review needed.
              </div>
              {form.engine === 'api_boards' && (
                <span className="absolute top-2 right-2 text-violet-400 text-xs font-medium">Selected</span>
              )}
            </button>

            {/* Quality */}
            <button
              type="button"
              onClick={() => set('engine', 'career_ops')}
              className={`relative rounded-xl border p-4 text-left transition-all ${
                form.engine === 'career_ops'
                  ? 'border-emerald-500/50 bg-emerald-500/10'
                  : 'border-white/[0.07] hover:border-white/20'
              }`}
            >
              <div className="text-sm font-semibold text-white mb-1">🎯 Quality</div>
              <div className="text-xs text-gray-400 leading-relaxed">
                AI scores each job against your CV (0–10). Generates a tailored PDF.
                You review &amp; submit — perfect for portals (Greenhouse, Ashby, Lever).
              </div>
              {form.engine === 'career_ops' && (
                <span className="absolute top-2 right-2 text-emerald-400 text-xs font-medium">Selected</span>
              )}
            </button>
          </div>
          {form.engine === 'career_ops' && (
            <p className="text-xs text-emerald-600/80 mt-2">
              ✓ Match score + tailored PDF generated per job. Applications land in "Pending Review" — you decide which ones to submit.
            </p>
          )}
        </div>

        {/* Source */}
        <div className="bg-[#141414] border border-white/[0.07] rounded-2xl p-5">
          <label className="block text-xs font-medium text-gray-400 mb-3">Job Source</label>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {SOURCES.map(s => (
              <button
                key={s.value}
                type="button"
                onClick={() => set('source', s.value)}
                className={`py-2.5 rounded-xl text-sm font-medium border transition-all
                  ${form.source === s.value
                    ? 'bg-gradient-to-r from-violet-600/30 to-blue-600/30 border-violet-500/40 text-white'
                    : 'border-white/[0.07] text-gray-500 hover:text-gray-300 hover:bg-white/[0.04]'
                  }`}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>

        {/* Keywords & Location */}
        <div className="bg-[#141414] border border-white/[0.07] rounded-2xl p-5 space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-2">Keywords</label>
            <input
              type="text"
              value={form.keywords}
              onChange={e => set('keywords', e.target.value)}
              placeholder="React, TypeScript, Next.js"
              className="w-full bg-[#1a1a1a] border border-white/[0.07] rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-violet-500/50 transition-colors"
            />
            <p className="text-xs text-gray-600 mt-1.5">Separate multiple keywords with commas</p>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-2">Location</label>
            <input
              type="text"
              value={form.location}
              onChange={e => set('location', e.target.value)}
              placeholder="New York, Remote, etc."
              className="w-full bg-[#1a1a1a] border border-white/[0.07] rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-violet-500/50 transition-colors"
            />
          </div>
        </div>

        {/* Advanced settings */}
        <div className="bg-[#141414] border border-white/[0.07] rounded-2xl p-5 space-y-4">
          <h3 className="text-sm font-semibold text-white">Advanced Settings</h3>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-2">Daily Limit</label>
              <input
                type="number"
                min={1}
                max={200}
                value={form.daily_limit}
                onChange={e => set('daily_limit', Number(e.target.value))}
                className="w-full bg-[#1a1a1a] border border-white/[0.07] rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-violet-500/50 transition-colors"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-2">Experience</label>
              <select
                value={form.experience}
                onChange={e => set('experience', e.target.value)}
                className="w-full bg-[#1a1a1a] border border-white/[0.07] rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-violet-500/50 transition-colors"
              >
                <option value="">Any</option>
                <option value="noExperience">No experience</option>
                <option value="between1And3">1–3 years</option>
                <option value="between3And6">3–6 years</option>
                <option value="moreThan6">6+ years</option>
              </select>
            </div>
          </div>

          {/* Cover letter toggle */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-white">AI Cover Letter</p>
              <p className="text-xs text-gray-500 mt-0.5">Generate a tailored cover letter for each job</p>
            </div>
            <button
              type="button"
              onClick={() => set('cover_letter', !form.cover_letter)}
              className={`relative w-11 h-6 rounded-full transition-colors ${form.cover_letter ? 'bg-gradient-to-r from-violet-600 to-blue-600' : 'bg-gray-700'}`}
            >
              <span className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-all ${form.cover_letter ? 'left-[22px]' : 'left-0.5'}`} />
            </button>
          </div>
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-500 hover:to-blue-500 text-white font-semibold py-3.5 rounded-xl text-sm transition-all disabled:opacity-60"
        >
          {loading ? 'Creating…' : '🚀 Launch Campaign'}
        </button>
      </form>
    </div>
  );
}
