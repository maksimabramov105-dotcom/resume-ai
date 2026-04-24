'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { getMe } from '../../../lib/api';
import type { User } from '../../../lib/types';

interface AuthCtx {
  user: User | null;
  token: string | null;
  loading: boolean;
  setToken: (t: string) => void;
  logout: () => void;
  refresh: () => void;
}

const AuthContext = createContext<AuthCtx>({
  user: null,
  token: null,
  loading: true,
  setToken: () => {},
  logout: () => {},
  refresh: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const loadUser = async (tok: string) => {
    const data = await getMe(tok);
    if (data) setUser(data as User);
    setLoading(false);
  };

  useEffect(() => {
    const stored = localStorage.getItem('aa_token');
    if (stored) {
      setTokenState(stored);
      loadUser(stored);
    } else {
      setLoading(false);
    }
  }, []);

  const setToken = (t: string) => {
    localStorage.setItem('aa_token', t);
    setTokenState(t);
    loadUser(t);
  };

  const logout = () => {
    localStorage.removeItem('aa_token');
    setTokenState(null);
    setUser(null);
    window.location.href = '/app/login';
  };

  const refresh = () => {
    if (token) loadUser(token);
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, setToken, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
