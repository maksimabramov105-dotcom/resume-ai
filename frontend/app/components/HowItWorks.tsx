const STEPS = [
  {
    number: "1",
    title: "Go to /app and upload your resume",
    description:
      "Open the web dashboard, paste your resume or upload a PDF. Our AI extracts your experience, skills, and education instantly.",
    icon: "📄",
  },
  {
    number: "2",
    title: "Set your job preferences",
    description:
      "Choose target job titles, locations, salary range, and which platforms to apply on (LinkedIn, Greenhouse, Lever, Workable…). Takes 2 minutes.",
    icon: "⚙️",
  },
  {
    number: "3",
    title: "Auto-apply runs 24/7",
    description:
      "The AI fills application forms, writes a tailored cover letter for each job, and logs every application in your tracker — while you focus on interviews.",
    icon: "🚀",
  },
];

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="py-16 sm:py-24 px-4 bg-white dark:bg-slate-900">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-12">
          <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white mb-3">
            Up and running in 2 minutes
          </h2>
          <p className="text-slate-500 dark:text-slate-400 text-lg">
            Start on the web — or use the Telegram bot as a companion.
          </p>
        </div>

        <div className="grid sm:grid-cols-3 gap-8">
          {STEPS.map((step) => (
            <div key={step.number} className="text-center">
              <div className="w-14 h-14 rounded-2xl bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center text-2xl mx-auto mb-4">
                {step.icon}
              </div>
              <div className="inline-block bg-blue-600 text-white text-xs font-bold px-2.5 py-0.5 rounded-full mb-2">
                Step {step.number}
              </div>
              <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-2">
                {step.title}
              </h3>
              <p className="text-slate-500 dark:text-slate-400 text-sm leading-relaxed">
                {step.description}
              </p>
            </div>
          ))}
        </div>

        <div className="text-center mt-10">
          <a
            href="/app"
            className="inline-flex items-center gap-2 bg-amber-500 hover:bg-amber-600 text-white font-bold px-6 py-3 rounded-xl transition-colors shadow"
          >
            🚀 Open Dashboard
          </a>
        </div>
      </div>
    </section>
  );
}
