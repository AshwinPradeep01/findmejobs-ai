import os
from playwright.sync_api import sync_playwright

def main():
    cookie_file = "cookie.txt"
    if not os.path.exists(cookie_file):
        print("cookie.txt not found!")
        return
        
    with open(cookie_file, "r") as f:
        cookie_val = f.read().strip()
        
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        
        context.add_cookies([
            {
                "name": "li_at",
                "value": cookie_val,
                "domain": ".linkedin.com",
                "path": "/",
                "secure": True,
                "httpOnly": True,
                "sameSite": "None"
            }
        ])
        
        page = context.new_page()
        
        # Step 1: Go to Feed
        print("Step 1: Navigating to feed...")
        try:
            page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            print("Feed URL:", page.url)
            page.screenshot(path="step1_feed.png")
        except Exception as e:
            print("Step 1 failed:", e)
            
        # Step 2: Go to Jobs main page
        print("\nStep 2: Navigating to jobs page...")
        try:
            page.goto("https://www.linkedin.com/jobs/", wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            print("Jobs URL:", page.url)
            page.screenshot(path="step2_jobs.png")
        except Exception as e:
            print("Step 2 failed:", e)

        # Step 3: Go to Job Search
        print("\nStep 3: Navigating to job search...")
        try:
            page.goto("https://www.linkedin.com/jobs/search/?keywords=Software%20Engineer&location=United%20States", wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            print("Search URL:", page.url)
            page.screenshot(path="step3_search.png")
        except Exception as e:
            print("Step 3 failed:", e)
            
        browser.close()

if __name__ == "__main__":
    main()
