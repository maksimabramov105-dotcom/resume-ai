export default function Footer() {
  return (
    <footer className="bg-slate-900 text-slate-400 py-10 px-4">
      <div className="max-w-5xl mx-auto flex flex-col sm:flex-row justify-between items-center gap-4 text-sm">
        <div>
          <span className="text-white font-bold">ResumeAI</span>
          <span className="ml-2">© {new Date().getFullYear()} All rights reserved.</span>
        </div>
        <div className="flex flex-wrap gap-4 justify-center">
          <a href="/app" className="hover:text-white transition-colors font-medium">
            Dashboard
          </a>
          <a
            href="https://t.me/topbestworkerbot"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-white transition-colors"
          >
            Telegram Bot
          </a>
          <a href="#pricing" className="hover:text-white transition-colors">
            Pricing
          </a>
          <a href="#faq" className="hover:text-white transition-colors">
            FAQ
          </a>
          <a
            href="mailto:support@resumeai-bot.ru"
            className="hover:text-white transition-colors"
          >
            Support
          </a>
        </div>
        <div className="text-xs text-slate-500 text-center sm:text-right">
          No spam. No data selling.{" "}
          <a href="/app" className="underline hover:text-slate-300 transition-colors">
            Cancel anytime.
          </a>
        </div>
      </div>
    </footer>
  );
}
