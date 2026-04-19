const STEPS = [
  {
    number: "1",
    title: "Upload your resume",
    description:
      "Paste your resume or upload a PDF. Our AI extracts all your experience, skills, and education.",
    icon: "📄",
  },
  {
    number: "2",
    title: "Set your preferences",
    description:
      "Choose job titles, locations, salary range, and which platforms to target. Takes 2 minutes.",
    icon: "⚙️",
  },
  {
    number: "3",
    title: "Let it run",
    description:
      "The bot applies round-the-clock — filling forms, writing cover letters, and tracking every application.",
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
            No Chrome extension required to get started. Just open the Telegram bot.
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
      </div>
    </section>
  );
}
