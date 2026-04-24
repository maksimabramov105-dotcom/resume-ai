'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '../../../lib/api';
import { useAuth } from '../components/AuthContext';
import { useToast } from '../components/Toast';

const PLANS = [
  {
    id: 'free',
    name: 'Free',
    price: 0,
    period: '',
    limit: 10,
    features: ['10 applications / month', '1 campaign', 'Basic job search', 'Email support'],
    popular: false,
  },
  {
    id: 'start',
    name: 'Starter',
    price: 2.99,
    period: '/14 days',
    limit: 30,
    features: ['30 applications', '3 campaigns', 'AI cover letters', 'All job sources', 'Priority support'],
    popular: false,
    badge: 'Trial',
  },
  {
    id: 'pro',
    name: 'Pro',
    price: 14.99,
    period: '/month',
    limit: 300,
    features: ['300 applications / month', 'Unlimited campaigns', 'AI cover letters', 'All job sources', 'Analytics dashboard', 'Priority support'],
    popular: true,
  },
  {
    id: 'unlimited',
    name: 'Unlimited',
    price: 29.99,
    period: '/month',
    limit: 999999,
    features: ['Unlimited applications', 'Unlimited campaigns', 'AI cover letters', 'All job sources', 'Advanced analytics', '24/7 support', 'API access'],
    popular: false,
  },
];

export default function PricingPage() {
  const { user } = useAuth();
  const { showToast } = useToast();
  const router = useRouter();
  const [loading, setLoading] = useState<string | null>(null);

  async function selectPlan(planId: string) {
    if (planId === 'free') {
      showToast('You are on the Free plan', 'info');
      return;
    }
    if (planId === user?.plan) {
      showToast('You already have this plan', 'info');
      return;
    }
    setLoading(planId);
    const res = await api.post<{ checkout_url?: string; detail?: string }>(
      '/payments/checkout',
      { plan: planId }
    );
    setLoading(null);
    if (res?.checkout_url) {
      window.location.href = res.checkout_url;
    } else {
      showToast(res?.detail ?? 'Failed to start checkout', 'error');
    }
  }

  return (
    <div className="max-w-[1100px] mx-auto px-6 py-8">
      <div className="text-center mb-12">
        <h1 className="text-3xl font-bold text-white mb-3">Choose your plan</h1>
        <p className="text-gray-500 text-base">
          Start free, upgrade when you need more applications.
        </p>
        {user && (
          <p className="text-sm text-gray-600 mt-2">
            Current plan: <span className="text-gray-400 capitalize font-medium">{user.plan}</span>
          </p>
        )}
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {PLANS.map(plan => {
          const isCurrent = user?.plan === plan.id;
          const isPopular = plan.popular;
          return (
            <div
              key={plan.id}
              className={`relative bg-[#141414] border rounded-2xl p-6 flex flex-col
                ${isPopular ? 'border-violet-500/50 shadow-lg shadow-violet-500/10' : 'border-white/[0.07]'}`}
            >
              {isPopular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="bg-gradient-to-r from-violet-600 to-blue-600 text-white text-[11px] font-bold uppercase tracking-wide px-3 py-1 rounded-full">
                    Most Popular
                  </span>
                </div>
              )}
              {plan.badge && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="bg-blue-600 text-white text-[11px] font-bold uppercase tracking-wide px-3 py-1 rounded-full">
                    {plan.badge}
                  </span>
                </div>
              )}

              <div className="mb-5">
                <h3 className="text-base font-bold text-white mb-1">{plan.name}</h3>
                <div className="flex items-baseline gap-1">
                  <span className="text-3xl font-extrabold text-white">${plan.price}</span>
                  {plan.period && <span className="text-gray-500 text-sm">{plan.period}</span>}
                </div>
                <p className="text-xs text-gray-600 mt-1">
                  {plan.limit === 999999 ? 'Unlimited' : plan.limit} applications
                </p>
              </div>

              <ul className="space-y-2 mb-6 flex-1">
                {plan.features.map(f => (
                  <li key={f} className="flex items-start gap-2 text-sm text-gray-400">
                    <span className="text-emerald-500 shrink-0 mt-0.5">✓</span>
                    {f}
                  </li>
                ))}
              </ul>

              <button
                onClick={() => selectPlan(plan.id)}
                disabled={isCurrent || loading === plan.id}
                className={`w-full py-2.5 rounded-xl text-sm font-semibold transition-all
                  ${isCurrent
                    ? 'bg-white/[0.06] text-gray-500 cursor-default'
                    : isPopular
                      ? 'bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-500 hover:to-blue-500 text-white'
                      : 'border border-white/[0.12] text-gray-300 hover:bg-white/[0.06]'
                  } disabled:opacity-60`}
              >
                {loading === plan.id ? 'Loading…' : isCurrent ? 'Current Plan' : plan.price === 0 ? 'Downgrade' : 'Upgrade'}
              </button>
            </div>
          );
        })}
      </div>

      <p className="text-center text-xs text-gray-600 mt-8">
        All plans include a 7-day money-back guarantee. Cancel anytime.
      </p>
    </div>
  );
}
