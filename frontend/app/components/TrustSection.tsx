const TRUST_ITEMS = [
  {
    icon: "🔒",
    title: "No password storage",
    desc: "Applications run in your own browser. We never see your job board logins.",
  },
  {
    icon: "🎯",
    title: "Personalized per job",
    desc: "AI tailors each cover letter to the specific job description — not a generic template.",
  },
  {
    icon: "📊",
    title: "Full transparency",
    desc: "Every application is logged. See exactly what was sent, when, and to whom.",
  },
  {
    icon: "⚡",
    title: "Works while you sleep",
    desc: "The bot runs 24/7, applying to fresh postings the moment they go live.",
  },
];

export default function TrustSection() {
  return (
    <section className="py-16 sm:py-24 px-4 bg-white dark:bg-slate-900">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-10">
          <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white mb-3">
            Built different
          </h2>
          <p className="text-slate-500 dark:text-slate-400 text-lg">
            Other bots store your passwords on their servers. We don&apos;t.
          </p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {TRUST_ITEMS.map((item) => (
            <div
              key={item.title}
              className="bg-slate-50 dark:bg-slate-800 rounded-2xl p-6 border border-slate-100 dark:border-slate-700"
            >
              <div className="text-3xl mb-3">{item.icon}</div>
              <h3 className="font-bold text-slate-900 dark:text-white text-sm mb-1">
                {item.title}
              </h3>
              <p className="text-slate-500 dark:text-slate-400 text-sm leading-relaxed">
                {item.desc}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
