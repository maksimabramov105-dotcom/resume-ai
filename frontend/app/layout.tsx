import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { GoogleAnalytics } from "@next/third-parties/google";
import Script from "next/script";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "ResumeAI — Auto-Apply to 300+ Jobs Per Day",
  description:
    "AI-powered job application bot. Auto-apply to Greenhouse, Lever, Workable, LinkedIn Easy Apply, and more. Set it up in 2 minutes.",
  keywords:
    "auto apply jobs, job application automation, AI job search, Greenhouse autofill, LinkedIn Easy Apply bot",
  openGraph: {
    title: "ResumeAI — Auto-Apply to 300+ Jobs Per Day",
    description:
      "Stop applying manually. Our AI bot applies to hundreds of jobs while you sleep.",
    type: "website",
    url: "https://resumeai-bot.ru",
    siteName: "ResumeAI",
  },
  twitter: {
    card: "summary_large_image",
    title: "ResumeAI — Auto-Apply to 300+ Jobs Per Day",
    description:
      "Stop applying manually. Our AI bot applies to hundreds of jobs while you sleep.",
  },
  alternates: {
    canonical: "https://resumeai-bot.ru",
    languages: {
      en: "https://resumeai-bot.ru",
      "x-default": "https://resumeai-bot.ru",
    },
  },
  robots: { index: true, follow: true },
};

const schemaOrg = JSON.stringify({
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "ResumeAI",
  applicationCategory: "BusinessApplication",
  operatingSystem: "Web, Telegram",
  offers: {
    "@type": "AggregateOffer",
    lowPrice: "2.99",
    highPrice: "29.99",
    priceCurrency: "USD",
  },
  description:
    "AI-powered job application bot that auto-applies to jobs on Greenhouse, Lever, Workable, LinkedIn Easy Apply, and more.",
  aggregateRating: {
    "@type": "AggregateRating",
    ratingValue: "4.8",
    ratingCount: "47",
  },
});

const faqSchema = JSON.stringify({
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: [
    {
      "@type": "Question",
      name: "Which job boards does ResumeAI support?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "ResumeAI supports LinkedIn Easy Apply, Greenhouse, Lever, Workable, Ashby, SmartRecruiters, Adzuna, RemoteOK, The Muse, and Arbeitnow.",
      },
    },
    {
      "@type": "Question",
      name: "Is my data safe with ResumeAI?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Yes. The Chrome Extension model means applications are sent from your own browser using your existing login sessions — we never store your job board passwords.",
      },
    },
    {
      "@type": "Question",
      name: "How many jobs can the bot apply to per day?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "The Pro plan applies to up to 50 jobs per day. The Unlimited plan has no daily cap.",
      },
    },
    {
      "@type": "Question",
      name: "Can I cancel anytime?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Yes. Cancel anytime with one click — no questions asked, no hidden fees.",
      },
    },
    {
      "@type": "Question",
      name: "Does it write personalized cover letters?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Yes. AI generates a tailored cover letter for each job based on your resume and the job description.",
      },
    },
    {
      "@type": "Question",
      name: "What is the $2.99 trial?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "The $2.99 trial gives you 30 applications over 14 days — enough to see real results before committing to a monthly plan.",
      },
    },
  ],
});

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <head>
        <Script id="schema-org" type="application/ld+json">
          {schemaOrg}
        </Script>
        <Script id="faq-schema" type="application/ld+json">
          {faqSchema}
        </Script>
        {/* Yandex Metrika */}
        <Script id="ym" strategy="afterInteractive">{`
          (function(m,e,t,r,i,k,a){m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};
          m[i].l=1*new Date();
          for(var j=0;j<document.scripts.length;j++){if(document.scripts[j].src===r){return;}}
          k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)})
          (window,document,'script','https://mc.yandex.ru/metrika/tag.js','ym');
          ym(108521982,'init',{clickmap:true,trackLinks:true,accurateTrackBounce:true});
        `}</Script>
      </head>
      <body className="bg-white text-slate-900 dark:bg-slate-900 dark:text-slate-100">
        {children}
        <GoogleAnalytics gaId="G-LSSCM2MPNG" />
      </body>
    </html>
  );
}
