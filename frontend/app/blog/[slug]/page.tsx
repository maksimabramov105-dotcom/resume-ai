import BlogPostClient from './BlogPostClient'

// One placeholder so Next.js generates the HTML shell for this route.
// Nginx serves this shell for ALL /blog/[slug]/ paths via try_files fallback.
export function generateStaticParams() {
  return [{ slug: '_placeholder' }]
}

export default function BlogPostPage() {
  return <BlogPostClient />
}
