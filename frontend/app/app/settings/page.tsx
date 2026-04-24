'use client';

import { useState, FormEvent } from 'react';
import { api } from '../../../lib/api';
import { useAuth } from '../components/AuthContext';
import { useToast } from '../components/Toast';

export default function SettingsPage() {
  const { user, refresh } = useAuth();
  const { showToast } = useToast();

  const [email, setEmail] = useState(user?.email ?? '');
  const [currentPw, setCurrentPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [savingEmail, setSavingEmail] = useState(false);
  const [savingPw, setSavingPw] = useState(false);

  async function saveEmail(e: FormEvent) {
    e.preventDefault();
    if (!email) { showToast('Email is required', 'error'); return; }
    setSavingEmail(true);
    const res = await api.patch<{ detail?: string }>('/auth/me', { email });
    setSavingEmail(false);
    if (res && !res.detail) { showToast('Email updated', 'success'); refresh(); }
    else showToast(res?.detail ?? 'Failed to update email', 'error');
  }

  async function savePassword(e: FormEvent) {
    e.preventDefault();
    if (!currentPw || !newPw) { showToast('Fill in both password fields', 'error'); return; }
    if (newPw.length < 6) { showToast('Password must be at least 6 characters', 'error'); return; }
    setSavingPw(true);
    const res = await api.post<{ detail?: string }>('/auth/change-password', {
      current_password: currentPw,
      new_password: newPw,
    });
    setSavingPw(false);
    if (res && !res.detail) {
      showToast('Password changed', 'success');
      setCurrentPw(''); setNewPw('');
    } else showToast(res?.detail ?? 'Failed to change password', 'error');
  }

  async function deleteAccount() {
    if (!confirm('Are you sure? This will permanently delete your account and all data.')) return;
    await api.del('/auth/me');
    localStorage.removeItem('aa_token');
    window.location.href = '/app/login';
  }

  return (
    <div className="max-w-[640px] mx-auto px-6 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-gray-500 text-sm mt-0.5">Manage your account preferences</p>
      </div>

      <div className="space-y-5">
        {/* Account info */}
        <div className="bg-[#141414] border border-white/[0.07] rounded-2xl p-5">
          <h2 className="text-sm font-semibold text-white mb-4">Account</h2>
          <div className="flex items-center gap-3 p-3 bg-[#1a1a1a] rounded-xl">
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-violet-600 to-blue-600 flex items-center justify-center text-sm font-bold text-white">
              {user?.email?.[0]?.toUpperCase() ?? '?'}
            </div>
            <div>
              <p className="text-sm font-medium text-white">{user?.email}</p>
              <p className="text-xs text-gray-500">Plan: <span className="capitalize text-gray-400">{user?.plan}</span></p>
            </div>
          </div>
        </div>

        {/* Change email */}
        <div className="bg-[#141414] border border-white/[0.07] rounded-2xl p-5">
          <h2 className="text-sm font-semibold text-white mb-4">Change Email</h2>
          <form onSubmit={saveEmail} className="space-y-3">
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              className="w-full bg-[#1a1a1a] border border-white/[0.07] rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-violet-500/50 transition-colors"
            />
            <button
              type="submit"
              disabled={savingEmail}
              className="bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-500 hover:to-blue-500 text-white font-semibold px-5 py-2.5 rounded-xl text-sm transition-all disabled:opacity-60"
            >
              {savingEmail ? 'Saving…' : 'Save Email'}
            </button>
          </form>
        </div>

        {/* Change password */}
        <div className="bg-[#141414] border border-white/[0.07] rounded-2xl p-5">
          <h2 className="text-sm font-semibold text-white mb-4">Change Password</h2>
          <form onSubmit={savePassword} className="space-y-3">
            <input
              type="password"
              value={currentPw}
              onChange={e => setCurrentPw(e.target.value)}
              placeholder="Current password"
              className="w-full bg-[#1a1a1a] border border-white/[0.07] rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-violet-500/50 transition-colors"
            />
            <input
              type="password"
              value={newPw}
              onChange={e => setNewPw(e.target.value)}
              placeholder="New password (min 6 chars)"
              className="w-full bg-[#1a1a1a] border border-white/[0.07] rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-violet-500/50 transition-colors"
            />
            <button
              type="submit"
              disabled={savingPw}
              className="bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-500 hover:to-blue-500 text-white font-semibold px-5 py-2.5 rounded-xl text-sm transition-all disabled:opacity-60"
            >
              {savingPw ? 'Changing…' : 'Change Password'}
            </button>
          </form>
        </div>

        {/* Notifications */}
        <div className="bg-[#141414] border border-white/[0.07] rounded-2xl p-5">
          <h2 className="text-sm font-semibold text-white mb-4">Notifications</h2>
          <p className="text-xs text-gray-500 mb-3">
            Connect your Telegram account to receive real-time updates about your campaigns.
          </p>
          {user?.telegram_id ? (
            <div className="flex items-center gap-2 text-emerald-400 text-sm">
              <span>✓</span>
              <span>Telegram connected</span>
            </div>
          ) : (
            <a
              href="https://t.me/ResumeAIBot"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 border border-white/[0.07] hover:bg-white/[0.04] text-gray-400 hover:text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-all"
            >
              🤖 Connect Telegram
            </a>
          )}
        </div>

        {/* Danger zone */}
        <div className="bg-[#141414] border border-red-500/20 rounded-2xl p-5">
          <h2 className="text-sm font-semibold text-red-400 mb-2">Danger Zone</h2>
          <p className="text-xs text-gray-500 mb-4">
            Permanently delete your account and all associated data. This cannot be undone.
          </p>
          <button
            onClick={deleteAccount}
            className="border border-red-500/40 text-red-400 hover:bg-red-500/10 px-4 py-2.5 rounded-xl text-sm font-medium transition-all"
          >
            Delete Account
          </button>
        </div>
      </div>
    </div>
  );
}
