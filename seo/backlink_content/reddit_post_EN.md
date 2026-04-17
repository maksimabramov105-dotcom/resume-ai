# Reddit Post — r/jobs (or r/GetEmployed)

Title: I sent 300 job applications in one week without losing my mind — here's what I used (with actual results)

---

After getting laid off in January, I faced the classic job search grind: copy resume, tweak cover letter, fill out the same form for the 40th time, repeat. By day three I was already burned out before even getting a single callback.

I'm a developer, so I did what developers do — I automated it.

What I built (and then turned into a Telegram bot):

The core insight is that most applications fail because of a mismatch between your resume and the job description. Recruiters spend 6 seconds on a resume. If your keywords don't match their ATS filters, you're invisible.

So I wrote a script that:
1. Takes a job description
2. Extracts the key requirements and skills
3. Rewrites my resume to match — keeping everything truthful but reordering priorities and adding relevant keywords
4. Generates a clean PDF/text
5. Submits via the job board's API or form automation (via web service)

The results after 7 days:

- 312 applications sent (hh.ru + LinkedIn + Indeed)
- 47 profile views from recruiters
- 18 callbacks / messages
- 12 actual interview invitations
- 3 offers received (took the second one)

What I used:

The automation part runs as a Telegram bot now — @topbestworkerbot — if you want to try it without setting anything up yourself. Free plan gives 3 auto-applications per day which is enough to test it.

The resume tailoring is Claude under the hood. You paste your base resume once, and for every vacancy it rewrites the bullet points to match. Not fabricating experience — just presenting the same experience in the language the recruiter is looking for.

The honest caveats:

- This works better in markets where volume matters (hh.ru in Russia is ideal)
- LinkedIn has rate limits — the bot is conservative to avoid account flags
- Quality matters more than quantity for senior roles — I'd still write those manually

Happy to answer questions about the technical approach or the job search strategy.

---

Relevant links: [@topbestworkerbot](https://t.me/topbestworkerbot) on Telegram, [resumeai.bot](https://resumeai.bot) for the web version
