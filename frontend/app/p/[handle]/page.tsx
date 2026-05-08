// One placeholder so Next.js generates the HTML shell for this route.
// FastAPI serves the real SEO page at GET /p/<handle>; this is a client-side fallback.
export function generateStaticParams() {
  return [{ handle: "_placeholder" }];
}

import PublicPortfolioClient from "./PublicPortfolioClient";

export default async function PublicPortfolioPage({ params }: { params: Promise<{ handle: string }> }) {
  const { handle } = await params;
  return <PublicPortfolioClient handle={handle} />;
}
