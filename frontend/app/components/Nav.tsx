import Link from "next/link";

export default function Nav() {
  return (
    <nav className="sticky top-0 z-50 bg-white/90 dark:bg-slate-900/90 backdrop-blur border-b border-slate-200 dark:border-slate-700">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
        <Link href="/" className="font-bold text-xl text-blue-600 dark:text-blue-400">
          ResumeAI
        </Link>
        <div className="hidden sm:flex items-center gap-6 text-sm text-slate-600 dark:text-slate-400">
          <a href="#how-it-works" className="hover:text-blue-600 transition-colors">How it works</a>
          <a href="#pricing" className="hover:text-blue-600 transition-colors">Pricing</a>
          <a href="#faq" className="hover:text-blue-600 transition-colors">FAQ</a>
          <a href="/app" className="hover:text-blue-600 transition-colors font-medium">Dashboard</a>
        </div>
        <a
          href="/app"
          className="bg-amber-500 hover:bg-amber-600 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors min-h-[40px] flex items-center"
        >
          Try Free
        </a>
      </div>
    </nav>
  );
}
