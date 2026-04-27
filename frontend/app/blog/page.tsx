'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import Nav from '../components/Nav'
import Footer from '../components/Footer'

interface PostMeta {
  slug: string
  title: string
  meta_description: string
  published_at: string
}

export default function BlogPage() {
  const [posts, setPosts] = useState<PostMeta[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/blog/index.json')
      .then(r => r.json())
      .then(setPosts)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  return (
    <>
      <Nav />
      <main className="max-w-3xl mx-auto px-4 py-16 min-h-screen">
        <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white mb-3">
          Job Search Blog
        </h1>
        <p className="text-slate-500 dark:text-slate-400 mb-10">
          Practical guides on job hunting, resume optimization, and application automation.
        </p>

        {loading && (
          <div className="space-y-6">
            {[1, 2, 3].map(i => (
              <div key={i} className="animate-pulse">
                <div className="h-5 bg-slate-200 dark:bg-slate-700 rounded w-3/4 mb-2" />
                <div className="h-4 bg-slate-100 dark:bg-slate-800 rounded w-full mb-1" />
                <div className="h-3 bg-slate-100 dark:bg-slate-800 rounded w-1/4" />
              </div>
            ))}
          </div>
        )}

        {!loading && posts.length === 0 && (
          <p className="text-slate-400">No posts yet — check back soon.</p>
        )}

        <div className="divide-y divide-slate-100 dark:divide-slate-800">
          {posts.map(post => (
            <article key={post.slug} className="py-6">
              <Link href={`/blog/${post.slug}/`} className="group block">
                <h2 className="text-lg font-semibold text-slate-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors mb-1">
                  {post.title}
                </h2>
                <p className="text-sm text-slate-500 dark:text-slate-400 mb-2 line-clamp-2">
                  {post.meta_description}
                </p>
                <p className="text-xs text-slate-400">
                  {new Date(post.published_at).toLocaleDateString('en-US', {
                    year: 'numeric', month: 'long', day: 'numeric',
                  })}
                </p>
              </Link>
            </article>
          ))}
        </div>
      </main>
      <Footer />
    </>
  )
}
