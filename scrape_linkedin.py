import os
import sys
import csv
import sqlite3
import datetime
from playwright.sync_api import sync_playwright

DB_PATH = "jobs.db"
CSV_PATH = "jobs.csv"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            title TEXT,
            company TEXT,
            location TEXT,
            url TEXT,
            date_posted TEXT,
            salary TEXT,
            employment_type TEXT,
            work_mode TEXT,
            description TEXT,
            scraped_at TEXT
        )
    """)
    # Migration: add work_mode column if database already existed without it
    try:
        cursor.execute("ALTER TABLE jobs ADD COLUMN work_mode TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass
    conn.close()

def save_to_db(job):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO jobs 
        (job_id, title, company, location, url, date_posted, salary, employment_type, work_mode, description, scraped_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        job["job_id"],
        job["title"],
        job["company"],
        job["location"],
        job["url"],
        job["date_posted"],
        job["salary"],
        job["employment_type"],
        job["work_mode"],
        job["description"],
        job["scraped_at"]
    ))
    conn.commit()
    conn.close()

def save_to_csv(job):
    file_exists = os.path.exists(CSV_PATH)
    fieldnames = ["job_id", "title", "company", "location", "url", "date_posted", "salary", "employment_type", "work_mode", "description", "scraped_at"]
    
    with open(CSV_PATH, mode="a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(job)

def check_login(page):
    """
    Check if the user is logged in.
    """
    print("Checking authentication status...")
    try:
        page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        current_url = page.url
        print(f"Current URL during auth check: {current_url}")
        if "login" in current_url or "signup" in current_url or "checkpoint" in current_url:
            return False
        return True
    except Exception as e:
        print(f"Error checking auth status: {e}")
        return False

def scrape_job_details(page, job_id):
    """
    Scrapes the details of the currently clicked job card on the right panel.
    """
    page.wait_for_timeout(2000)
    
    # 1. Title
    title = ""
    title_selectors = [
        ".job-details-jobs-unified-top-card__job-title h1 a",
        ".job-details-jobs-unified-top-card__job-title h1",
        "h1.t-24",
        "h1",
        "h2.jobs-unified-top-card__job-title",
        ".jobs-unified-top-card__job-title",
        ".job-details-jobs-unified-top-card__title",
        "h2"
    ]
    for sel in title_selectors:
        el = page.locator(sel)
        if el.count() > 0:
            title = el.first.inner_text().strip()
            if title:
                break
    if not title:
        title = "Unknown Title"

    # 2. Company
    company = ""
    company_selectors = [
        ".job-details-jobs-unified-top-card__company-name a",
        ".job-details-jobs-unified-top-card__company-name",
        ".jobs-unified-top-card__company-name a[href*='/company/']",
        ".job-details-jobs-unified-top-card__company-name a[href*='/company/']",
        ".jobs-unified-top-card__company-name a",
        ".jobs-unified-top-card__company-name",
        ".jobs-details-top-card__company-info a",
        "a[href*='/company/']"
    ]
    for sel in company_selectors:
        el = page.locator(sel)
        if el.count() > 0:
            company = el.first.inner_text().strip()
            if company:
                break
    if not company:
        company = "Unknown Company"

    # 3. Location & Workplace type
    location = ""
    tertiary_container_selectors = [
        ".job-details-jobs-unified-top-card__tertiary-description-container",
        ".jobs-unified-top-card__tertiary-description-container",
        ".jobs-details-top-card__tertiary-description-container"
    ]
    for container_sel in tertiary_container_selectors:
        container = page.locator(container_sel)
        if container.count() > 0:
            spans = container.locator(".tvm__text")
            count = spans.count()
            for idx in range(count):
                text = spans.nth(idx).inner_text().strip()
                if not text or text == "·":
                    continue
                text_lower = text.lower()
                if any(k in text_lower for k in ["ago", "posted", "reposted", "applicant", "actively reviewing", "promoted"]):
                    continue
                location = text
                break
            if location:
                break

    if not location:
        location_selectors = [
            ".jobs-unified-top-card__bullet",
            ".job-details-jobs-unified-top-card__bullet",
            ".jobs-details-top-card__bullet",
            "span.jobs-unified-top-card__bullet-point"
        ]
        for sel in location_selectors:
            el = page.locator(sel)
            if el.count() > 0:
                val = el.first.inner_text().strip()
                if val and not any(k in val.lower() for k in ["ago", "posted", "reposted"]):
                    location = val
                    break
    if not location:
        location = "Unknown Location"

    # 4. Work Mode
    work_mode = "Not Specified"
    pref_selectors = [
        ".job-details-fit-level-preferences button",
        ".job-details-preferences button",
        ".job-details-jobs-unified-top-card__container--two-pane button"
    ]
    for sel in pref_selectors:
        els = page.locator(sel)
        count = els.count()
        for idx in range(count):
            text = els.nth(idx).inner_text().strip()
            text_lower = text.lower()
            if "remote" in text_lower:
                work_mode = "Remote"
                break
            elif "hybrid" in text_lower:
                work_mode = "Hybrid"
                break
            elif "on-site" in text_lower or "onsite" in text_lower:
                work_mode = "On-site"
                break
        if work_mode != "Not Specified":
            break

    if work_mode == "Not Specified":
        workplace_selectors = [
            ".jobs-unified-top-card__workplace-type",
            ".job-details-jobs-unified-top-card__workplace-type",
            ".jobs-details-top-card__workplace-type"
        ]
        for sel in workplace_selectors:
            el = page.locator(sel)
            if el.count() > 0:
                work_mode = el.first.inner_text().strip()
                if work_mode:
                    break
                
    if not work_mode or work_mode in ["Unknown", "Not Specified"]:
        bullet_els = page.locator(".jobs-unified-top-card__bullet, .job-details-jobs-unified-top-card__bullet, .jobs-details-top-card__bullet, .jobs-unified-top-card__bullet-point")
        for i in range(bullet_els.count()):
            text = bullet_els.nth(i).inner_text().lower()
            if "remote" in text:
                work_mode = "Remote"
                break
            elif "hybrid" in text:
                work_mode = "Hybrid"
                break
            elif "on-site" in text or "onsite" in text:
                work_mode = "On-site"
                break

    if not work_mode or work_mode in ["Unknown", "Not Specified"]:
        loc_lower = location.lower()
        if "remote" in loc_lower:
            work_mode = "Remote"
        elif "hybrid" in loc_lower:
            work_mode = "Hybrid"
        elif "on-site" in loc_lower or "onsite" in loc_lower:
            work_mode = "On-site"

    import re
    if work_mode != "Not Specified" and location:
        location = re.sub(r"\s*\(\s*" + re.escape(work_mode) + r"\s*\)", "", location, flags=re.IGNORECASE)
        location = re.sub(r"\s*\(\s*(remote|hybrid|on-site|onsite)\s*\)", "", location, flags=re.IGNORECASE)
        location = location.strip().rstrip(",").strip().rstrip("(").rstrip(")").strip()

    # 5. Date Posted
    date_posted = ""
    for container_sel in tertiary_container_selectors:
        container = page.locator(container_sel)
        if container.count() > 0:
            spans = container.locator(".tvm__text")
            count = spans.count()
            for idx in range(count):
                text = spans.nth(idx).inner_text().strip()
                if any(k in text.lower() for k in ["ago", "posted", "reposted"]):
                    date_posted = text
                    break
            if date_posted:
                break

    if not date_posted:
        date_selectors = [
            ".jobs-unified-top-card__posted-date",
            ".job-details-jobs-unified-top-card__posted-date",
            ".jobs-details-top-card__posted-date"
        ]
        for sel in date_selectors:
            el = page.locator(sel)
            if el.count() > 0:
                date_posted = el.first.inner_text().strip()
                if date_posted:
                    break
                
    if not date_posted or date_posted in ["Unknown", "Not Specified"]:
        bullet_els = page.locator(".jobs-unified-top-card__bullet, .job-details-jobs-unified-top-card__bullet, .jobs-details-top-card__bullet, .jobs-unified-top-card__bullet-point")
        for i in range(bullet_els.count()):
            text = bullet_els.nth(i).inner_text().strip()
            if "ago" in text.lower() or "posted" in text.lower() or "reposted" in text.lower():
                date_posted = text
                break
    if not date_posted:
        date_posted = "Unknown"

    # 6. Salary and Employment Type
    salary = "Not Specified"
    employment_type = "Not Specified"
    
    for sel in pref_selectors:
        els = page.locator(sel)
        count = els.count()
        for idx in range(count):
            text = els.nth(idx).inner_text().strip()
            text_lower = text.lower()
            for k in ["full-time", "part-time", "contractual", "contract", "internship", "intern", "temporary", "co-op"]:
                if k in text_lower:
                    if k in ["full-time", "full time"]:
                        employment_type = "Full-time"
                    elif k in ["part-time", "part time"]:
                        employment_type = "Part-time"
                    elif k in ["contract", "contractual"]:
                        employment_type = "Contract"
                    elif k in ["intern", "internship"]:
                        employment_type = "Internship"
                    elif k in ["temporary"]:
                        employment_type = "Temporary"
                    elif k in ["co-op"]:
                        employment_type = "Co-op"
                    break
            if employment_type != "Not Specified":
                break

    insight_els = page.locator(".jobs-unified-top-card__job-insight, .job-details-jobs-unified-top-card__job-insight, .jobs-unified-top-card__job-insight-view-model-string, .job-details-jobs-unified-top-card__job-insight-view-model-string")
    for i in range(insight_els.count()):
        text = insight_els.nth(i).inner_text().strip()
        text_lower = text.lower()
        if "$" in text or "yr" in text or "hr" in text:
            salary = text.replace("\n", " ").strip()
        elif employment_type == "Not Specified" and any(k in text_lower for k in ["full-time", "full time", "part-time", "part time", "contract", "contractual", "intern", "internship", "temporary", "co-op"]):
            employment_type = text.replace("\n", " ").strip()

    if salary == "Not Specified":
        bullet_els = page.locator(".jobs-unified-top-card__bullet, .job-details-jobs-unified-top-card__bullet, .jobs-details-top-card__bullet")
        for i in range(bullet_els.count()):
            text = bullet_els.nth(i).inner_text().strip()
            if "$" in text:
                salary = text
                break

    # 7. Description
    description = ""
    description_selectors = [
        ".jobs-description__content",
        ".jobs-description",
        "#job-details",
        ".jobs-box__html-content"
    ]
    for sel in description_selectors:
        el = page.locator(sel)
        if el.count() > 0:
            description = el.first.inner_text().strip()
            if description:
                break
    if not description:
        description = "No description available"

    job = {
        "job_id": job_id,
        "title": title,
        "company": company,
        "location": location,
        "url": f"https://www.linkedin.com/jobs/view/{job_id}/",
        "date_posted": date_posted,
        "salary": salary,
        "employment_type": employment_type,
        "work_mode": work_mode,
        "description": description,
        "scraped_at": datetime.datetime.now().isoformat()
    }
    return job

def main():
    init_db()
    keywords = "Software Engineer"
    location = "United States"
    
    user_data_dir = os.path.join(os.getcwd(), ".playwright_data")
    print(f"Using persistent user data dir: {user_data_dir}")
    
    print("Initializing Playwright (headed)...")
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False, # Must be headed so you can log in on your screen
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--start-maximized"
            ]
        )
        
        page = context.pages[0] if context.pages else context.new_page()
        page.set_viewport_size({"width": 1280, "height": 800})
        
        # Check login status
        if not check_login(page):
            print("\n" + "="*80)
            print("ALERT: YOU ARE NOT LOGGED IN.")
            print("Please log in to LinkedIn in the browser window that just opened.")
            print("After logging in successfully and seeing your Feed or Jobs home,")
            print("return to your terminal and press Enter to continue...")
            print("="*80 + "\n")
            input("Press Enter here in the terminal to continue after logging in...")
            
            # Recheck login
            if not check_login(page):
                print("Error: Still not logged in. Exiting.")
                context.close()
                sys.exit(1)
        
        print("Successfully authenticated! Navigating to Job Search...")
        
        # Navigate to search URL
        search_url = f"https://www.linkedin.com/jobs/search/?keywords={keywords.replace(' ', '%20')}&location={location.replace(' ', '%20')}"
        print(f"Navigating to job search: {search_url}")
        page.goto(search_url, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        
        print("Scraping job listings...")
        jobs_scraped = 0
        pages_to_scrape = 2
        
        for current_page in range(1, pages_to_scrape + 1):
            print(f"\n--- Scraping Page {current_page} ---")
            
            # Scroll left panel to load all lazy-loaded job cards
            print("Scrolling job list...")
            left_panel = page.locator(".jobs-search-results-list")
            if left_panel.count() == 0:
                left_panel = page.locator(".jobs-search-results-container")
                
            if left_panel.count() > 0:
                for i in range(10):
                    left_panel.first.evaluate("el => el.scrollTop = el.scrollHeight * " + str((i + 1) / 10))
                    page.wait_for_timeout(400)
            else:
                for i in range(5):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight * " + str((i + 1) / 5) + ")")
                    page.wait_for_timeout(400)
            
            # Extract job cards
            job_cards = page.locator("[data-occludable-job-id], [data-job-id], .job-card-container")
            card_count = job_cards.count()
            print(f"Found {card_count} job cards on this page.")
            
            job_ids = []
            for i in range(card_count):
                card = job_cards.nth(i)
                job_id = card.get_attribute("data-occludable-job-id") or card.get_attribute("data-job-id")
                if not job_id:
                    links = card.locator("a")
                    for li in range(links.count()):
                        href = links.nth(li).get_attribute("href") or ""
                        if "/jobs/view/" in href:
                            parts = href.split("/jobs/view/")
                            if len(parts) > 1:
                                job_id = parts[1].split("/")[0].split("?")[0]
                                break
                if job_id and job_id not in job_ids:
                    job_ids.append(job_id)
            
            print(f"Extracted {len(job_ids)} unique Job IDs: {job_ids}")
            
            for index, job_id in enumerate(job_ids):
                print(f"[{index+1}/{len(job_ids)}] Clicking job ID: {job_id}")
                job_card_click = page.locator(f"[data-occludable-job-id='{job_id}'], [data-job-id='{job_id}']").first
                if job_card_click.count() > 0:
                    try:
                        job_card_click.scroll_into_view_if_needed()
                        job_card_click.click()
                        
                        job_details = scrape_job_details(page, job_id)
                        save_to_db(job_details)
                        save_to_csv(job_details)
                        
                        print(f"   Saved: '{job_details['title']}' at '{job_details['company']}'")
                        jobs_scraped += 1
                    except Exception as e:
                        print(f"   Error scraping job {job_id}: {e}")
                else:
                    print(f"   Job card not clickable. Navigating directly...")
                    try:
                        detail_page = context.new_page()
                        detail_page.goto(f"https://www.linkedin.com/jobs/view/{job_id}/", wait_until="domcontentloaded")
                        job_details = scrape_job_details(detail_page, job_id)
                        save_to_db(job_details)
                        save_to_csv(job_details)
                        print(f"   Saved: '{job_details['title']}' at '{job_details['company']}'")
                        detail_page.close()
                        jobs_scraped += 1
                    except Exception as ex:
                        print(f"   Error navigating directly to job {job_id}: {ex}")
            
            # Go to next page if not last
            if current_page < pages_to_scrape:
                print("Looking for 'Next' page button...")
                next_btn = page.locator("button[aria-label='Next'], button[aria-label^='Page'][class*='active'] + button")
                if next_btn.count() == 0:
                    next_btn = page.locator(f"button[aria-label='Page {current_page + 1}']")
                
                if next_btn.count() > 0 and next_btn.first.is_enabled():
                    print(f"Navigating to page {current_page + 1}...")
                    next_btn.first.click()
                    page.wait_for_timeout(4000)
                else:
                    print("No active 'Next' button found. Stopping scraping.")
                    break
                    
        print(f"\nScrape complete! Successfully scraped {jobs_scraped} jobs.")
        context.close()

if __name__ == "__main__":
    main()
