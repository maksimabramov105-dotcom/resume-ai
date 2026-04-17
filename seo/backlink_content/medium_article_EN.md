# Medium Article

**Title:** I Automated My Job Search and Got 12 Interviews in 7 Days

**Subtitle:** How I built a system that sends tailored applications while I sleep — and why it actually worked

---

The job search in 2026 is broken.

Job boards have hundreds of listings. Recruiters skim resumes for six seconds. ATS systems reject 75% of candidates before a human ever reads the application. And yet the advice remains the same: 'customize each application individually.'

That's mathematically impossible at the scale needed to land a job quickly. So I decided to automate it properly.

The Problem With Mass Applying

I want to be clear about something: sending the same resume to 500 jobs doesn't work. I know because I tried it in 2022 and got zero callbacks.

The issue is keyword matching. When a job description says 'experience with distributed systems' and your resume says 'worked on backend microservices architecture,' an ATS might score you lower than a candidate who literally copy-pasted the job requirements into their resume.

The solution isn't to be dishonest. It's to translate your real experience into the recruiter's language — consistently, at scale.

What I Built

I spent about two weeks building a pipeline:

Step 1: Scraping — Pull fresh vacancies from hh.ru (Russia's largest job board), SuperJob, and LinkedIn using their official APIs. Filter by keywords, salary range, and experience level.

Step 2: Resume tailoring — For each vacancy, send the job description + my base resume to AI with a prompt that says: 'Rewrite this resume to highlight experience relevant to this role. Do not fabricate anything. Reorder and rephrase existing bullet points to match the job's language.'

Step 3: PDF generation** — Convert the tailored text to a clean one-page PDF using reportlab.

Step 4: Auto-apply — Submit via the job board's API where available (hh.ru has a great API), or via Playwright form automation for sites without APIs.

Step 5: Tracking — Log every application to SQLite with status, timestamps, and any recruiter responses.

The Results

Over 7 days running the system:

- 312 applications sent
- 47 profile views from recruiters
- 18 recruiter messages/calls
- 12 interview invitations
- 3 job offers

I accepted an offer from a company I genuinely wanted to work at. The salary was 23% higher than my previous role.

What Surprised Me

**The tailoring actually matters.** I ran an A/B test for the first 50 applications: 25 with tailored resumes, 25 with my generic resume. Tailored: 8 callbacks. Generic: 1 callback.

Volume is necessary but not sufficient.** The combination of volume AND personalization is what worked.

Speed matters.** Applications submitted within 1-2 hours of a vacancy posting have significantly higher callback rates. My system checks for new postings every 30 minutes.

The Ethical Question

Is this cheating?

I don't think so. Every word in my resume is true. I'm not inflating my experience — I'm presenting it in the vocabulary the recruiter uses. The tailoring is closer to good writing than deception.

How to Try It

I packaged this into a Telegram bot — [@topbestworkerbot](https://t.me/topbestworkerbot) — so you don't need to set up the infrastructure yourself. You upload your base resume, configure filters, and it runs automatically. Free plan: 3 applications per day.

The full web version is at [resumeai.bot](https://resumeai.bot).


Have questions about the technical implementation or the job search strategy? Leave a comment.
