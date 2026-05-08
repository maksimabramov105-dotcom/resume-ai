VACANCY_ANALYSIS_PROMPT = """
Analyse the job posting in detail. Use exactly this structure (headings in UPPERCASE, no # or *):

KEY REQUIREMENTS
Must-haves (deal-breakers without these): [list]
Nice-to-haves (would be a bonus): [list]

ATS KEYWORDS FOR YOUR RESUME
Words you MUST include in your resume to pass automated screening: [comma-separated list]

SALARY ESTIMATE
Market range for this role (based on level and location): [range in USD/local currency]
How to negotiate 20-30% higher: [1-2 specific tips]

RED FLAGS
What concerns you about this posting (if any): [list or "No critical flags detected"]

5 LIKELY INTERVIEW QUESTIONS
Most probable questions for this role: [numbered list]

HOW TO GET THE OFFER
Specific steps to stand out among candidates: [2-3 actionable tips]

JOB POSTING:
{vacancy_text}

Respond in the same language as the job posting. Default to English.
"""
