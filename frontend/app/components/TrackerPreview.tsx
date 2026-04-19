const TRACKER_ROWS = [
  { company: "Stripe", role: "Software Engineer", status: "Applied", color: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300" },
  { company: "Airbnb", role: "Frontend Developer", status: "Screening", color: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300" },
  { company: "Figma", role: "Full-Stack Engineer", status: "Interview", color: "bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300" },
  { company: "Notion", role: "React Developer", status: "Offer 🎉", color: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300" },
  { company: "Linear", role: "Backend Engineer", status: "Applied", color: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300" },
];

export default function TrackerPreview() {
  return (
    <section className="py-16 sm:py-24 px-4 bg-slate-50 dark:bg-slate-800">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-10">
          <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white mb-3">
            Track every application
          </h2>
          <p className="text-slate-500 dark:text-slate-400 text-lg max-w-xl mx-auto">
            See exactly where you stand — Applied → Screening → Interview → Offer, all in one place.
          </p>
        </div>

        {/* Tracker mockup */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-700 overflow-hidden max-w-2xl mx-auto">
          {/* Header */}
          <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-700 flex items-center gap-3">
            <div className="flex gap-1.5">
              <div className="w-3 h-3 rounded-full bg-red-400" />
              <div className="w-3 h-3 rounded-full bg-yellow-400" />
              <div className="w-3 h-3 rounded-full bg-green-400" />
            </div>
            <span className="text-sm text-slate-500 dark:text-slate-400 font-medium">
              📊 Application Tracker
            </span>
          </div>

          {/* Stats row */}
          <div className="px-5 py-3 bg-slate-50 dark:bg-slate-800/50 border-b border-slate-100 dark:border-slate-700 grid grid-cols-4 gap-2 text-center text-xs">
            {[
              { label: "Applied", val: "147" },
              { label: "Screening", val: "23" },
              { label: "Interviews", val: "4" },
              { label: "Offers", val: "1" },
            ].map(({ label, val }) => (
              <div key={label}>
                <div className="font-bold text-slate-900 dark:text-white text-base">{val}</div>
                <div className="text-slate-500">{label}</div>
              </div>
            ))}
          </div>

          {/* Rows */}
          <div className="divide-y divide-slate-100 dark:divide-slate-700">
            {TRACKER_ROWS.map((row) => (
              <div
                key={`${row.company}-${row.role}`}
                className="px-5 py-3 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
              >
                <div>
                  <div className="text-sm font-semibold text-slate-900 dark:text-white">
                    {row.company}
                  </div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">{row.role}</div>
                </div>
                <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${row.color}`}>
                  {row.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
