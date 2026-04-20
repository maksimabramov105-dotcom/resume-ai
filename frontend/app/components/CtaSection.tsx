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
          href="/app"
          className="inline-flex items-center justify-center gap-2 bg-white text-blue-600 hover:bg-blue-50 font-bold text-lg px-8 py-4 rounded-xl shadow-lg transition-all hover:shadow-xl hover:-translate-y-0.5 min-h-[56px]"
        >
          🚀 Open Dashboard — Start Free
        </a>
        <p className="text-blue-200 text-sm mt-4">
          Prefer Telegram?{" "}
          <a
            href="https://t.me/topbestworkerbot"
            target="_blank"
            rel="noopener noreferrer"
            className="underline hover:text-white transition-colors"
          >
            Try the bot →
          </a>
        </p>
      </div>
    </section>
  );
}
