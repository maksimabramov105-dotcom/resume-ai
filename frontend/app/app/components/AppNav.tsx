'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from './AuthContext';

const PLAN_STYLES: Record<string, string> = {
  free:      'bg-gray-500/20 text-gray-400 border border-gray-500/30',
  start:     'bg-blue-500/20 text-blue-400 border border-blue-500/30',
  pro:       'bg-violet-500/20 text-violet-400 border border-violet-500/30',
  unlimited: 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/30',
};

const NAV_ITEMS = [
  { href: '/app/dashboard',    label: 'Dashboard' },
  { href: '/app/campaigns',    label: 'Campaigns' },
  { href: '/app/applications', label: 'Applications' },
  { href: '/app/resume',       label: 'Resume' },
  { href: '/app/jobs',         label: 'Job Search' },
  { href: '/app/tracker',      label: 'Tracker' },
];

export default function AppNav() {
  const { user, logout } = useAuth();
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <>
      <nav className="sticky top-0 z-50 bg-[#0a0a0a]/90 backdrop-blur-xl border-b border-white/[0.07] h-[60px] flex items-center justify-between px-6">
        {/* Logo */}
        <Link
          href="/app/dashboard"
          className="text-lg font-extrabold tracking-tight bg-gradient-to-r from-violet-500 to-blue-500 bg-clip-text text-transparent"
        >
          AutoApply
        </Link>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-1">
          {NAV_ITEMS.map(item => {
            const active = pathname?.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all duration-150
                  ${active
                    ? 'bg-white/10 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-white/[0.06]'
                  }`}
              >
                {item.label}
              </Link>
            );
          })}
        </div>

        {/* Right side */}
        <div className="flex items-center gap-2.5">
          <Link
            href="/app/pricing"
            className={`hidden sm:inline-flex text-[11px] font-semibold uppercase tracking-wide px-2.5 py-1 rounded-full
              ${PLAN_STYLES[user?.plan ?? 'free']}`}
          >
            {user?.plan ?? 'free'}
          </Link>
          <button
            onClick={logout}
            className="hidden sm:block text-gray-500 border border-white/[0.07] hover:text-red-400 hover:border-red-500/40 px-3.5 py-1.5 rounded-lg text-sm transition-all duration-150"
          >
            Sign Out
          </button>

          {/* Hamburger */}
          <button
            className="md:hidden flex flex-col gap-[5px] p-1"
            onClick={() => setMobileOpen(o => !o)}
            aria-label="Toggle menu"
          >
            <span className="block w-[22px] h-[2px] bg-gray-300 rounded" />
            <span className="block w-[22px] h-[2px] bg-gray-300 rounded" />
            <span className="block w-[22px] h-[2px] bg-gray-300 rounded" />
          </button>
        </div>
      </nav>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="md:hidden fixed top-[60px] left-0 right-0 bg-[#0e0e0e]/98 backdrop-blur-xl border-b border-white/[0.07] p-4 z-40 flex flex-col gap-1">
          {NAV_ITEMS.map(item => (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setMobileOpen(false)}
              className={`block px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all
                ${pathname?.startsWith(item.href)
                  ? 'bg-white/10 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-white/[0.06]'
                }`}
            >
              {item.label}
            </Link>
          ))}
          <Link href="/app/pricing" onClick={() => setMobileOpen(false)}
            className="block px-3.5 py-2.5 rounded-lg text-sm font-medium text-gray-400 hover:text-white hover:bg-white/[0.06]">
            💳 Plans
          </Link>
          <button
            onClick={logout}
            className="text-left px-3.5 py-2.5 rounded-lg text-sm font-medium text-red-400 hover:bg-red-500/10 transition-all"
          >
            Sign Out
          </button>
        </div>
      )}
    </>
  );
}
