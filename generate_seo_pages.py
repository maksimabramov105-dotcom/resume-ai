#!/usr/bin/env python3
"""
generate_seo_pages.py — Generate English-only SEO landing pages for job titles.

2026-05 international pivot: Russian-language pages archived to landing/_archive_ru/resume/
English pages written to landing/resume/

Run: python3 generate_seo_pages.py
"""
import os
import shutil

JOBS = [
  {"en": "Software Engineer",        "slug": "software-engineer",       "keywords": ["Python", "Java", "Git", "Docker", "SQL", "REST API", "Agile", "CI/CD", "Linux", "Microservices"]},
  {"en": "Product Manager",          "slug": "product-manager",         "keywords": ["Roadmap", "Agile", "Scrum", "Stakeholder", "KPI", "A/B Testing", "Jira", "User Story", "Metrics", "MVP"]},
  {"en": "Data Analyst",             "slug": "data-analyst",            "keywords": ["SQL", "Python", "Excel", "Tableau", "Power BI", "Statistics", "A/B Test", "ETL", "Data Warehouse", "Pandas"]},
  {"en": "UX Designer",              "slug": "ux-designer",             "keywords": ["Figma", "Prototyping", "User Research", "Wireframing", "Usability", "Design System", "A/B Test", "CSS", "Accessibility", "UX Writing"]},
  {"en": "Marketing Manager",        "slug": "marketing-manager",       "keywords": ["SEO", "SMM", "Google Ads", "Email Marketing", "KPI", "ROI", "CRM", "Analytics", "Content Strategy", "PPC"]},
  {"en": "Sales Manager",            "slug": "sales-manager",           "keywords": ["B2B", "CRM", "Cold Calling", "KPI", "Pipeline", "Salesforce", "Negotiation", "Lead Generation", "Upsell", "Revenue"]},
  {"en": "Project Manager",          "slug": "project-manager",         "keywords": ["Agile", "Scrum", "PMP", "Jira", "Confluence", "Risk Management", "Stakeholder", "Roadmap", "Budget", "PMO"]},
  {"en": "DevOps Engineer",          "slug": "devops-engineer",         "keywords": ["Kubernetes", "Docker", "CI/CD", "Terraform", "AWS", "Linux", "Ansible", "Jenkins", "Monitoring", "Git"]},
  {"en": "Frontend Developer",       "slug": "frontend-developer",      "keywords": ["React", "TypeScript", "JavaScript", "CSS", "HTML", "Vue.js", "Webpack", "REST API", "Testing", "Git"]},
  {"en": "Backend Developer",        "slug": "backend-developer",       "keywords": ["Python", "Node.js", "Java", "SQL", "PostgreSQL", "Redis", "Docker", "REST API", "Microservices", "Git"]},
  {"en": "Full Stack Developer",     "slug": "fullstack-developer",     "keywords": ["React", "Node.js", "Python", "PostgreSQL", "Docker", "TypeScript", "REST API", "Git", "AWS", "Redis"]},
  {"en": "QA Engineer",              "slug": "qa-engineer",             "keywords": ["Selenium", "TestNG", "Jira", "API Testing", "Automation", "SQL", "Postman", "Load Testing", "Python", "CI/CD"]},
  {"en": "Business Analyst",         "slug": "business-analyst",        "keywords": ["SQL", "BPMN", "Requirements", "Use Cases", "Jira", "Confluence", "Stakeholder", "Excel", "Visio", "Agile"]},
  {"en": "HR Manager",               "slug": "hr-manager",              "keywords": ["Recruiting", "Onboarding", "HRIS", "KPI", "Employee Relations", "Training", "Performance Review", "Compensation", "Labor Law", "ATS"]},
  {"en": "Accountant",               "slug": "accountant",              "keywords": ["GAAP", "IFRS", "Excel", "QuickBooks", "Financial Reporting", "Audit", "Payroll", "Tax Compliance", "ERP", "Reconciliation"]},
  {"en": "Graphic Designer",         "slug": "graphic-designer",        "keywords": ["Photoshop", "Illustrator", "InDesign", "Figma", "Branding", "Typography", "Layout", "Print", "UI Design", "After Effects"]},
  {"en": "Content Writer",           "slug": "content-writer",          "keywords": ["SEO", "Copywriting", "WordPress", "Content Strategy", "Social Media", "Editing", "Research", "Keywords", "Analytics", "CMS"]},
  {"en": "Customer Support",         "slug": "customer-support",        "keywords": ["CRM", "Zendesk", "Customer Service", "SLA", "Ticketing", "Communication", "KPI", "Escalation", "Product Knowledge", "NPS"]},
  {"en": "System Administrator",     "slug": "system-administrator",    "keywords": ["Windows Server", "Linux", "Active Directory", "Virtualization", "Networking", "Security", "Backup", "DNS", "VMware", "PowerShell"]},
  {"en": "Financial Analyst",        "slug": "financial-analyst",       "keywords": ["Excel", "Financial Modeling", "DCF", "Valuation", "Bloomberg", "SQL", "IFRS", "Budget", "Forecasting", "PowerPoint"]},
  {"en": "Data Scientist",           "slug": "data-scientist",          "keywords": ["Python", "Machine Learning", "TensorFlow", "Pandas", "SQL", "Statistics", "NLP", "Computer Vision", "Jupyter", "Scikit-learn"]},
  {"en": "Machine Learning Engineer","slug": "ml-engineer",             "keywords": ["Python", "TensorFlow", "PyTorch", "MLOps", "Docker", "SQL", "NLP", "Computer Vision", "Kubernetes", "Feature Engineering"]},
  {"en": "iOS Developer",            "slug": "ios-developer",           "keywords": ["Swift", "SwiftUI", "Xcode", "UIKit", "Core Data", "REST API", "Combine", "TestFlight", "Firebase", "Git"]},
  {"en": "Android Developer",        "slug": "android-developer",       "keywords": ["Kotlin", "Java", "Android Studio", "Jetpack Compose", "REST API", "Firebase", "Room", "MVVM", "Coroutines", "Git"]},
  {"en": "Cybersecurity Analyst",    "slug": "cybersecurity-analyst",   "keywords": ["SIEM", "Penetration Testing", "CISSP", "Firewall", "Network Security", "Vulnerability Assessment", "ISO 27001", "SOC", "Python", "IDS/IPS"]},
  {"en": "Cloud Engineer",           "slug": "cloud-engineer",          "keywords": ["AWS", "Azure", "GCP", "Terraform", "Kubernetes", "Docker", "CI/CD", "IaC", "Security", "Networking"]},
  {"en": "Technical Writer",         "slug": "technical-writer",        "keywords": ["Documentation", "Markdown", "API Docs", "DITA", "Confluence", "Git", "XML", "Technical Communication", "UX Writing", "Swagger"]},
  {"en": "UI Designer",              "slug": "ui-designer",             "keywords": ["Figma", "Design System", "CSS", "Prototyping", "Typography", "Color Theory", "Responsive Design", "Accessibility", "Adobe XD", "Sketch"]},
  {"en": "Scrum Master",             "slug": "scrum-master",            "keywords": ["Scrum", "Agile", "Jira", "Kanban", "Retrospectives", "Sprint Planning", "Coaching", "SAFe", "Confluence", "Facilitation"]},
  {"en": "Supply Chain Manager",     "slug": "supply-chain-manager",    "keywords": ["SAP", "ERP", "Logistics", "Procurement", "Inventory", "Forecasting", "Vendor Management", "KPI", "Excel", "LEAN"]},
  {"en": "Teacher",                  "slug": "teacher",                 "keywords": ["Curriculum", "Lesson Planning", "Differentiated Instruction", "Assessment", "Classroom Management", "E-learning", "Moodle", "Google Classroom", "EdTech", "IEP"]},
  {"en": "Nurse",                    "slug": "nurse",                   "keywords": ["Patient Care", "Medical Records", "IV Therapy", "Vital Signs", "EHR", "ACLS", "BLS", "Medication Administration", "ICU", "Triage"]},
  {"en": "Lawyer",                   "slug": "lawyer",                  "keywords": ["Contract Law", "Litigation", "Legal Research", "Due Diligence", "Corporate Law", "Compliance", "Arbitration", "Legal Writing", "IP Law", "Labor Law"]},
  {"en": "Architect",                "slug": "architect",               "keywords": ["AutoCAD", "Revit", "BIM", "ArchiCAD", "3D Modeling", "Building Codes", "Project Management", "Structural Design", "Urban Planning", "Sustainability"]},
  {"en": "Mechanical Engineer",      "slug": "mechanical-engineer",     "keywords": ["AutoCAD", "SolidWorks", "ANSYS", "CAD", "Manufacturing", "FEA", "Thermodynamics", "CNC", "Materials Science", "ISO Standards"]},
  {"en": "Civil Engineer",           "slug": "civil-engineer",          "keywords": ["AutoCAD", "Structural Analysis", "BIM", "Project Management", "Soil Mechanics", "Construction Management", "SAP2000", "Budget", "Surveying", "Environmental"]},
  {"en": "Pharmacist",               "slug": "pharmacist",              "keywords": ["Pharmaceutical", "Drug Interactions", "Patient Counseling", "Inventory", "Clinical Pharmacy", "Compounding", "Regulatory", "PBM", "Medication Review", "GCP"]},
  {"en": "Chef",                     "slug": "chef",                    "keywords": ["Menu Development", "Food Safety", "HACCP", "Inventory Management", "Staff Training", "Cost Control", "Culinary Arts", "Kitchen Management", "Pastry", "Nutrition"]},
  {"en": "Electrician",              "slug": "electrician",             "keywords": ["Electrical Wiring", "NEC", "PLC", "Safety Compliance", "Troubleshooting", "Blueprint Reading", "AC/DC", "Motor Control", "Conduit", "Industrial Electrical"]},
  {"en": "Real Estate Agent",        "slug": "real-estate-agent",       "keywords": ["CRM", "Negotiation", "Property Valuation", "MLS", "Contract", "Client Relations", "Market Analysis", "Marketing", "Legal Compliance", "Networking"]},
]

TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>AI Resume for {EN_TITLE} — Build in 30 Seconds | ResumeAI</title>
  <meta name="description" content="Create a perfect ATS-optimised resume for {EN_TITLE} with AI. Auto-filled keywords, professional templates, tailored to each job. Free to try." />
  <meta name="robots" content="index, follow" />
  <link rel="canonical" href="https://resumeai-bot.ru/resume/{SLUG}" />
  <meta property="og:type" content="website" />
  <meta property="og:url" content="https://resumeai-bot.ru/resume/{SLUG}" />
  <meta property="og:title" content="AI Resume for {EN_TITLE} — ResumeAI" />
  <meta property="og:description" content="Build a professional {EN_TITLE} resume in 30 seconds with AI optimisation for ATS." />
  <meta property="og:image" content="https://resumeai-bot.ru/og-image.png" />
  <meta property="og:site_name" content="ResumeAI" />
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{{"@type":"ListItem","position":1,"name":"Home","item":"https://resumeai-bot.ru"}},{{"@type":"ListItem","position":2,"name":"Resume","item":"https://resumeai-bot.ru/resume/"}},{{"@type":"ListItem","position":3,"name":"AI Resume for {EN_TITLE}","item":"https://resumeai-bot.ru/resume/{SLUG}"}}]}}
  </script>
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[{{"@type":"Question","name":"How fast does AI generate a {EN_TITLE} resume?","acceptedAnswer":{{"@type":"Answer","text":"AI produces a fully tailored resume in under 30 seconds. Paste the job link and you\\'re done."}}}},{{"@type":"Question","name":"Which keywords matter most for {EN_TITLE}?","acceptedAnswer":{{"@type":"Answer","text":"Top ATS keywords for {EN_TITLE}: {KEYWORDS_STRING}. AI automatically injects the most relevant ones."}}}},{{"@type":"Question","name":"Is building a {EN_TITLE} resume free?","acceptedAnswer":{{"@type":"Answer","text":"Yes — first resume is free, no credit card. Also available via Telegram bot @topbestworkerbot."}}}}]}}
  </script>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
  <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    :root{{--primary:#2563EB;--cta:#F59E0B;--bg:#F8FAFC;--card:#fff;--text:#334155;--heading:#0F172A;--border:#E2E8F0;--radius:12px}}
    body{{font-family:'Inter',-apple-system,sans-serif;background:var(--bg);color:var(--text);line-height:1.6}}
    a{{color:inherit;text-decoration:none}}
    .container{{max-width:1100px;margin:0 auto;padding:0 24px}}
    header{{position:sticky;top:0;z-index:100;background:#fff;border-bottom:1px solid var(--border);padding:0 24px}}
    .header-inner{{max-width:1100px;margin:0 auto;display:flex;align-items:center;justify-content:space-between;height:60px}}
    .logo{{font-size:1.2rem;font-weight:800;color:var(--primary)}}
    .nav-links{{display:flex;gap:24px;font-size:0.9rem;color:var(--text)}}
    .nav-links a:hover{{color:var(--primary)}}
    .btn-signup{{background:var(--cta);color:#fff;padding:8px 20px;border-radius:8px;font-weight:600;font-size:0.88rem}}
    .breadcrumb{{padding:16px 0;font-size:0.82rem;color:#94A3B8}}
    .breadcrumb a{{color:var(--primary)}}
    .breadcrumb span{{margin:0 6px}}
    .page-hero{{background:linear-gradient(135deg,#F8FAFC 0%,#EEF2FF 50%,#F8FAFC 100%);padding:60px 0 48px;border-bottom:1px solid var(--border)}}
    .page-hero h1{{font-size:clamp(1.8rem,4vw,2.8rem);font-weight:800;color:var(--heading);margin-bottom:16px;line-height:1.2}}
    .page-hero p{{font-size:1.1rem;color:#64748B;max-width:600px;margin-bottom:32px}}
    .hero-btns{{display:flex;gap:12px;flex-wrap:wrap}}
    .btn-primary{{background:linear-gradient(135deg,#F59E0B,#D97706);color:#fff;padding:14px 28px;border-radius:var(--radius);font-weight:700;font-size:1rem;display:inline-flex;align-items:center;gap:8px;transition:all .2s;box-shadow:0 4px 14px rgba(245,158,11,.3)}}
    .btn-primary:hover{{transform:translateY(-1px);box-shadow:0 6px 20px rgba(245,158,11,.4)}}
    .btn-telegram{{background:#0088CC;color:#fff;padding:14px 24px;border-radius:var(--radius);font-weight:600;font-size:0.95rem;display:inline-flex;align-items:center;gap:8px}}
    .content-grid{{display:grid;grid-template-columns:2fr 1fr;gap:40px;padding:48px 0}}
    .article h2{{font-size:1.4rem;font-weight:700;color:var(--heading);margin:32px 0 12px}}
    .article h3{{font-size:1.1rem;font-weight:600;color:var(--heading);margin:20px 0 8px}}
    .article p{{margin-bottom:16px;font-size:1rem;line-height:1.7}}
    .article ul{{margin:12px 0 16px 20px}}
    .article ul li{{margin-bottom:8px}}
    .keyword-grid{{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0}}
    .kw-tag{{background:#EEF2FF;color:var(--primary);padding:6px 14px;border-radius:20px;font-size:0.85rem;font-weight:500}}
    .sidebar{{display:flex;flex-direction:column;gap:20px}}
    .sidebar-card{{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:24px;box-shadow:0 4px 12px rgba(0,0,0,.06)}}
    .sidebar-title{{font-weight:700;font-size:0.95rem;color:var(--heading);margin-bottom:12px}}
    .related-link{{display:block;padding:8px 0;border-bottom:1px solid var(--border);font-size:0.88rem;color:var(--primary)}}
    .related-link:last-child{{border-bottom:none}}
    .faq-section{{padding:48px 0;border-top:1px solid var(--border)}}
    .faq-item{{border:1px solid var(--border);border-radius:var(--radius);margin-bottom:12px;overflow:hidden}}
    .faq-q{{padding:18px 20px;font-weight:600;cursor:pointer;display:flex;justify-content:space-between;align-items:center;background:var(--card)}}
    .faq-a{{padding:0 20px;max-height:0;overflow:hidden;transition:.3s ease}}
    .faq-a.open{{max-height:200px;padding:0 20px 16px}}
    .cta-banner{{background:linear-gradient(135deg,#1E40AF,#2563EB);border-radius:16px;padding:40px;text-align:center;color:#fff;margin:40px 0}}
    .cta-banner h2{{font-size:1.6rem;font-weight:800;margin-bottom:12px}}
    .cta-banner p{{opacity:.85;margin-bottom:24px}}
    footer{{background:#0F172A;color:#64748B;padding:40px 0 24px;margin-top:64px}}
    .footer-bottom{{text-align:center;font-size:0.82rem;padding-top:24px;border-top:1px solid #1E293B;margin-top:24px}}
    @media(max-width:768px){{.content-grid{{grid-template-columns:1fr}}.nav-links{{display:none}}.hero-btns{{flex-direction:column}}}}
  </style>
</head>
<body>

<header>
  <div class="header-inner">
    <a href="/" class="logo">ResumeAI</a>
    <nav class="nav-links">
      <a href="/">Home</a>
      <a href="/#pricing">Pricing</a>
      <a href="/blog/">Blog</a>
      <a href="https://t.me/topbestworkerbot" target="_blank">Telegram</a>
    </nav>
    <a href="/app" class="btn-signup">Build your resume</a>
  </div>
</header>

<div class="container">
  <div class="breadcrumb">
    <a href="/">Home</a><span>›</span>
    <a href="/resume/">Resume</a><span>›</span>
    AI Resume for {EN_TITLE}
  </div>
</div>

<div class="page-hero">
  <div class="container">
    <h1>AI Resume for {EN_TITLE}</h1>
    <p>Build a professional, ATS-optimised {EN_TITLE} resume in 30 seconds. Our AI reads the job description and tailors your resume to fit — keywords, format, and all.</p>
    <div class="hero-btns">
      <a href="/app" class="btn-primary">Start free — build your {EN_TITLE} resume →</a>
      <a href="https://t.me/topbestworkerbot" target="_blank" class="btn-telegram">Open in Telegram</a>
    </div>
  </div>
</div>

<div class="container">
  <div class="content-grid">
    <article class="article">
      <h2>What recruiters look for in a {EN_TITLE} resume</h2>
      <p>The job market is more competitive than ever. For {EN_TITLE} roles, recruiters review dozens of resumes per day — and most are filtered out before a human sees them. An ATS-optimised resume dramatically improves your chances of reaching the interview stage.</p>

      <h2>Top 10 ATS keywords for {EN_TITLE}</h2>
      <p>These keywords appear most often in {EN_TITLE} job postings and should be present in your resume:</p>
      <div class="keyword-grid">
        {KEYWORD_TAGS}
      </div>

      <h2>Core skills for {EN_TITLE}</h2>
      <p>Beyond technical skills, employers value soft skills. For {EN_TITLE}, teamwork, time management, communication, and a results-first mindset are consistently valued.</p>
      <ul>
        <li>Technical expertise: {KEYWORDS_0}, {KEYWORDS_1}, {KEYWORDS_2}</li>
        <li>Analytical thinking and structured problem-solving</li>
        <li>Clear communication with teams and stakeholders</li>
        <li>Priority management and deadline delivery</li>
        <li>Commitment to learning and continuous improvement</li>
      </ul>

      <h2>Common mistakes in {EN_TITLE} resumes</h2>
      <p>Most {EN_TITLE} resumes are rejected for the same reasons:</p>
      <ul>
        <li><strong>Missing ATS keywords</strong> — the system filters your resume before a recruiter ever sees it</li>
        <li><strong>Generic phrases</strong> — "team player" and "hard worker" say nothing without concrete examples</li>
        <li><strong>No quantified achievements</strong> — "improved sales" vs "grew revenue 34% in Q3"</li>
        <li><strong>Wrong format</strong> — unreadable PDFs, non-standard fonts, or overly complex layouts</li>
        <li><strong>One resume for every job</strong> — each application deserves a tailored version</li>
      </ul>

      <h2>How AI fixes all of this</h2>
      <p>ResumeAI reads the specific {EN_TITLE} job posting and automatically:</p>
      <ul>
        <li>Injects all required ATS keywords from the job description</li>
        <li>Reframes your experience to match what the role requires</li>
        <li>Optimises structure and formatting for ATS parsers</li>
        <li>Generates a personalised cover letter for each application</li>
        <li>Shows your ATS score with improvement suggestions</li>
      </ul>

      <div class="cta-banner">
        <h2>Build your {EN_TITLE} resume now</h2>
        <p>Free · 30 seconds · ATS-optimised · No credit card</p>
        <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap;">
          <a href="/app" class="btn-primary">Start free →</a>
          <a href="https://t.me/topbestworkerbot" target="_blank" class="btn-telegram">Open in Telegram</a>
        </div>
      </div>
    </article>

    <aside class="sidebar">
      <div class="sidebar-card">
        <div class="sidebar-title">Quick start</div>
        <p style="font-size:.88rem;color:#64748B;margin-bottom:16px;">Build your {EN_TITLE} resume in 30 seconds</p>
        <a href="/app" class="btn-primary" style="width:100%;justify-content:center;font-size:.9rem;">Start free →</a>
        <a href="https://t.me/topbestworkerbot" target="_blank" class="btn-telegram" style="width:100%;justify-content:center;margin-top:10px;font-size:.88rem;">Open in Telegram</a>
      </div>
      <div class="sidebar-card">
        <div class="sidebar-title">ATS keywords</div>
        <div class="keyword-grid">{KEYWORD_TAGS_SMALL}</div>
      </div>
      <div class="sidebar-card">
        <div class="sidebar-title">Related roles</div>
        {RELATED_LINKS}
      </div>
    </aside>
  </div>

  <div class="faq-section">
    <h2 style="font-size:1.6rem;font-weight:800;color:#0F172A;margin-bottom:24px;">Frequently asked questions</h2>
    <div class="faq-item">
      <div class="faq-q" onclick="this.nextElementSibling.classList.toggle(\'open\')">How fast does AI build a {EN_TITLE} resume? <span>+</span></div>
      <div class="faq-a">Under 30 seconds. Paste the job link or description and get a fully tailored DOCX resume ready to send.</div>
    </div>
    <div class="faq-item">
      <div class="faq-q" onclick="this.nextElementSibling.classList.toggle(\'open\')">Which skills are essential for {EN_TITLE}? <span>+</span></div>
      <div class="faq-a">Key skills for {EN_TITLE}: {KEYWORDS_STRING}. AI automatically prioritises the most relevant ones for each specific job posting.</div>
    </div>
    <div class="faq-item">
      <div class="faq-q" onclick="this.nextElementSibling.classList.toggle(\'open\')">Does it work with LinkedIn and Indeed job postings? <span>+</span></div>
      <div class="faq-a">Yes — ResumeAI works with LinkedIn, Indeed, Adzuna, RemoteOK, Greenhouse, Lever, and more. Just paste the job URL or description.</div>
    </div>
    <div class="faq-item">
      <div class="faq-q" onclick="this.nextElementSibling.classList.toggle(\'open\')">Is it really free? <span>+</span></div>
      <div class="faq-a">Yes — your first resume is completely free, no credit card required. Also available via Telegram bot @topbestworkerbot: 3 free auto-applies per day on the free plan.</div>
    </div>
  </div>
</div>

<footer>
  <div class="container">
    <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:24px;margin-bottom:24px;">
      <div><div style="font-size:1.2rem;font-weight:800;color:#F8FAFC;margin-bottom:8px;">ResumeAI</div><div style="font-size:.85rem;">AI-powered career tools for the global job market</div></div>
      <div style="display:flex;gap:40px;flex-wrap:wrap;font-size:.88rem;">
        <div><div style="color:#F8FAFC;font-weight:600;margin-bottom:10px;">Product</div><a href="/app" style="display:block;margin-bottom:6px;color:#64748B;">Resume builder</a><a href="/#pricing" style="display:block;color:#64748B;">Pricing</a></div>
        <div><div style="color:#F8FAFC;font-weight:600;margin-bottom:10px;">Company</div><a href="/blog/" style="display:block;margin-bottom:6px;color:#64748B;">Blog</a><a href="/privacy.html" style="display:block;color:#64748B;">Privacy</a></div>
      </div>
    </div>
    <div class="footer-bottom">© 2026 ResumeAI · <a href="/privacy.html" style="color:#64748B;">Privacy Policy</a> · <a href="https://t.me/topbestworkerbot" target="_blank" style="color:#0088CC;">@topbestworkerbot</a></div>
  </div>
</footer>

</body>
</html>'''

LANDING_DIR = os.path.join(os.path.dirname(__file__), 'landing')
OUT_DIR     = os.path.join(LANDING_DIR, 'resume')
ARCHIVE_DIR = os.path.join(LANDING_DIR, '_archive_ru', 'resume')


def archive_existing_ru_pages() -> int:
    """Move existing RU-language HTML files to _archive_ru/ instead of deleting."""
    if not os.path.isdir(OUT_DIR):
        return 0
    archived = 0
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    for fname in os.listdir(OUT_DIR):
        if not fname.endswith('.html'):
            continue
        src = os.path.join(OUT_DIR, fname)
        dst = os.path.join(ARCHIVE_DIR, fname)
        shutil.move(src, dst)
        archived += 1
    if archived:
        print(f'  Archived {archived} Russian-language pages → landing/_archive_ru/resume/')
    return archived


def main() -> None:
    archive_existing_ru_pages()
    os.makedirs(OUT_DIR, exist_ok=True)

    for i, job in enumerate(JOBS):
        en    = job['en']
        slug  = job['slug']
        kws   = job['keywords']
        kw_str      = ', '.join(kws)
        kw_tags     = '\n        '.join(f'<span class="kw-tag">{k}</span>' for k in kws)
        kw_tags_small = '\n'.join(f'<span class="kw-tag">{k}</span>' for k in kws)

        neighbors = []
        for j in range(max(0, i - 2), min(len(JOBS), i + 4)):
            if j != i:
                neighbors.append(JOBS[j])
        related = '\n        '.join(
            f'<a href="/resume/{n["slug"]}" class="related-link">{n["en"]}</a>'
            for n in neighbors[:5]
        )

        html = TEMPLATE
        html = html.replace('{EN_TITLE}', en)
        html = html.replace('{SLUG}', slug)
        html = html.replace('{KEYWORDS_STRING}', kw_str)
        html = html.replace('{KEYWORD_TAGS}', kw_tags)
        html = html.replace('{KEYWORD_TAGS_SMALL}', kw_tags_small)
        html = html.replace('{KEYWORDS_0}', kws[0])
        html = html.replace('{KEYWORDS_1}', kws[1])
        html = html.replace('{KEYWORDS_2}', kws[2])
        html = html.replace('{RELATED_LINKS}', related)

        path = os.path.join(OUT_DIR, f'{slug}.html')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'  [{i + 1}/{len(JOBS)}] {path}')

    print(f'\nDone — {len(JOBS)} English SEO pages written to landing/resume/')


if __name__ == '__main__':
    main()
