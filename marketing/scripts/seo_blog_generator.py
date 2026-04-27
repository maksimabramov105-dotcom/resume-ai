#!/usr/bin/env python3
"""
SEO blog generator — runs daily at 06:00 UTC.
Writes a new blog post targeting a keyword from the rotation list.
Saves as JSON to BLOG_DIR for Next.js to serve statically.
"""
import os
import json
import random
import hashlib
from datetime import datetime
from openai import OpenAI

_openai_key = os.getenv('OPENAI_API_KEY')
_openrouter_key = os.getenv('OPENROUTER_API_KEY')
if _openai_key:
    client = OpenAI(api_key=_openai_key)
else:
    client = OpenAI(api_key=_openrouter_key, base_url='https://openrouter.ai/api/v1')

BLOG_DIR = os.getenv('BLOG_DIR', 'public/blog')
os.makedirs(BLOG_DIR, exist_ok=True)

KEYWORDS = [
    "how to auto apply for jobs", "job application automation 2025",
    "best job application bots", "automate job search linkedin",
    "greenhouse form autofill chrome extension", "lever job application auto fill",
    "how to apply to 100 jobs per day", "job search automation reddit",
    "ai resume tailoring tool", "ats resume optimization tool",
    "how to get more job interviews", "job application tracker free",
    "auto apply jobs indeed", "workable application autofill",
    "how to beat ats systems", "resume keyword optimization",
    "job hunting productivity tools 2025", "linkedin easy apply automation",
    "smartrecruiters auto fill", "ashby ats job application tips",
    "how to apply for remote jobs automatically", "ai cover letter generator free",
    "job application follow up automation", "best resume parser tools",
    "how to apply to 50 jobs a day", "software engineer job search strategy",
    "data scientist job application tips", "product manager job automation",
    "job search mental health burnout", "how long does job search take",
]

USED_FILE = os.path.join(BLOG_DIR, '_used_keywords.json')


def get_next_keyword():
    used = []
    if os.path.exists(USED_FILE):
        with open(USED_FILE) as f:
            used = json.load(f)
    available = [k for k in KEYWORDS if k not in used]
    if not available:
        used = []
        available = KEYWORDS[:]
    keyword = random.choice(available)
    used.append(keyword)
    with open(USED_FILE, 'w') as f:
        json.dump(used, f)
    return keyword


def generate_post(keyword):
    prompt = f"""Write a helpful, practical blog post targeting this SEO keyword: "{keyword}"

Requirements:
- 800-1000 words
- Title: H1 that naturally includes the keyword
- 4-5 H2 subheadings
- Conversational but authoritative tone
- Include 1-2 mentions of "ResumeAI Bot" as a tool that helps with this (natural, not spammy)
- End with a CTA: "Try ResumeAI Bot free at t.me/topbestworkerbot"
- Return valid JSON: {{"title": "...", "slug": "...", "meta_description": "...(150 chars)", "content_html": "...full HTML..."}}
- Slug: lowercase, hyphens only, 4-6 words from the keyword
"""
    response = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[{'role': 'user', 'content': prompt}],
        response_format={'type': 'json_object'},
        temperature=0.7,
    )
    return json.loads(response.choices[0].message.content)


def save_post(post_data, keyword):
    slug = post_data.get('slug') or hashlib.md5(keyword.encode()).hexdigest()[:8]
    post_data['keyword'] = keyword
    post_data['published_at'] = datetime.utcnow().isoformat()
    post_data['author'] = 'ResumeAI Team'
    filename = f"{datetime.utcnow().strftime('%Y-%m-%d')}-{slug}.json"
    filepath = os.path.join(BLOG_DIR, filename)
    with open(filepath, 'w') as f:
        json.dump(post_data, f, ensure_ascii=False, indent=2)
    print(f"Saved: {filepath}")

    index_path = os.path.join(BLOG_DIR, 'index.json')
    index = []
    if os.path.exists(index_path):
        with open(index_path) as f:
            index = json.load(f)
    index.insert(0, {
        'slug': slug,
        'title': post_data.get('title', ''),
        'meta_description': post_data.get('meta_description', ''),
        'published_at': post_data['published_at'],
        'filename': filename,
    })
    with open(index_path, 'w') as f:
        json.dump(index[:50], f, ensure_ascii=False, indent=2)
    print(f"Index updated: {len(index)} posts")


def main():
    keyword = get_next_keyword()
    print(f"Generating post for: {keyword}")
    post = generate_post(keyword)
    save_post(post, keyword)
    print("Done.")


if __name__ == '__main__':
    main()
