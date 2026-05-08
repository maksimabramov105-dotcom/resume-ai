'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useAuth } from '../../components/AuthContext';
import VoiceRecorder from '../../../components/VoiceRecorder';

type PageState = 'landing' | 'recording' | 'transcribing' | 'structuring' | 'done' | 'error';

interface ResumeBlob {
  name?: string;
  headline?: string;
  summary?: string;
  experience?: Array<{ company: string; position: string; period: string; description: string }>;
  education?: Array<{ institution: string; degree: string; period: string }>;
  skills?: string[];
  languages?: Array<{ language: string; level: string }>;
  contact?: { email: string; phone: string; location: string; linkedin: string };
}

export default function VoiceResumePage() {
  const { user } = useAuth();
  const [pageState, setPageState] = useState<PageState>('landing');
  const [errorMsg, setErrorMsg] = useState('');
  const [resumeBlob, setResumeBlob] = useState<ResumeBlob | null>(null);
  const [savedToPortfolio, setSavedToPortfolio] = useState(false);

  const isFreePlan = !user?.plan || user.plan === 'free';

  const handleRecordingComplete = async (blob: Blob, _durationSec: number) => {
    setPageState('transcribing');
    setErrorMsg('');

    const token = localStorage.getItem('aa_token');
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    // Step 1: Transcribe
    let transcript = '';
    try {
      const form = new FormData();
      const ext = blob.type.includes('webm') ? 'webm' : 'mp4';
      form.append('audio', blob, `recording.${ext}`);

      const res = await fetch('/api/resume/voice/transcribe', {
        method: 'POST',
        headers,
        body: form,
      });

      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.detail ?? `Transcription failed (${res.status})`);
      }

      const data = await res.json();
      transcript = data.transcript ?? '';
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Transcription error';
      setErrorMsg(message);
      setPageState('error');
      return;
    }

    // Step 2: Structure
    setPageState('structuring');
    try {
      const res = await fetch('/api/resume/voice/build', {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ transcript, save_to_portfolio: true }),
      });

      if (res.status === 429) {
        const data = await res.json().catch(() => null);
        const detail = data?.detail;
        if (detail && typeof detail === 'object') {
          throw new Error(`Daily voice limit reached (${detail.limit} per day on ${detail.plan} plan). Upgrade for more.`);
        }
        throw new Error('Daily voice limit reached. Please upgrade your plan.');
      }

      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.detail ?? `Resume build failed (${res.status})`);
      }

      const data = await res.json();
      setResumeBlob(data.resume_blob ?? null);
      setSavedToPortfolio(data.saved ?? false);
      setPageState('done');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Resume build error';
      setErrorMsg(message);
      setPageState('error');
    }
  };

  return (
    <div className="max-w-[860px] mx-auto px-6 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 text-sm text-gray-500 mb-3">
          <Link href="/app/resume" className="hover:text-gray-300 transition-colors">Resume</Link>
          <span>›</span>
          <span className="text-gray-300">Voice Builder</span>
        </div>
        <h1 className="text-2xl font-bold text-white">Voice Resume Builder</h1>
        <p className="text-gray-500 text-sm mt-1">
          Speak about your experience for 2–5 minutes. AI will structure it into a complete resume.
        </p>
      </div>

      {/* Free plan quota warning */}
      {isFreePlan && pageState === 'landing' && (
        <div className="mb-6 bg-yellow-500/10 border border-yellow-500/30 rounded-2xl px-5 py-4 flex items-start gap-3">
          <span className="text-yellow-400 text-lg shrink-0">⚠️</span>
          <div>
            <p className="text-sm font-semibold text-yellow-300">Free plan: 1 voice build per day</p>
            <p className="text-xs text-yellow-500 mt-0.5">
              <Link href="/app/pricing" className="underline">Upgrade to Pro</Link> for up to 20 voice builds per day.
            </p>
          </div>
        </div>
      )}

      {/* Landing state */}
      {pageState === 'landing' && (
        <div className="bg-[#141414] border border-white/[0.07] rounded-2xl p-10 flex flex-col items-center text-center gap-6">
          <div className="w-20 h-20 bg-gradient-to-br from-violet-600/20 to-blue-600/20 border border-violet-500/30 rounded-2xl flex items-center justify-center text-4xl">
            🎙
          </div>
          <div>
            <h2 className="text-xl font-bold text-white mb-2">Speak your resume into existence</h2>
            <p className="text-gray-500 text-sm max-w-md">
              Talk naturally about your work history, education, skills, and achievements.
              Our AI will extract and structure everything automatically.
            </p>
          </div>
          <div className="flex gap-8 text-center text-sm">
            {[
              { icon: '⏱', label: '2–5 minutes', sub: 'ideal length' },
              { icon: '🤖', label: 'Whisper AI', sub: 'transcription' },
              { icon: '✨', label: 'GPT-4o-mini', sub: 'structuring' },
            ].map(({ icon, label, sub }) => (
              <div key={label} className="flex flex-col items-center gap-1">
                <span className="text-2xl">{icon}</span>
                <span className="text-white font-semibold">{label}</span>
                <span className="text-gray-600 text-xs">{sub}</span>
              </div>
            ))}
          </div>
          <VoiceRecorder
            onRecordingComplete={handleRecordingComplete}
            maxDurationSec={300}
          />
        </div>
      )}

      {/* Recording state — VoiceRecorder handles its own UI during recording */}
      {pageState === 'recording' && (
        <div className="bg-[#141414] border border-white/[0.07] rounded-2xl p-10 flex flex-col items-center gap-6">
          <VoiceRecorder
            onRecordingComplete={handleRecordingComplete}
            maxDurationSec={300}
          />
        </div>
      )}

      {/* Processing states */}
      {(pageState === 'transcribing' || pageState === 'structuring') && (
        <div className="bg-[#141414] border border-white/[0.07] rounded-2xl p-10 flex flex-col items-center gap-6">
          <div className="w-16 h-16 rounded-full border-2 border-violet-500/30 border-t-violet-500 animate-spin" />
          <div className="text-center">
            <p className="text-white font-semibold text-lg">
              {pageState === 'transcribing' ? 'Transcribing audio…' : 'Structuring resume…'}
            </p>
            <p className="text-gray-500 text-sm mt-1">
              {pageState === 'transcribing'
                ? 'Converting your speech to text with Whisper AI'
                : 'Extracting and organising your experience with GPT-4o-mini'}
            </p>
          </div>
          {/* Progress steps */}
          <div className="flex items-center gap-3 text-sm">
            <div className={`flex items-center gap-1.5 ${pageState === 'transcribing' ? 'text-violet-400' : 'text-green-400'}`}>
              <span>{pageState === 'transcribing' ? '⏳' : '✅'}</span>
              <span>Transcribe</span>
            </div>
            <span className="text-gray-700">→</span>
            <div className={`flex items-center gap-1.5 ${pageState === 'structuring' ? 'text-violet-400' : 'text-gray-600'}`}>
              <span>{pageState === 'structuring' ? '⏳' : '○'}</span>
              <span>Structure</span>
            </div>
          </div>
        </div>
      )}

      {/* Error state */}
      {pageState === 'error' && (
        <div className="bg-[#141414] border border-white/[0.07] rounded-2xl p-8 flex flex-col items-center gap-4 text-center">
          <span className="text-4xl">❌</span>
          <div>
            <p className="text-white font-semibold">Something went wrong</p>
            <p className="text-red-400 text-sm mt-2">{errorMsg}</p>
          </div>
          <button
            onClick={() => { setPageState('landing'); setErrorMsg(''); }}
            className="bg-white/5 hover:bg-white/10 border border-white/10 text-white font-medium px-5 py-2.5 rounded-xl text-sm transition-all"
          >
            Try again
          </button>
        </div>
      )}

      {/* Done state */}
      {pageState === 'done' && resumeBlob && (
        <div className="flex flex-col gap-6">
          {/* Success banner */}
          <div className="bg-green-500/10 border border-green-500/30 rounded-2xl px-5 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-green-400 text-2xl">✅</span>
              <div>
                <p className="text-sm font-semibold text-green-300">Resume built successfully!</p>
                {savedToPortfolio && (
                  <p className="text-xs text-green-600 mt-0.5">Saved to your portfolio.</p>
                )}
              </div>
            </div>
            <div className="flex gap-2">
              <Link
                href="/app/profile"
                className="bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-500 hover:to-blue-500 text-white font-semibold px-4 py-2 rounded-xl text-sm transition-all"
              >
                View portfolio →
              </Link>
              <button
                onClick={() => setPageState('landing')}
                className="bg-white/5 hover:bg-white/10 border border-white/10 text-white font-medium px-4 py-2 rounded-xl text-sm transition-all"
              >
                Record again
              </button>
            </div>
          </div>

          {/* Resume preview */}
          <div className="bg-[#141414] border border-white/[0.07] rounded-2xl p-6 space-y-5">
            {/* Header info */}
            <div className="border-b border-white/[0.07] pb-4">
              <h2 className="text-xl font-bold text-white">{resumeBlob.name || 'Your Name'}</h2>
              {resumeBlob.headline && (
                <p className="text-violet-400 font-medium mt-0.5">{resumeBlob.headline}</p>
              )}
              {resumeBlob.summary && (
                <p className="text-gray-400 text-sm mt-2 leading-relaxed">{resumeBlob.summary}</p>
              )}
              {resumeBlob.contact && (resumeBlob.contact.email || resumeBlob.contact.location) && (
                <div className="flex flex-wrap gap-3 mt-2 text-xs text-gray-500">
                  {resumeBlob.contact.email && <span>✉ {resumeBlob.contact.email}</span>}
                  {resumeBlob.contact.phone && <span>📞 {resumeBlob.contact.phone}</span>}
                  {resumeBlob.contact.location && <span>📍 {resumeBlob.contact.location}</span>}
                  {resumeBlob.contact.linkedin && <span>🔗 {resumeBlob.contact.linkedin}</span>}
                </div>
              )}
            </div>

            {/* Experience */}
            {resumeBlob.experience && resumeBlob.experience.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-widest text-gray-500 mb-3">Experience</h3>
                <div className="space-y-3">
                  {resumeBlob.experience.map((exp, i) => (
                    <div key={i} className="bg-[#1a1a1a] rounded-xl px-4 py-3">
                      <div className="flex items-start justify-between">
                        <div>
                          <p className="text-sm font-semibold text-white">{exp.position}</p>
                          <p className="text-xs text-gray-500">{exp.company}</p>
                        </div>
                        <span className="text-xs text-gray-600 shrink-0 ml-2">{exp.period}</span>
                      </div>
                      {exp.description && (
                        <p className="text-xs text-gray-400 mt-2 whitespace-pre-line">{exp.description}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Education */}
            {resumeBlob.education && resumeBlob.education.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-widest text-gray-500 mb-3">Education</h3>
                <div className="space-y-2">
                  {resumeBlob.education.map((edu, i) => (
                    <div key={i} className="bg-[#1a1a1a] rounded-xl px-4 py-3 flex items-start justify-between">
                      <div>
                        <p className="text-sm font-semibold text-white">{edu.institution}</p>
                        <p className="text-xs text-gray-500">{edu.degree}</p>
                      </div>
                      <span className="text-xs text-gray-600 shrink-0 ml-2">{edu.period}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Skills */}
            {resumeBlob.skills && resumeBlob.skills.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-widest text-gray-500 mb-3">Skills</h3>
                <div className="flex flex-wrap gap-2">
                  {resumeBlob.skills.map((skill, i) => (
                    <span key={i} className="bg-[#1a1a1a] border border-white/[0.07] rounded-lg px-3 py-1 text-xs text-gray-300">
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Languages */}
            {resumeBlob.languages && resumeBlob.languages.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-widest text-gray-500 mb-3">Languages</h3>
                <div className="flex flex-wrap gap-2">
                  {resumeBlob.languages.map((lang, i) => (
                    <span key={i} className="bg-[#1a1a1a] border border-white/[0.07] rounded-lg px-3 py-1 text-xs text-gray-300">
                      {lang.language} <span className="text-gray-600">· {lang.level}</span>
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
