'use client';

import { useEffect, useState, useRef } from 'react';
import { api } from '../../../lib/api';
import { useToast } from '../components/Toast';
import type { Resume } from '../../../lib/types';

export default function ResumePage() {
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const { showToast } = useToast();

  const load = async () => {
    const data = await api.get<Resume[]>('/resumes');
    if (Array.isArray(data)) setResumes(data);
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  async function uploadFile(file: File) {
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) { showToast('File too large (max 5MB)', 'error'); return; }
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!['pdf', 'doc', 'docx'].includes(ext ?? '')) {
      showToast('Only PDF, DOC, DOCX files are allowed', 'error'); return;
    }
    setUploading(true);
    const token = localStorage.getItem('aa_token');
    const form = new FormData();
    form.append('file', file);
    try {
      const res = await fetch('/api/resumes/upload', {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: form,
      });
      if (res.ok) {
        showToast('Resume uploaded!', 'success');
        load();
      } else {
        const d = await res.json().catch(() => null);
        showToast(d?.detail ?? 'Upload failed', 'error');
      }
    } catch {
      showToast('Upload error', 'error');
    }
    setUploading(false);
  }

  async function setActive(id: number) {
    await api.patch(`/resumes/${id}/activate`, {});
    setResumes(prev => prev.map(r => ({ ...r, is_active: r.id === id })));
    showToast('Active resume updated', 'success');
  }

  async function deleteResume(id: number) {
    if (!confirm('Delete this resume?')) return;
    await api.del(`/resumes/${id}`);
    setResumes(prev => prev.filter(r => r.id !== id));
    showToast('Resume deleted', 'info');
  }

  const formatDate = (s: string) =>
    new Date(s).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

  return (
    <div className="max-w-[800px] mx-auto px-6 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Resume</h1>
        <p className="text-gray-500 text-sm mt-0.5">Upload and manage your resumes</p>
      </div>

      {/* Upload zone */}
      <div
        className="bg-[#141414] border-2 border-dashed border-white/[0.1] hover:border-violet-500/40 rounded-2xl p-10 text-center cursor-pointer transition-all mb-6"
        onClick={() => fileRef.current?.click()}
        onDragOver={e => e.preventDefault()}
        onDrop={e => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) uploadFile(f); }}
      >
        <div className="text-4xl mb-3">📄</div>
        <p className="text-white font-medium mb-1">
          {uploading ? 'Uploading…' : 'Drop your resume here'}
        </p>
        <p className="text-xs text-gray-500">PDF, DOC, DOCX up to 5MB</p>
        <button
          type="button"
          disabled={uploading}
          className="mt-4 bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-500 hover:to-blue-500 text-white font-semibold px-5 py-2.5 rounded-xl text-sm transition-all disabled:opacity-60"
        >
          {uploading ? 'Uploading…' : 'Choose File'}
        </button>
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.doc,.docx"
          className="hidden"
          onChange={e => { const f = e.target.files?.[0]; if (f) uploadFile(f); }}
        />
      </div>

      {/* Resume list */}
      {loading ? (
        <div className="space-y-3">
          {[...Array(2)].map((_, i) => (
            <div key={i} className="h-16 bg-[#141414] border border-white/[0.07] rounded-2xl animate-pulse" />
          ))}
        </div>
      ) : resumes.length === 0 ? (
        <div className="bg-[#141414] border border-white/[0.07] rounded-2xl p-10 text-center">
          <p className="text-gray-500 text-sm">No resumes yet. Upload one above.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {resumes.map(r => (
            <div
              key={r.id}
              className={`bg-[#141414] border rounded-2xl px-5 py-4 flex items-center justify-between gap-4
                ${r.is_active ? 'border-violet-500/40' : 'border-white/[0.07]'}`}
            >
              <div className="flex items-center gap-3 min-w-0">
                <span className="text-2xl">📄</span>
                <div className="min-w-0">
                  <p className="text-sm font-medium text-white truncate">{r.filename}</p>
                  <p className="text-xs text-gray-500">{formatDate(r.uploaded_at)}</p>
                </div>
                {r.is_active && (
                  <span className="text-[11px] font-semibold uppercase tracking-wide px-2 py-0.5 rounded-full bg-violet-500/20 text-violet-400 border border-violet-500/30 whitespace-nowrap">
                    Active
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {!r.is_active && (
                  <button
                    onClick={() => setActive(r.id)}
                    className="text-xs font-medium px-3.5 py-1.5 rounded-lg border border-white/[0.07] text-gray-400 hover:text-white hover:bg-white/[0.06] transition-all"
                  >
                    Set Active
                  </button>
                )}
                <button
                  onClick={() => deleteResume(r.id)}
                  className="text-xs font-medium px-3.5 py-1.5 rounded-lg border border-white/[0.07] text-gray-500 hover:text-red-400 hover:border-red-500/40 transition-all"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Tips */}
      <div className="mt-8 bg-[#141414] border border-white/[0.07] rounded-2xl p-5">
        <h3 className="text-sm font-semibold text-white mb-3">Tips for a better resume</h3>
        <ul className="space-y-2">
          {[
            'Use a clean, ATS-friendly format (avoid tables and columns)',
            'Include keywords from job descriptions',
            'Keep it to 1–2 pages',
            'Save as PDF for best compatibility',
          ].map(tip => (
            <li key={tip} className="flex items-start gap-2 text-xs text-gray-500">
              <span className="text-violet-500 shrink-0">•</span>
              {tip}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
