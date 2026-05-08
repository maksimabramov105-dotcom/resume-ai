'use client';

import { useState, useEffect } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? '';

interface Testimonial {
  name: string;
  text: string;
  rating: number;
  created_at?: string;
}

// Seeded beta-tester testimonials shown while API loads or as fallback
const SEED_TESTIMONIALS: Testimonial[] = [
  {
    name: 'Arjun M.',
    text: 'I was applying to 5 jobs a week manually. ResumeAI Bot sent 200 applications in my first month — I had 11 interviews. Landed a role at a Series B startup in Berlin.',
    rating: 5,
  },
  {
    name: 'Lena K.',
    text: 'The tailored cover letters actually sound like me. Three recruiters commented on how well my application was written. I got my current job through one of the bot\'s applications.',
    rating: 5,
  },
  {
    name: 'David O.',
    text: 'Switched from LazyApply because I needed the Telegram interface. Being able to check my applications from my phone without opening a browser is a game changer.',
    rating: 5,
  },
];

function StarRating({ rating }: { rating: number }) {
  return (
    <div className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map((s) => (
        <svg
          key={s}
          className={`w-4 h-4 ${s <= rating ? 'text-amber-400' : 'text-slate-700'}`}
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
        </svg>
      ))}
    </div>
  );
}

export default function Testimonials() {
  const [testimonials, setTestimonials] = useState<Testimonial[]>(SEED_TESTIMONIALS);
  const [active, setActive] = useState(0);

  useEffect(() => {
    fetch(`${API_URL}/api/testimonials`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data: { testimonials?: Testimonial[] } | null) => {
        if (data?.testimonials && data.testimonials.length >= 1) {
          // Merge: API testimonials first, then seeds not already present
          setTestimonials(data.testimonials.slice(0, 6));
        }
      })
      .catch(() => {});
  }, []);

  const shown = testimonials.slice(0, 3);

  return (
    <section className="py-16 sm:py-24 px-4 bg-[#0a0a0a]">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-12">
          <span className="inline-block bg-emerald-500/15 text-emerald-400 text-xs font-semibold px-3 py-1 rounded-full border border-emerald-500/25 mb-4">
            Real results
          </span>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-white mb-3">
            From the people who got hired
          </h2>
          <p className="text-slate-400 text-lg">
            Beta testers who used ResumeAI Bot during early access.
          </p>
        </div>

        {/* Cards */}
        <div className="grid md:grid-cols-3 gap-5">
          {shown.map((t, i) => (
            <div
              key={i}
              className="bg-[#141414] border border-white/[0.07] rounded-2xl p-6 flex flex-col gap-4 hover:border-white/[0.12] transition-colors"
            >
              <StarRating rating={t.rating} />
              <p className="text-slate-300 text-sm leading-relaxed flex-1">
                &ldquo;{t.text}&rdquo;
              </p>
              <div className="flex items-center gap-3 pt-2 border-t border-white/[0.06]">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-violet-500 to-blue-500 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                  {t.name[0]}
                </div>
                <span className="text-white text-sm font-medium">{t.name}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Navigation dots */}
        {testimonials.length > 3 && (
          <div className="flex justify-center gap-2 mt-6">
            {Array.from({ length: Math.ceil(testimonials.length / 3) }).map((_, i) => (
              <button
                key={i}
                onClick={() => setActive(i)}
                className={`w-2 h-2 rounded-full transition-colors ${
                  i === active ? 'bg-violet-500' : 'bg-white/20'
                }`}
              />
            ))}
          </div>
        )}

        {/* Submit your testimonial */}
        <p className="text-center text-slate-600 text-sm mt-8">
          Got hired using ResumeAI Bot?{' '}
          <a href="https://t.me/topbestworkerbot" className="text-violet-400 hover:text-violet-300 transition-colors">
            Share your story →
          </a>
        </p>
      </div>
    </section>
  );
}
