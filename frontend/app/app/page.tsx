'use client';

import { useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from './components/AuthContext';

export default function AppRoot() {
  const { token, loading, setToken } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const authToken = searchParams.get('auth');
    if (authToken) {
      setToken(authToken);
      router.replace('/app/dashboard');
      return;
    }
    if (loading) return;
    router.replace(token ? '/app/dashboard' : '/app/login');
  }, [token, loading, router, searchParams, setToken]);

  return (
    <div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center">
      <div className="w-8 h-8 rounded-full border-2 border-violet-500 border-t-transparent animate-spin" />
    </div>
  );
}
