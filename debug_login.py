import os
from playwright.sync_api import sync_playwright

def main():
    cookie_file = "cookie.txt"
    if not os.path.exists(cookie_file):
        print("cookie.txt not found!")
        return
        
    with open(cookie_file, "r") as f:
        cookie_val = f.read().strip()
        
    print(f"Loaded cookie (length {len(cookie_val)})")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        
        # Try injecting with .linkedin.com
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
        print("Navigating to https://www.linkedin.com/feed/ ...")
        page.goto("https://www.linkedin.com/feed/", wait_until="networkidle")
        page.wait_for_timeout(3000)
        
        print("Current URL:", page.url)
        screenshot_path = "login_debug.png"
        page.screenshot(path=screenshot_path)
        print(f"Screenshot saved to {screenshot_path}")
        
        browser.close()

if __name__ == "__main__":
    main()
