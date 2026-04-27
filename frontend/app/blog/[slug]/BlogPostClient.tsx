'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import Nav from '../../components/Nav'
import Footer from '../../components/Footer'

interface PostMeta {
  slug: string
  filename: string
}

interface Post {
  title: string
  content_html: string
  published_at: string
}

export default function BlogPostClient() {
  const params = useParams()
  const slug = params?.slug as string
  const [post, setPost] = useState<Post | null>(null)
  const [notFound, setNotFound] = useState(false)

  useEffect(() => {
    if (!slug || slug === '_placeholder') return
    fetch('/blog/index.json')
      .then(r => r.json())
      .then((index: PostMeta[]) => {
        const entry = index.find(p => p.slug === slug)
        if (!entry) { setNotFound(true); return null }
        return fetch(`/blog/${entry.filename}`)
      })
      .then(r => r?.json())
      .then(data => data && setPost(data))
      .catch(() => setNotFound(true))
  }, [slug])

  if (slug === '_placeholder') return null

  if (notFound) return (
    <>
      <Nav />
      <main className="max-w-3xl mx-auto px-4 py-16 min-h-screen">
        <p className="text-slate-500 mb-4">Post not found.</p>
        <Link href="/blog/" className="text-blue-600 hover:underline text-sm">← Back to blog</Link>
      </main>
      <Footer />
    </>
  )

  if (!post) return (
    <>
      <Nav />
      <main className="max-w-3xl mx-auto px-4 py-16 min-h-screen">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-slate-200 dark:bg-slate-700 rounded w-3/4" />
          <div className="h-4 bg-slate-100 dark:bg-slate-800 rounded w-1/4" />
          <div className="space-y-2 mt-8">
            {[1,2,3,4].map(i => <div key={i} className="h-4 bg-slate-100 dark:bg-slate-800 rounded" />)}
          </div>
        </div>
      </main>
      <Footer />
    </>
  )

  return (
    <>
      <Nav />
      <main className="max-w-3xl mx-auto px-4 py-16 min-h-screen">
        <Link href="/blog/" className="text-blue-600 hover:underline text-sm mb-6 block">
          ← All posts
        </Link>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white mb-2">
          {post.title}
        </h1>
        <p className="text-xs text-slate-400 mb-10">
          {new Date(post.published_at).toLocaleDateString('en-US', {
            year: 'numeric', month: 'long', day: 'numeric',
          })}
        </p>
        <div
          className="text-slate-700 dark:text-slate-300 leading-relaxed
            [&>h2]:text-2xl [&>h2]:font-bold [&>h2]:text-slate-900 [&>h2]:dark:text-white [&>h2]:mt-10 [&>h2]:mb-4
            [&>p]:mb-5
            [&>ul]:list-disc [&>ul]:pl-6 [&>ul]:mb-5 [&>ul>li]:mb-1
            [&>ol]:list-decimal [&>ol]:pl-6 [&>ol]:mb-5
            [&>a]:text-blue-600 [&>a]:hover:underline
            [&>strong]:font-semibold [&>strong]:text-slate-900 [&>strong]:dark:text-white"
          dangerouslySetInnerHTML={{ __html: post.content_html }}
        />
      </main>
      <Footer />
    </>
  )
}
