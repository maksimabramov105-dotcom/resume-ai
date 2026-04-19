export default function CtaSection() {
  return (
    <section className="py-16 sm:py-20 px-4 bg-blue-600 dark:bg-blue-700">
      <div className="max-w-3xl mx-auto text-center text-white">
        <h2 className="text-3xl sm:text-4xl font-extrabold mb-4">
          Start applying smarter today
        </h2>
        <p className="text-blue-100 text-lg mb-8 max-w-xl mx-auto">
          $2.99 gets you 30 real applications in 14 days. See results before you commit.
        </p>
        <a
          href="https://t.me/topbestworkerbot"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center justify-center gap-2 bg-white text-blue-600 hover:bg-blue-50 font-bold text-lg px-8 py-4 rounded-xl shadow-lg transition-all hover:shadow-xl hover:-translate-y-0.5 min-h-[56px]"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.562 8.248l-2.01 9.478c-.148.66-.537.818-1.084.508l-3-2.21-1.447 1.394c-.16.16-.295.295-.605.295l.213-3.053 5.56-5.023c.242-.213-.054-.333-.373-.12L7.34 14.105l-2.95-.924c-.64-.202-.652-.64.136-.948l11.527-4.447c.533-.194 1 .13.83.924l-.321-.462z"/>
          </svg>
          Try Free in Telegram
        </a>
        <p className="text-blue-200 text-sm mt-4">
          No spam. No data selling. Cancel anytime.
        </p>
      </div>
    </section>
  );
}
