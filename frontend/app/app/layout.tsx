'use client';

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { AuthProvider, useAuth } from './components/AuthContext';
import { ToastProvider } from './components/Toast';
import AppNav from './components/AppNav';

function Shell({ children }: { children: React.ReactNode }) {
  const { token, loading } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  const isAuthPage = pathname === '/app/login' || pathname === '/app/login/';

  useEffect(() => {
    if (loading) return;
    if (!token && !isAuthPage) {
      router.push('/app/login');
    }
    if (token && isAuthPage) {
      router.push('/app/dashboard');
    }
  }, [token, loading, isAuthPage, router]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center">
        <div className="w-8 h-8 rounded-full border-2 border-violet-500 border-t-transparent animate-spin" />
      </div>
    );
  }

  if (isAuthPage) return <>{children}</>;

  if (!token) return null;

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-[#e5e7eb]">
      <AppNav />
      <main>{children}</main>
    </div>
  );
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <ToastProvider>
        <Shell>{children}</Shell>
      </ToastProvider>
    </AuthProvider>
  );
}
