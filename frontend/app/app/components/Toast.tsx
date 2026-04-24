'use client';

import { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import type { Toast } from '../../../lib/types';

interface ToastCtx {
  showToast: (message: string, type?: Toast['type']) => void;
}

const ToastContext = createContext<ToastCtx>({ showToast: () => {} });

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const showToast = useCallback((message: string, type: Toast['type'] = 'info') => {
    const id = Math.random().toString(36).slice(2);
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 3500);
  }, []);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div className="fixed bottom-6 right-6 z-[9999] flex flex-col gap-2 pointer-events-none">
        {toasts.map(t => (
          <div
            key={t.id}
            className={`px-4 py-3 rounded-xl text-sm font-medium shadow-xl pointer-events-auto
              ${t.type === 'success' ? 'bg-emerald-500/20 border border-emerald-500/40 text-emerald-300' : ''}
              ${t.type === 'error'   ? 'bg-red-500/20 border border-red-500/40 text-red-300' : ''}
              ${t.type === 'info'    ? 'bg-blue-500/20 border border-blue-500/40 text-blue-300' : ''}
              animate-in slide-in-from-right-4 fade-in duration-300`}
          >
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}
