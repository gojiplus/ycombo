#!/usr/bin/env python3
import os
import random
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

GITHUB_API = "https://api.github.com"
USERNAME   = os.getenv("GITHUB_USERNAME")
ORGS       = os.getenv("GITHUB_ORGS", "")
TOKEN      = os.getenv("GITHUB_TOKEN")
HN_COOKIE  = os.getenv("HN_USER_COOKIE")

HEADERS = {
    "Accept": "application/vnd.github+json",
    **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {})
}

# --- Step 1: Fetch repos ---
def fetch_repos(user_or_org):
    url = f"{GITHUB_API}/users/{user_or_org}/repos?per_page=100&type=public"
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    return r.json()

def pick_repo():
    all_repos = fetch_repos(USERNAME)
    for org in [o.strip() for o in ORGS.split(",") if o.strip()]:
        all_repos += fetch_repos(org)
    filtered = [r for r in all_repos if r.get("stargazers_count", 0) >= 5]
    return random.choice(filtered)

# --- Step 2: Generate post text ---
def make_title(repo):
    name = repo["name"]
    desc = repo.get("description") or "An open-source tool."
    return f"{name} - {desc[:200]}"

# --- Step 3: Post via Playwright ---
def post_to_hn(title, url):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()

        # Inject HN login cookie
        context.add_cookies([
            {
                "name": "user",
                "value": HN_COOKIE,
                "domain": "news.ycombinator.com",
                "path": "/",
                "httpOnly": True,
                "secure": True
            }
        ])

        page = context.new_page()
        page.goto("https://news.ycombinator.com/submit")

        # Fill in the form
        page.fill("input[name='title']", title)
        page.fill("input[name='url']", url)

        # Submit it
        page.click("input[type='submit']")

        print("✅ Submitted to Hacker News:", title)

if __name__ == "__main__":
    repo = pick_repo()
    hn_title = make_title(repo)
    post_to_hn(hn_title, repo["html_url"])
