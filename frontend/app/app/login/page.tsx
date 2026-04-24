'use client';

import { useState, FormEvent } from 'react';
import { login, register } from '../../../lib/api';
import { useAuth } from '../components/AuthContext';
import { useToast } from '../components/Toast';

type Tab = 'login' | 'register';

export default function LoginPage() {
  const [tab, setTab] = useState<Tab>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { setToken } = useAuth();
  const { showToast } = useToast();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!email || !password) { showToast('Please fill in all fields', 'error'); return; }
    setLoading(true);

    const fn = tab === 'login' ? login : register;
    const res = await fn(email, password);
    setLoading(false);

    if (!res) { showToast('Connection error. Please try again.', 'error'); return; }

    if (res.access_token) {
      setToken(res.access_token);
    } else {
      showToast(res.detail ?? 'Invalid email or password', 'error');
    }
  }

  return (
    <div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center p-4">
      <div className="w-full max-w-[400px]">
        {/* Logo */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-extrabold bg-gradient-to-r from-violet-500 to-blue-500 bg-clip-text text-transparent">
            AutoApply
          </h1>
          <p className="text-gray-500 text-sm mt-1">Automated Job Applications</p>
        </div>

        {/* Card */}
        <div className="bg-[#141414] border border-white/[0.07] rounded-2xl p-7">
          {/* Tabs */}
          <div className="flex bg-[#0a0a0a] rounded-xl p-1 mb-6">
            {(['login', 'register'] as Tab[]).map(t => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`flex-1 py-2 text-sm font-semibold rounded-lg transition-all capitalize
                  ${tab === t
                    ? 'bg-gradient-to-r from-violet-600 to-blue-600 text-white'
                    : 'text-gray-500 hover:text-gray-300'
                  }`}
              >
                {t === 'login' ? 'Sign In' : 'Sign Up'}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5">Email</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full bg-[#1a1a1a] border border-white/[0.07] rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-violet-500/50 transition-colors"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5">Password</label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-[#1a1a1a] border border-white/[0.07] rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-violet-500/50 transition-colors"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-500 hover:to-blue-500 text-white font-semibold py-3 rounded-xl text-sm transition-all mt-1 disabled:opacity-60"
            >
              {loading ? 'Please wait…' : tab === 'login' ? 'Sign In' : 'Create Account'}
            </button>
          </form>

          {/* Divider */}
          <div className="flex items-center gap-3 my-5">
            <div className="flex-1 h-px bg-white/[0.07]" />
            <span className="text-xs text-gray-600">or</span>
            <div className="flex-1 h-px bg-white/[0.07]" />
          </div>

          {/* Telegram */}
          <a
            href="https://t.me/ResumeAIBot"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center gap-2 w-full border border-white/[0.07] hover:bg-white/[0.04] text-gray-400 hover:text-white py-3 rounded-xl text-sm font-medium transition-all"
          >
            🤖 Sign in via Telegram Bot
          </a>
        </div>

        <p className="text-center text-xs text-gray-600 mt-5">
          By continuing you agree to our{' '}
          <a href="/terms" className="text-gray-500 hover:text-gray-300">Terms</a> &amp;{' '}
          <a href="/privacy" className="text-gray-500 hover:text-gray-300">Privacy Policy</a>
        </p>
      </div>
    </div>
  );
}
