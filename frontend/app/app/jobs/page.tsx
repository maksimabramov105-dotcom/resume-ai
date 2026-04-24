'use client';

import { useState, FormEvent } from 'react';
import { api } from '../../../lib/api';
import { useToast } from '../components/Toast';

interface Job {
  id: string;
  title: string;
  company: string;
  location: string;
  salary?: string;
  url: string;
  source: string;
  published_at: string;
}

const SOURCES = ['all', 'hh', 'superjob'];

export default function JobsPage() {
  const [query, setQuery] = useState('');
  const [location, setLocation] = useState('');
  const [source, setSource] = useState('all');
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const { showToast } = useToast();

  async function search(e: FormEvent) {
    e.preventDefault();
    if (!query) { showToast('Enter a job title or keywords', 'error'); return; }
    setLoading(true);
    setSearched(true);
    const params = new URLSearchParams({ q: query });
    if (location) params.set('location', location);
    if (source !== 'all') params.set('source', source);
    const data = await api.get<Job[]>(`/jobs/search?${params.toString()}`);
    setLoading(false);
    if (data) setJobs(data as Job[]);
    else showToast('Search failed', 'error');
  }

  const formatDate = (s: string) =>
    new Date(s).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

  return (
    <div className="max-w-[1100px] mx-auto px-6 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Job Search</h1>
        <p className="text-gray-500 text-sm mt-0.5">Search vacancies across job boards</p>
      </div>

      {/* Search form */}
      <form onSubmit={search} className="bg-[#141414] border border-white/[0.07] rounded-2xl p-5 mb-6">
        <div className="flex flex-col sm:flex-row gap-3 mb-4">
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Job title, skills, keywords…"
            className="flex-1 bg-[#1a1a1a] border border-white/[0.07] rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-violet-500/50 transition-colors"
          />
          <input
            type="text"
            value={location}
            onChange={e => setLocation(e.target.value)}
            placeholder="Location (optional)"
            className="sm:w-48 bg-[#1a1a1a] border border-white/[0.07] rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-violet-500/50 transition-colors"
          />
        </div>

        <div className="flex items-center justify-between gap-3 flex-wrap">
          {/* Source filter */}
          <div className="flex gap-1.5">
            {SOURCES.map(s => (
              <button
                key={s}
                type="button"
                onClick={() => setSource(s)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-all
                  ${source === s
                    ? 'bg-gradient-to-r from-violet-600 to-blue-600 text-white'
                    : 'bg-[#1a1a1a] border border-white/[0.07] text-gray-500 hover:text-gray-300'
                  }`}
              >
                {s === 'all' ? 'All Sources' : s === 'hh' ? 'hh.ru' : 'SuperJob'}
              </button>
            ))}
          </div>

          <button
            type="submit"
            disabled={loading}
            className="bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-500 hover:to-blue-500 text-white font-semibold px-6 py-2.5 rounded-xl text-sm transition-all disabled:opacity-60"
          >
            {loading ? 'Searching…' : '🔍 Search'}
          </button>
        </div>
      </form>

      {/* Results */}
      {loading ? (
        <div className="space-y-3">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-24 bg-[#141414] border border-white/[0.07] rounded-2xl animate-pulse" />
          ))}
        </div>
      ) : searched && jobs.length === 0 ? (
        <div className="bg-[#141414] border border-white/[0.07] rounded-2xl p-16 text-center">
          <p className="text-gray-500 text-sm">No jobs found. Try different keywords.</p>
        </div>
      ) : jobs.length > 0 ? (
        <>
          <p className="text-xs text-gray-600 mb-3">{jobs.length} jobs found</p>
          <div className="space-y-3">
            {jobs.map(job => (
              <a
                key={job.id}
                href={job.url}
                target="_blank"
                rel="noopener noreferrer"
                className="block bg-[#141414] border border-white/[0.07] hover:border-violet-500/30 rounded-2xl px-5 py-4 transition-all group"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-semibold text-white group-hover:text-violet-400 transition-colors truncate">
                      {job.title}
                    </h3>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {job.company}
                      {job.location ? ` · ${job.location}` : ''}
                    </p>
                    {job.salary && (
                      <p className="text-xs text-emerald-400 mt-1">{job.salary}</p>
                    )}
                  </div>
                  <div className="text-right shrink-0">
                    <span className="text-[11px] text-gray-600 uppercase font-medium">{job.source}</span>
                    <p className="text-xs text-gray-600 mt-0.5">{formatDate(job.published_at)}</p>
                  </div>
                </div>
              </a>
            ))}
          </div>
        </>
      ) : (
        <div className="text-center py-16 text-gray-600 text-sm">
          Enter keywords above to search for jobs
        </div>
      )}
    </div>
  );
}
