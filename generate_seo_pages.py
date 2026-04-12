#!/usr/bin/env python3
import os

jobs = [
  {"en":"Software Engineer","ru":"Программист","slug":"software-engineer","keywords":["Python","Java","Git","Docker","SQL","REST API","Agile","CI/CD","Linux","Microservices"]},
  {"en":"Product Manager","ru":"Продуктовый менеджер","slug":"product-manager","keywords":["Roadmap","Agile","Scrum","Stakeholder","KPI","A/B тестирование","Jira","User Story","Метрики","MVP"]},
  {"en":"Data Analyst","ru":"Аналитик данных","slug":"data-analyst","keywords":["SQL","Python","Excel","Tableau","Power BI","Statistics","A/B тест","ETL","Data Warehouse","Pandas"]},
  {"en":"UX Designer","ru":"UX Дизайнер","slug":"ux-designer","keywords":["Figma","Prototyping","User Research","Wireframing","Usability","Design System","A/B тест","CSS","Accessibility","UX Writing"]},
  {"en":"Marketing Manager","ru":"Маркетинг менеджер","slug":"marketing-manager","keywords":["SEO","SMM","Google Ads","Яндекс.Директ","Email маркетинг","KPI","ROI","CRM","Analytics","Content"]},
  {"en":"Sales Manager","ru":"Менеджер по продажам","slug":"sales-manager","keywords":["B2B","CRM","Cold Calling","KPI","Pipeline","Salesforce","Negotiation","Lead Generation","Upsell","Revenue"]},
  {"en":"Project Manager","ru":"Проджект менеджер","slug":"project-manager","keywords":["Agile","Scrum","PMP","Jira","Confluence","Risk Management","Stakeholder","Roadmap","Budget","PMO"]},
  {"en":"DevOps Engineer","ru":"DevOps инженер","slug":"devops-engineer","keywords":["Kubernetes","Docker","CI/CD","Terraform","AWS","Linux","Ansible","Jenkins","Monitoring","Git"]},
  {"en":"Frontend Developer","ru":"Фронтенд разработчик","slug":"frontend-developer","keywords":["React","TypeScript","JavaScript","CSS","HTML","Vue.js","Webpack","REST API","Testing","Git"]},
  {"en":"Backend Developer","ru":"Бэкенд разработчик","slug":"backend-developer","keywords":["Python","Node.js","Java","SQL","PostgreSQL","Redis","Docker","REST API","Microservices","Git"]},
  {"en":"Full Stack Developer","ru":"Фулстек разработчик","slug":"fullstack-developer","keywords":["React","Node.js","Python","PostgreSQL","Docker","TypeScript","REST API","Git","AWS","Redis"]},
  {"en":"QA Engineer","ru":"QA Инженер","slug":"qa-engineer","keywords":["Selenium","TestNG","Jira","API Testing","Automation","SQL","Postman","Load Testing","Python","CI/CD"]},
  {"en":"Business Analyst","ru":"Бизнес аналитик","slug":"business-analyst","keywords":["SQL","BPMN","Requirements","Use Cases","Jira","Confluence","Stakeholder","Excel","Visio","Agile"]},
  {"en":"HR Manager","ru":"HR Менеджер","slug":"hr-manager","keywords":["Recruiting","Onboarding","HRIS","KPI","Employee Relations","Training","Performance Review","Compensation","Labor Law","ATS"]},
  {"en":"Accountant","ru":"Бухгалтер","slug":"accountant","keywords":["1С","Налоговая отчётность","МСФО","Excel","Бухгалтерский учёт","Аудит","Payroll","Финансовая отчётность","Балансовый отчёт","ERP"]},
  {"en":"Graphic Designer","ru":"Графический дизайнер","slug":"graphic-designer","keywords":["Photoshop","Illustrator","InDesign","Figma","Branding","Typography","Layout","Print","UI Design","After Effects"]},
  {"en":"Content Writer","ru":"Копирайтер","slug":"content-writer","keywords":["SEO","Copywriting","WordPress","Content Strategy","Social Media","Editing","Research","Keywords","Analytics","CMS"]},
  {"en":"Customer Support","ru":"Менеджер поддержки","slug":"customer-support","keywords":["CRM","Zendesk","Customer Service","SLA","Ticketing","Communication","KPI","Escalation","Product Knowledge","NPS"]},
  {"en":"System Administrator","ru":"Системный администратор","slug":"system-administrator","keywords":["Windows Server","Linux","Active Directory","Virtualization","Networking","Security","Backup","DNS","VMware","PowerShell"]},
  {"en":"Financial Analyst","ru":"Финансовый аналитик","slug":"financial-analyst","keywords":["Excel","Financial Modeling","DCF","Valuation","Bloomberg","SQL","МСФО","Budget","Forecasting","PowerPoint"]},
  {"en":"Data Scientist","ru":"Data Scientist","slug":"data-scientist","keywords":["Python","Machine Learning","TensorFlow","Pandas","SQL","Statistics","NLP","Computer Vision","Jupyter","Scikit-learn"]},
  {"en":"Machine Learning Engineer","ru":"ML Инженер","slug":"ml-engineer","keywords":["Python","TensorFlow","PyTorch","MLOps","Docker","SQL","NLP","Computer Vision","Kubernetes","Feature Engineering"]},
  {"en":"iOS Developer","ru":"iOS Разработчик","slug":"ios-developer","keywords":["Swift","SwiftUI","Xcode","UIKit","Core Data","REST API","Combine","TestFlight","Firebase","Git"]},
  {"en":"Android Developer","ru":"Android Разработчик","slug":"android-developer","keywords":["Kotlin","Java","Android Studio","Jetpack Compose","REST API","Firebase","Room","MVVM","Coroutines","Git"]},
  {"en":"Cybersecurity Analyst","ru":"Аналитик по кибербезопасности","slug":"cybersecurity-analyst","keywords":["SIEM","Penetration Testing","CISSP","Firewall","Network Security","Vulnerability Assessment","ISO 27001","SOC","Python","IDS/IPS"]},
  {"en":"Cloud Engineer","ru":"Cloud Инженер","slug":"cloud-engineer","keywords":["AWS","Azure","GCP","Terraform","Kubernetes","Docker","CI/CD","IaC","Security","Networking"]},
  {"en":"Technical Writer","ru":"Технический писатель","slug":"technical-writer","keywords":["Documentation","Markdown","API Docs","DITA","Confluence","Git","XML","Technical Communication","UX Writing","Swagger"]},
  {"en":"UI Designer","ru":"UI Дизайнер","slug":"ui-designer","keywords":["Figma","Design System","CSS","Prototyping","Typography","Color Theory","Responsive Design","Accessibility","Adobe XD","Sketch"]},
  {"en":"Scrum Master","ru":"Scrum мастер","slug":"scrum-master","keywords":["Scrum","Agile","Jira","Kanban","Retrospectives","Sprint Planning","Coaching","SAFe","Confluence","Facilitation"]},
  {"en":"Supply Chain Manager","ru":"Менеджер по логистике","slug":"supply-chain-manager","keywords":["SAP","ERP","Logistics","Procurement","Inventory","Forecasting","Vendor Management","KPI","Excel","LEAN"]},
  {"en":"Teacher","ru":"Учитель","slug":"teacher","keywords":["Педагогика","Методология","Дифференцированный подход","ФГОС","Curriculum","ЕГЭ","Classroom Management","E-learning","Moodle","Google Classroom"]},
  {"en":"Nurse","ru":"Медсестра","slug":"nurse","keywords":["Patient Care","Medical Records","IV Therapy","Vital Signs","EHR","ACLS","BLS","Medication Administration","ICU","Triage"]},
  {"en":"Lawyer","ru":"Юрист","slug":"lawyer","keywords":["Contract Law","Litigation","Legal Research","Due Diligence","Corporate Law","Compliance","Arbitration","Legal Writing","IP Law","Labor Law"]},
  {"en":"Architect","ru":"Архитектор","slug":"architect","keywords":["AutoCAD","Revit","BIM","ArchiCAD","3D Modeling","Building Codes","Project Management","Structural Design","Urban Planning","Sustainability"]},
  {"en":"Mechanical Engineer","ru":"Инженер-механик","slug":"mechanical-engineer","keywords":["AutoCAD","SolidWorks","ANSYS","CAD","Manufacturing","FEA","Thermodynamics","CNC","Materials Science","ISO Standards"]},
  {"en":"Civil Engineer","ru":"Инженер-строитель","slug":"civil-engineer","keywords":["AutoCAD","Structural Analysis","BIM","Project Management","Soil Mechanics","Construction Management","SAP2000","Budget","Surveying","Environmental"]},
  {"en":"Pharmacist","ru":"Фармацевт","slug":"pharmacist","keywords":["Pharmaceutical","Drug Interactions","Patient Counseling","Inventory","Clinical Pharmacy","Compounding","Regulatory","PBM","Medication Review","GCP"]},
  {"en":"Chef","ru":"Шеф-повар","slug":"chef","keywords":["Menu Development","Food Safety","HACCP","Inventory Management","Staff Training","Cost Control","Culinary Arts","Kitchen Management","Pastry","Nutrition"]},
  {"en":"Electrician","ru":"Электрик","slug":"electrician","keywords":["Electrical Wiring","NEC","PLC","Safety Compliance","Troubleshooting","Blueprint Reading","AC/DC","Motor Control","Conduit","Industrial Electrical"]},
  {"en":"Real Estate Agent","ru":"Риелтор","slug":"real-estate-agent","keywords":["CRM","Negotiation","Property Valuation","MLS","Contract","Client Relations","Market Analysis","Marketing","Legal Compliance","Networking"]},
]

TEMPLATE = '''<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>AI Резюме для {RU_TITLE} — Создать за 30 секунд | РезюмеАИ</title>
  <meta name="description" content="Создайте идеальное резюме для должности {RU_TITLE} с помощью AI. ATS-оптимизация, ключевые слова, профессиональные шаблоны. Бесплатно за 30 секунд." />
  <meta name="robots" content="index, follow" />
  <link rel="canonical" href="https://resumeai-bot.ru/resume/{SLUG}" />
  <meta property="og:type" content="website" />
  <meta property="og:url" content="https://resumeai-bot.ru/resume/{SLUG}" />
  <meta property="og:title" content="AI Резюме для {RU_TITLE} — РезюмеАИ" />
  <meta property="og:description" content="Создайте профессиональное резюме для {RU_TITLE} за 30 секунд с AI-оптимизацией." />
  <meta property="og:image" content="https://resumeai-bot.ru/og-image.png" />
  <meta property="og:site_name" content="РезюмеАИ" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{{"@type":"ListItem","position":1,"name":"Главная","item":"https://resumeai-bot.ru"}},{{"@type":"ListItem","position":2,"name":"Резюме","item":"https://resumeai-bot.ru/resume/"}},{{"@type":"ListItem","position":3,"name":"AI Резюме для {RU_TITLE}","item":"https://resumeai-bot.ru/resume/{SLUG}"}}]}}
  </script>
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[{{"@type":"Question","name":"Как быстро AI создаёт резюме для {RU_TITLE}?","acceptedAnswer":{{"@type":"Answer","text":"AI создаёт адаптированное резюме за 30 секунд. Просто вставьте ссылку на вакансию."}}}},{{"@type":"Question","name":"Какие ключевые навыки важны для {RU_TITLE}?","acceptedAnswer":{{"@type":"Answer","text":"Для {RU_TITLE} важны: {KEYWORDS_STRING}. AI автоматически включает релевантные навыки."}}}},{{"@type":"Question","name":"Бесплатно ли создание резюме для {RU_TITLE}?","acceptedAnswer":{{"@type":"Answer","text":"Да, первое резюме бесплатно. Также доступно через Telegram бот @topbestworkerbot."}}}}]}}
  </script>
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
      <a href="/">Главная</a>
      <a href="/#pricing">Тарифы</a>
      <a href="/blog/">Блог</a>
      <a href="https://t.me/topbestworkerbot" target="_blank">Telegram</a>
    </nav>
    <a href="/app" class="btn-signup">Создать резюме</a>
  </div>
</header>

<div class="container">
  <div class="breadcrumb">
    <a href="/">Главная</a><span>›</span>
    <a href="/resume/">Резюме</a><span>›</span>
    AI Резюме для {RU_TITLE}
  </div>
</div>

<div class="page-hero">
  <div class="container">
    <h1>AI Резюме для {RU_TITLE}</h1>
    <p>Создайте профессиональное, ATS-оптимизированное резюме для позиции {RU_TITLE} за 30 секунд. Наш AI анализирует вакансию и адаптирует резюме под конкретные требования.</p>
    <div class="hero-btns">
      <a href="/app" class="btn-primary">Создать резюме {RU_TITLE} бесплатно →</a>
      <a href="https://t.me/topbestworkerbot" target="_blank" class="btn-telegram">💬 Или попробуй в Telegram</a>
    </div>
  </div>
</div>

<div class="container">
  <div class="content-grid">
    <article class="article">
      <h2>Что работодатели ищут в резюме {RU_TITLE}</h2>
      <p>Рынок труда становится всё более конкурентным. Для позиции {RU_TITLE} рекрутеры ежедневно просматривают десятки резюме — и большинство из них отсеиваются ещё на этапе ATS-фильтрации. Правильно составленное резюме увеличивает шансы на приглашение на собеседование в 3 раза.</p>

      <h2>Топ-10 ATS-ключей для {RU_TITLE}</h2>
      <p>Эти ключевые слова чаще всего встречаются в вакансиях {RU_TITLE} и должны присутствовать в вашем резюме:</p>
      <div class="keyword-grid">
        {KEYWORD_TAGS}
      </div>

      <h2>Ключевые навыки для позиции {RU_TITLE}</h2>
      <p>Помимо технических навыков, рекрутеры обращают внимание на soft skills. Для {RU_TITLE} особенно важны: умение работать в команде, управление временем, коммуникабельность и ориентация на результат.</p>
      <ul>
        <li>Технические компетенции: {KEYWORDS_0}, {KEYWORDS_1}, {KEYWORDS_2}</li>
        <li>Аналитическое мышление и решение проблем</li>
        <li>Коммуникация с командой и стейкхолдерами</li>
        <li>Управление приоритетами и дедлайнами</li>
        <li>Готовность к обучению и развитию</li>
      </ul>

      <h2>Частые ошибки в резюме {RU_TITLE}</h2>
      <p>Большинство резюме для позиции {RU_TITLE} отклоняются по одним и тем же причинам:</p>
      <ul>
        <li><strong>Нет ключевых слов из вакансии</strong> — ATS не находит соответствие и отсеивает резюме автоматически</li>
        <li><strong>Общие фразы</strong> — "ответственный", "коммуникабельный" без конкретных примеров ничего не говорят рекрутеру</li>
        <li><strong>Не указаны достижения с цифрами</strong> — "увеличил продажи" vs "увеличил продажи на 34% за квартал"</li>
        <li><strong>Неправильный формат</strong> — нечитаемый PDF, нестандартные шрифты, сложная структура</li>
        <li><strong>Одно резюме на все вакансии</strong> — каждая вакансия требует адаптации</li>
      </ul>

      <h2>Как AI решает эти проблемы</h2>
      <p>РезюмеАИ анализирует конкретную вакансию {RU_TITLE} и автоматически:</p>
      <ul>
        <li>Включает все нужные ATS-ключевые слова из описания вакансии</li>
        <li>Переформулирует ваш опыт под требования конкретной позиции</li>
        <li>Оптимизирует структуру и форматирование для ATS-систем</li>
        <li>Генерирует персональное сопроводительное письмо</li>
        <li>Показывает ATS-скор и рекомендации по улучшению</li>
      </ul>

      <div class="cta-banner">
        <h2>Создайте резюме {RU_TITLE} прямо сейчас</h2>
        <p>Бесплатно · 30 секунд · ATS-оптимизация · Без кредитной карты</p>
        <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap;">
          <a href="/app" class="btn-primary">Создать резюме бесплатно →</a>
          <a href="https://t.me/topbestworkerbot" target="_blank" class="btn-telegram">💬 В Telegram</a>
        </div>
      </div>
    </article>

    <aside class="sidebar">
      <div class="sidebar-card">
        <div class="sidebar-title">⚡ Быстрый старт</div>
        <p style="font-size:.88rem;color:#64748B;margin-bottom:16px;">Создайте резюме {RU_TITLE} за 30 секунд</p>
        <a href="/app" class="btn-primary" style="width:100%;justify-content:center;font-size:.9rem;">Создать бесплатно →</a>
        <a href="https://t.me/topbestworkerbot" target="_blank" class="btn-telegram" style="width:100%;justify-content:center;margin-top:10px;font-size:.88rem;">💬 В Telegram</a>
      </div>
      <div class="sidebar-card">
        <div class="sidebar-title">🔑 ATS-ключевые слова</div>
        <div class="keyword-grid">{KEYWORD_TAGS_SMALL}</div>
      </div>
      <div class="sidebar-card">
        <div class="sidebar-title">📄 Похожие профессии</div>
        {RELATED_LINKS}
      </div>
    </aside>
  </div>

  <div class="faq-section">
    <h2 style="font-size:1.6rem;font-weight:800;color:#0F172A;margin-bottom:24px;">Частые вопросы</h2>
    <div class="faq-item">
      <div class="faq-q" onclick="this.nextElementSibling.classList.toggle(\'open\')">Как быстро AI создаёт резюме для {RU_TITLE}? <span>+</span></div>
      <div class="faq-a">AI создаёт полностью адаптированное резюме за 30 секунд. Вставьте ссылку на вакансию или её текст — и получите готовый документ в формате DOCX.</div>
    </div>
    <div class="faq-item">
      <div class="faq-q" onclick="this.nextElementSibling.classList.toggle(\'open\')">Какие навыки обязательны для {RU_TITLE}? <span>+</span></div>
      <div class="faq-a">Для позиции {RU_TITLE} ключевые навыки: {KEYWORDS_STRING}. AI автоматически включает наиболее релевантные навыки из конкретной вакансии.</div>
    </div>
    <div class="faq-item">
      <div class="faq-q" onclick="this.nextElementSibling.classList.toggle(\'open\')">Работает ли сервис с вакансиями на hh.ru? <span>+</span></div>
      <div class="faq-a">Да, РезюмеАИ работает с вакансиями на hh.ru, SuperJob, LinkedIn, Indeed и других платформах. Просто вставьте ссылку.</div>
    </div>
    <div class="faq-item">
      <div class="faq-q" onclick="this.nextElementSibling.classList.toggle(\'open\')">Это действительно бесплатно? <span>+</span></div>
      <div class="faq-a">Первое резюме полностью бесплатно — без кредитной карты. Также доступно через Telegram бот @topbestworkerbot: 1 резюме + 1 письмо + 3 AI-сообщения бесплатно.</div>
    </div>
  </div>
</div>

<footer>
  <div class="container">
    <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:24px;margin-bottom:24px;">
      <div><div style="font-size:1.2rem;font-weight:800;color:#F8FAFC;margin-bottom:8px;">ResumeAI</div><div style="font-size:.85rem;">AI-карьерный помощник нового поколения</div></div>
      <div style="display:flex;gap:40px;flex-wrap:wrap;font-size:.88rem;">
        <div><div style="color:#F8FAFC;font-weight:600;margin-bottom:10px;">Продукт</div><a href="/app" style="display:block;margin-bottom:6px;color:#64748B;">Конструктор резюме</a><a href="/#pricing" style="display:block;color:#64748B;">Тарифы</a></div>
        <div><div style="color:#F8FAFC;font-weight:600;margin-bottom:10px;">Компания</div><a href="/blog/" style="display:block;margin-bottom:6px;color:#64748B;">Блог</a><a href="/privacy.html" style="display:block;color:#64748B;">Политика</a></div>
      </div>
    </div>
    <div class="footer-bottom">© 2026 РезюмеАИ · <a href="/privacy.html" style="color:#64748B;">Конфиденциальность</a> · <a href="https://t.me/topbestworkerbot" target="_blank" style="color:#0088CC;">@topbestworkerbot</a></div>
  </div>
</footer>

</body>
</html>'''

out_dir = '/Users/maksimabramov/resume-ai-bot/landing/resume'
os.makedirs(out_dir, exist_ok=True)

for i, job in enumerate(jobs):
    ru = job['ru']
    slug = job['slug']
    kws = job['keywords']
    kw_str = ', '.join(kws)
    kw_tags = '\n        '.join(f'<span class="kw-tag">{k}</span>' for k in kws)
    kw_tags_small = '\n'.join(f'<span class="kw-tag">{k}</span>' for k in kws)

    # Related links: 4-5 neighbors
    neighbors = []
    for j in range(max(0, i-2), min(len(jobs), i+4)):
        if j != i:
            neighbors.append(jobs[j])
    related = '\n        '.join(
        f'<a href="/resume/{n["slug"]}" class="related-link">{n["ru"]}</a>'
        for n in neighbors[:5]
    )

    html = TEMPLATE
    html = html.replace('{RU_TITLE}', ru)
    html = html.replace('{SLUG}', slug)
    html = html.replace('{KEYWORDS_STRING}', kw_str)
    html = html.replace('{KEYWORD_TAGS}', kw_tags)
    html = html.replace('{KEYWORD_TAGS_SMALL}', kw_tags_small)
    html = html.replace('{KEYWORDS_0}', kws[0])
    html = html.replace('{KEYWORDS_1}', kws[1])
    html = html.replace('{KEYWORDS_2}', kws[2])
    html = html.replace('{RELATED_LINKS}', related)

    path = os.path.join(out_dir, f'{slug}.html')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'  [{i+1}/40] {path}')

print(f'\nDone! {len(jobs)} files written to {out_dir}')
