#!/usr/bin/env python3
"""
twitter_poster.py — Posts daily career tips to Twitter/X at 14:00 UTC.
Requires: TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET
"""
import os
import random
from datetime import datetime

TWITTER_API_KEY         = os.getenv("TWITTER_API_KEY", "")
TWITTER_API_SECRET      = os.getenv("TWITTER_API_SECRET", "")
TWITTER_ACCESS_TOKEN    = os.getenv("TWITTER_ACCESS_TOKEN", "")
TWITTER_ACCESS_SECRET   = os.getenv("TWITTER_ACCESS_SECRET", "")

TIPS = [
    "75% of resumes are rejected by ATS before a human sees them.\n\nFix: tailor keywords to each job description.\n\nResumeAI does this automatically for every application. 🤖\n\nhttps://t.me/topbestworkerbot",
    "Sending 3 job applications/day won't get you hired.\n\nThe math: 3 apps × 5% response rate = 0.15 responses/day.\n\nAt 50 apps/day with AI automation → 2-3 responses per day.\n\nhttps://t.me/topbestworkerbot",
    "Most job seekers spend 45 min per application.\n\nAt that rate: 10 apps = 7.5 hours of manual work.\n\nAutomate the repetitive parts. Use those 7.5 hours to prep for interviews.\n\nhttps://t.me/topbestworkerbot",
    "LinkedIn Easy Apply tip: the first 200 applicants get 80% of recruiter attention.\n\nApply within hours of posting, not days.\n\nAI auto-apply bots monitor job boards 24/7 so you're always first. ⚡\n\nhttps://t.me/topbestworkerbot",
    "The average job search takes 5 months.\n\nMost people quit after 2-3 weeks of silence.\n\nVolume + consistency wins. Not talent. Not luck.\n\nhttps://t.me/topbestworkerbot",
    "Greenhouse, Lever, Workable — 3 ATS platforms that power 60% of tech job applications.\n\nThey all have the same form structure.\n\nOnce you auto-fill one, you auto-fill all of them. 🎯\n\nhttps://t.me/topbestworkerbot",
    "Job search tip: apply Monday–Wednesday morning.\n\nRecruiters review apps at the start of the week.\n\nApplications submitted Friday afternoon sit until next week.\n\nhttps://t.me/topbestworkerbot",
    "Your cover letter is read for 7 seconds on average.\n\nMake line 1 count: 'I built X that did Y — here's how I'd do that at [Company].'\n\nAI can generate this for every single application.\n\nhttps://t.me/topbestworkerbot",
]


def _post_tweet(text: str) -> bool:
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET]):
        print("[twitter_poster] Twitter credentials not set — skipping")
        return False
    try:
        import tweepy  # type: ignore
        client = tweepy.Client(
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_SECRET,
        )
        response = client.create_tweet(text=text)
        tweet_id = response.data["id"] if response.data else "unknown"
        print(f"[twitter_poster] Posted tweet {tweet_id}")
        return True
    except Exception as e:
        print(f"[twitter_poster] Error: {e}")
        return False


def run_twitter_poster() -> None:
    tip = random.choice(TIPS)
    print(f"[twitter_poster] Posting at {datetime.utcnow().isoformat()}")
    _post_tweet(tip)


if __name__ == "__main__":
    run_twitter_poster()
