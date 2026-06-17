import sys
import asyncio
if sys.platform == 'win32':
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

import os
import re
import csv
import json
import sqlite3
import datetime
import base64
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("linkedin_finder")

DB_PATH = "jobs.db"
CSV_PATH = "jobs.csv"

# FastAPI App
app = FastAPI(title="FindMeJobs.ai - LinkedIn Scraper with HITL")

# Initialize DB
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

init_db()

# DB Helpers
def save_job_data(job):
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

    # Save to CSV
    file_exists = os.path.exists(CSV_PATH)
    fieldnames = ["job_id", "title", "company", "location", "url", "date_posted", "salary", "employment_type", "work_mode", "description", "scraped_at"]
    with open(CSV_PATH, mode="a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(job)

def extract_job_id(url):
    match = re.search(r"/view/(\d+)", url)
    if match:
        return match.group(1)
    match = re.search(r"currentJobId=(\d+)", url)
    if match:
        return match.group(1)
    import hashlib
    return hashlib.md5(url.encode()).hexdigest()

# Browser Use imports
from browser_use import Agent, Browser, BrowserProfile, Controller
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

# Set up browser-use Controller for Custom Actions
controller = Controller()

@controller.action("Save job details to database and CSV")
async def save_job_to_db(
    title: str, 
    company: str, 
    location: str, 
    url: str, 
    description: str, 
    salary: str = "Not Specified", 
    employment_type: str = "Not Specified",
    date_posted: str = "Unknown",
    work_mode: str = "Not Specified"
):
    """Saves the extracted job details (Title, Company, Location, Description, Salary, Work Mode, etc.) to the SQLite database and CSV."""
    global active_browser
    
    # Fallback parsing directly from Playwright DOM if values are missing or default
    if active_browser:
        try:
            page = await active_browser.get_current_page()
            if page:
                # 1. Location Fallback
                if not location or location in ["Unknown Location", "Not Specified", "Unknown"]:
                    loc_selectors = [
                        ".jobs-unified-top-card__bullet",
                        ".job-details-jobs-unified-top-card__bullet",
                        ".jobs-details-top-card__bullet",
                        "span.jobs-unified-top-card__bullet-point",
                        ".job-card-container__metadata-item"
                    ]
                    for sel in loc_selectors:
                        el = page.locator(sel)
                        if await el.count() > 0:
                            val = (await el.first.inner_text()).strip()
                            if val:
                                location = val
                                break

                # 2. Date Posted Fallback
                if not date_posted or date_posted in ["Unknown", "Not Specified"]:
                    date_selectors = [
                        ".jobs-unified-top-card__posted-date",
                        ".job-details-jobs-unified-top-card__posted-date",
                        ".jobs-details-top-card__posted-date"
                    ]
                    for sel in date_selectors:
                        el = page.locator(sel)
                        if await el.count() > 0:
                            val = (await el.first.inner_text()).strip()
                            if val:
                                date_posted = val
                                break

                # 3. Salary & Employment Type from insights
                insight_els = page.locator(".jobs-unified-top-card__job-insight, .job-details-jobs-unified-top-card__job-insight")
                for i in range(await insight_els.count()):
                    text = (await insight_els.nth(i).inner_text()).strip()
                    if ("$" in text or "yr" in text or "hr" in text) and (not salary or salary == "Not Specified"):
                        salary = text.replace("\n", " ").strip()
                    elif ("Full-time" in text or "Part-time" in text or "Contract" in text or "Temporary" in text) and (not employment_type or employment_type == "Not Specified"):
                        employment_type = text.replace("\n", " ").strip()
                            
                # Fallback check bullets for salary
                if not salary or salary == "Not Specified":
                    bullet_els = page.locator(".jobs-unified-top-card__bullet, .job-details-jobs-unified-top-card__bullet")
                    for i in range(await bullet_els.count()):
                        text = (await bullet_els.nth(i).inner_text()).strip()
                        if "$" in text:
                            salary = text
                            break

                # 4. Work Mode Fallback
                if not work_mode or work_mode in ["Unknown", "Not Specified"]:
                    workplace_selectors = [
                        ".jobs-unified-top-card__workplace-type",
                        ".job-details-jobs-unified-top-card__workplace-type",
                        ".jobs-details-top-card__workplace-type"
                    ]
                    for sel in workplace_selectors:
                        el = page.locator(sel)
                        if await el.count() > 0:
                            val = (await el.first.inner_text()).strip()
                            if val:
                                work_mode = val
                                break
                    if not work_mode or work_mode in ["Unknown", "Not Specified"]:
                        bullet_els = page.locator(".jobs-unified-top-card__bullet, .job-details-jobs-unified-top-card__bullet, .jobs-unified-top-card__bullet-point")
                        for i in range(await bullet_els.count()):
                            text = (await bullet_els.nth(i).inner_text()).lower()
                            if "remote" in text:
                                work_mode = "Remote"
                                break
                            elif "hybrid" in text:
                                work_mode = "Hybrid"
                                break
                            elif "on-site" in text or "onsite" in text:
                                work_mode = "On-site"
                                break

                # Clean location if it contains work_mode
                if work_mode != "Not Specified" and location:
                    location = re.sub(r"\s*\(\s*" + re.escape(work_mode) + r"\s*\)", "", location, flags=re.IGNORECASE)
                    location = re.sub(r"\s*\(\s*(remote|hybrid|on-site|onsite)\s*\)", "", location, flags=re.IGNORECASE)

                # 5. Description Fallback (if LLM passed short summary)
                if not description or len(description) < 50:
                    desc_selectors = [
                        ".jobs-description__content",
                        ".jobs-description",
                        "#job-details",
                        ".jobs-box__html-content"
                    ]
                    for sel in desc_selectors:
                        el = page.locator(sel)
                        if await el.count() > 0:
                            val = (await el.first.inner_text()).strip()
                            if val:
                                description = val
                                break
        except Exception as e:
            logger.error(f"Error during DOM fallback parsing in custom action: {e}")

    job_id = extract_job_id(url)
    job = {
        "job_id": job_id,
        "title": title,
        "company": company,
        "location": location or "Unknown Location",
        "url": url,
        "date_posted": date_posted or "Unknown",
        "salary": salary or "Not Specified",
        "employment_type": employment_type or "Not Specified",
        "work_mode": work_mode or "Not Specified",
        "description": description or "No description available",
        "scraped_at": datetime.datetime.now().isoformat()
    }
    save_job_data(job)
    logger.info(f"Custom Action saved job: {title} at {company} (Location: {location}, Work Mode: {work_mode}, Salary: {salary})")
    
    # Broadcast database update to UI
    asyncio.create_task(manager.broadcast({"type": "db_update"}))
    
    return f"Successfully saved job '{title}' at '{company}' (Location: {location}, Work Mode: {work_mode}, Salary: {salary}) to DB."


# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

class AgentStoppedException(Exception):
    pass

# Global State
state = {
    "agent_running": False,
    "agent_paused": False,
    "logs": [],
    "current_screenshot": None
}

pause_event = asyncio.Event()
pause_event.set()

active_browser = None
active_agent = None

async def capture_screenshot():
    global active_browser
    if active_browser:
        try:
            page = await active_browser.get_current_page()
            if page:
                screenshot_bytes = await page.screenshot(type="jpeg", quality=55)
                state["current_screenshot"] = base64.b64encode(screenshot_bytes).decode("utf-8")
                await manager.broadcast({
                    "type": "screenshot",
                    "data": state["current_screenshot"]
                })
        except Exception as e:
            pass

async def screenshot_loop():
    while state["agent_running"]:
        await capture_screenshot()
        await asyncio.sleep(1.5)

async def add_log(message: str):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    formatted_log = f"[{timestamp}] {message}"
    state["logs"].append(formatted_log)
    await manager.broadcast({
        "type": "log",
        "message": formatted_log
    })

# Callback called after every step by browser-use agent
async def on_agent_step(state_summary, agent_output, step_number):
    global pause_event
    
    # Check if stop requested
    if not state["agent_running"]:
        raise AgentStoppedException("Agent execution stopped by user.")
        
    # Get thought and action details
    thoughts = getattr(agent_output, "model_thoughts", "Executing next action...")
    await add_log(f"Agent Thought (Step {step_number}): {thoughts}")
    
    # Send screenshot immediately
    await capture_screenshot()
    
    # HITL Pause Check
    if state["agent_paused"]:
        await add_log("Agent execution PAUSED by user. Waiting for resume...")
        await manager.broadcast({"type": "status", "status": "paused"})
        await pause_event.wait()
        
        # Check again after unblocking from pause
        if not state["agent_running"]:
            raise AgentStoppedException("Agent execution stopped by user.")
            
        await add_log("Agent execution RESUMED by user.")
        await manager.broadcast({"type": "status", "status": "running"})

# Async Playwright Scraper Helpers
async def check_login_async(page):
    await add_log("[SYSTEM] Checking authentication status...")
    try:
        await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
        await asyncio.sleep(3)
        current_url = page.url
        logger.info(f"Current URL during auth check: {current_url}")
        if "login" in current_url or "signup" in current_url or "checkpoint" in current_url:
            return False
        return True
    except Exception as e:
        await add_log(f"[SYSTEM] Error checking auth status: {str(e)}")
        return False

async def scrape_job_details_async(page, job_id):
    await asyncio.sleep(2)
    
    title = ""
    title_selectors = [
        "h2.jobs-unified-top-card__job-title",
        ".jobs-unified-top-card__job-title",
        ".job-details-jobs-unified-top-card__title",
        "h1.t-24",
        "h2"
    ]
    for sel in title_selectors:
        el = page.locator(sel)
        if await el.count() > 0:
            title = (await el.first.inner_text()).strip()
            if title:
                break

    company = ""
    company_selectors = [
        ".jobs-unified-top-card__company-name a",
        ".jobs-unified-top-card__company-name",
        ".job-details-jobs-unified-top-card__company-name a",
        ".job-details-jobs-unified-top-card__company-name",
        ".jobs-details-top-card__company-info a"
    ]
    for sel in company_selectors:
        el = page.locator(sel)
        if await el.count() > 0:
            company = (await el.first.inner_text()).strip()
            if company:
                break

    location = ""
    location_selectors = [
        ".jobs-unified-top-card__bullet",
        ".job-details-jobs-unified-top-card__bullet",
        ".jobs-details-top-card__bullet"
    ]
    for sel in location_selectors:
        el = page.locator(sel)
        if await el.count() > 0:
            location = (await el.first.inner_text()).strip()
            if location:
                break

    date_posted = ""
    date_selectors = [
        ".jobs-unified-top-card__posted-date",
        ".job-details-jobs-unified-top-card__posted-date",
        ".jobs-details-top-card__posted-date"
    ]
    for sel in date_selectors:
        el = page.locator(sel)
        if await el.count() > 0:
            date_posted = (await el.first.inner_text()).strip()
            if date_posted:
                break

    description = ""
    description_selectors = [
        ".jobs-description__content",
        ".jobs-description",
        "#job-details",
        ".jobs-box__html-content"
    ]
    for sel in description_selectors:
        el = page.locator(sel)
        if await el.count() > 0:
            description = (await el.first.inner_text()).strip()
            if description:
                break

    salary = ""
    employment_type = ""
    try:
        insight_els = page.locator(".jobs-unified-top-card__job-insight, .job-details-jobs-unified-top-card__job-insight")
        for i in range(await insight_els.count()):
            text = (await insight_els.nth(i).inner_text()).strip()
            if "$" in text or "yr" in text or "hr" in text:
                salary = text.replace("\n", " ").strip()
            elif "Full-time" in text or "Part-time" in text or "Contract" in text or "Temporary" in text:
                employment_type = text.replace("\n", " ").strip()
    except Exception:
        pass

    if not salary:
        try:
            bullet_els = page.locator(".jobs-unified-top-card__bullet, .job-details-jobs-unified-top-card__bullet")
            for i in range(await bullet_els.count()):
                text = (await bullet_els.nth(i).inner_text()).strip()
                if "$" in text:
                    salary = text
                    break
        except Exception:
            pass

    work_mode = "Not Specified"
    try:
        workplace_selectors = [
            ".jobs-unified-top-card__workplace-type",
            ".job-details-jobs-unified-top-card__workplace-type",
            ".jobs-details-top-card__workplace-type"
        ]
        for sel in workplace_selectors:
            el = page.locator(sel)
            if await el.count() > 0:
                work_mode = (await el.first.inner_text()).strip()
                if work_mode:
                    break
        
        if not work_mode or work_mode in ["Unknown", "Not Specified"]:
            bullet_els = page.locator(".jobs-unified-top-card__bullet, .job-details-jobs-unified-top-card__bullet, .jobs-unified-top-card__bullet-point")
            for i in range(await bullet_els.count()):
                text = (await bullet_els.nth(i).inner_text()).lower()
                if "remote" in text:
                    work_mode = "Remote"
                    break
                elif "hybrid" in text:
                    work_mode = "Hybrid"
                    break
                elif "on-site" in text or "onsite" in text:
                    work_mode = "On-site"
                    break
    except Exception:
        pass

    if work_mode != "Not Specified" and location:
        location = re.sub(r"\s*\(\s*" + re.escape(work_mode) + r"\s*\)", "", location, flags=re.IGNORECASE)
        location = re.sub(r"\s*\(\s*(remote|hybrid|on-site|onsite)\s*\)", "", location, flags=re.IGNORECASE)

    job = {
        "job_id": job_id,
        "title": title or "Unknown Title",
        "company": company or "Unknown Company",
        "location": location or "Unknown Location",
        "url": f"https://www.linkedin.com/jobs/view/{job_id}/",
        "date_posted": date_posted or "Unknown",
        "salary": salary or "Not Specified",
        "employment_type": employment_type or "Not Specified",
        "work_mode": work_mode,
        "description": description or "No description available",
        "scraped_at": datetime.datetime.now().isoformat()
    }
    return job

# Main Fast Playwright Runner
async def run_linkedin_fast(keywords, location):
    global active_browser, pause_event
    
    state["agent_running"] = True
    state["agent_paused"] = False
    pause_event.set()
    
    await manager.broadcast({"type": "status", "status": "running"})
    await add_log("[SYSTEM] Starting Fast Playwright Scraper...")
    asyncio.create_task(screenshot_loop())
    
    user_data_dir = os.path.abspath(".playwright_data")
    await add_log(f"[SYSTEM] Loading Playwright context from: {user_data_dir}")
    
    try:
        from playwright.async_api import async_playwright
        
        class BrowserMock:
            def __init__(self, page, context):
                self._page = page
                self._context = context
            async def get_current_page(self):
                return self._page
            async def close(self):
                try:
                    await self._context.close()
                except Exception:
                    pass
        
        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox"
                ]
            )
            
            page = context.pages[0] if context.pages else await context.new_page()
            await page.set_viewport_size({"width": 1280, "height": 800})
            
            active_browser = BrowserMock(page, context)
            
            async def check_hitl_pause():
                if state["agent_paused"]:
                    await add_log("[HITL] Scraper execution PAUSED by user. Waiting for resume...")
                    await manager.broadcast({"type": "status", "status": "paused"})
                    await pause_event.wait()
                    await add_log("[HITL] Scraper execution RESUMED by user.")
                    await manager.broadcast({"type": "status", "status": "running"})
            
            def should_stop():
                return not state["agent_running"]

            await check_hitl_pause()
            if should_stop():
                await context.close()
                return
                
            logged_in = await check_login_async(page)
            if not logged_in:
                await add_log("[HITL] Warning: LinkedIn session is not logged in or has expired.")
                await add_log("[HITL] Pausing execution. Please log in on the browser viewport and then click Resume.")
                state["agent_paused"] = True
                await check_hitl_pause()
                
                logged_in = await check_login_async(page)
                if not logged_in:
                    await add_log("[SYSTEM] Error: Still not authenticated. Exiting scraper.")
                    await context.close()
                    return
            
            await add_log("[SYSTEM] Authenticated! Navigating to LinkedIn Job Search...")
            await check_hitl_pause()
            if should_stop():
                await context.close()
                return

            search_url = f"https://www.linkedin.com/jobs/search/?keywords={keywords.replace(' ', '%20')}&location={location.replace(' ', '%20')}"
            await add_log(f"[SYSTEM] Navigating to search: {search_url}")
            await page.goto(search_url, wait_until="domcontentloaded")
            await asyncio.sleep(4)
            await capture_screenshot()
            
            pages_to_scrape = 5
            jobs_scraped = 0
            
            for current_page in range(1, pages_to_scrape + 1):
                await check_hitl_pause()
                if should_stop():
                    break
                
                await add_log(f"[SYSTEM] --- Scraping Search Page {current_page} ---")
                
                # Scroll left panel
                await add_log("[SYSTEM] Scrolling job card list...")
                left_panel = page.locator(".jobs-search-results-list")
                if await left_panel.count() == 0:
                    left_panel = page.locator(".jobs-search-results-container")
                    
                if await left_panel.count() > 0:
                    for i in range(10):
                        await check_hitl_pause()
                        if should_stop():
                            break
                        await left_panel.first.evaluate(f"el => el.scrollTop = el.scrollHeight * {(i + 1) / 10}")
                        await asyncio.sleep(0.4)
                else:
                    for i in range(5):
                        await check_hitl_pause()
                        if should_stop():
                            break
                        await page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {(i + 1) / 5})")
                        await asyncio.sleep(0.4)
                
                await capture_screenshot()
                
                job_cards = page.locator("[data-occludable-job-id], [data-job-id], .job-card-container")
                card_count = await job_cards.count()
                await add_log(f"[SYSTEM] Found {card_count} job cards on this page.")
                
                job_ids = []
                for i in range(card_count):
                    card = job_cards.nth(i)
                    job_id = await card.get_attribute("data-occludable-job-id") or await card.get_attribute("data-job-id")
                    if not job_id:
                        links = card.locator("a")
                        for li in range(await links.count()):
                            href = await links.nth(li).get_attribute("href") or ""
                            if "/jobs/view/" in href:
                                parts = href.split("/jobs/view/")
                                if len(parts) > 1:
                                    job_id = parts[1].split("/")[0].split("?")[0]
                                    break
                    if job_id and job_id not in job_ids:
                        job_ids.append(job_id)
                
                await add_log(f"[SYSTEM] Extracted {len(job_ids)} unique Job IDs.")
                
                for index, job_id in enumerate(job_ids):
                    await check_hitl_pause()
                    if should_stop():
                        break
                    
                    await add_log(f"[SYSTEM] [{index+1}/{len(job_ids)}] Clicking job ID: {job_id}")
                    job_card_click = page.locator(f"[data-occludable-job-id='{job_id}'], [data-job-id='{job_id}']").first
                    if await job_card_click.count() > 0:
                        try:
                            await job_card_click.scroll_into_view_if_needed()
                            await job_card_click.click()
                            await capture_screenshot()
                            
                            job_details = await scrape_job_details_async(page, job_id)
                            save_job_data(job_details)
                            await manager.broadcast({"type": "db_update"})
                            
                            await add_log(f"   [SYSTEM] Saved: '{job_details['title']}' at '{job_details['company']}'")
                            jobs_scraped += 1
                        except Exception as e:
                            await add_log(f"   [SYSTEM] Error scraping job {job_id}: {str(e)}")
                    else:
                        await add_log(f"   [SYSTEM] Job card not clickable. Navigating directly to details page...")
                        try:
                            detail_page = await context.new_page()
                            await detail_page.goto(f"https://www.linkedin.com/jobs/view/{job_id}/", wait_until="domcontentloaded")
                            job_details = await scrape_job_details_async(detail_page, job_id)
                            save_job_data(job_details)
                            await manager.broadcast({"type": "db_update"})
                            
                            await add_log(f"   [SYSTEM] Saved: '{job_details['title']}' at '{job_details['company']}'")
                            await detail_page.close()
                            jobs_scraped += 1
                        except Exception as ex:
                            await add_log(f"   [SYSTEM] Error loading direct job details {job_id}: {str(ex)}")
                
                if current_page < pages_to_scrape:
                    await check_hitl_pause()
                    if should_stop():
                        break
                    
                    await add_log("[SYSTEM] Looking for 'Next' page button...")
                    next_btn = page.locator("button[aria-label='Next'], button[aria-label^='Page'][class*='active'] + button")
                    if await next_btn.count() == 0:
                        next_btn = page.locator(f"button[aria-label='Page {current_page + 1}']")
                    
                    if await next_btn.count() > 0 and await next_btn.first.is_enabled():
                        await add_log(f"[SYSTEM] Navigating to page {current_page + 1}...")
                        await next_btn.first.click()
                        await asyncio.sleep(4)
                        await capture_screenshot()
                    else:
                        await add_log("[SYSTEM] No active 'Next' button found. Stopping scraping.")
                        break
            
            await add_log(f"[SYSTEM] Fast Scraper finished! Scraped {jobs_scraped} jobs successfully.")
            await context.close()
            
    except Exception as e:
        await add_log(f"[SYSTEM] Error in Fast Scraper: {str(e)}")
    finally:
        state["agent_running"] = False
        state["agent_paused"] = False
        await manager.broadcast({"type": "status", "status": "idle"})
        active_browser = None

# Main Agent Runner Task
async def run_linkedin_agent(keywords, location, llm_provider, api_key):
    global active_browser, active_agent, pause_event
    
    state["agent_running"] = True
    state["agent_paused"] = False
    pause_event.set()
    
    await manager.broadcast({"type": "status", "status": "running"})
    await add_log(f"Starting browser-use agent for '{keywords}' in '{location}'...")
    
    # Initialize LLM
    try:
        if llm_provider == "gemini":
            llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=api_key)
            await add_log("Initialized Gemini 2.5 Flash LLM.")
        elif llm_provider == "openai":
            llm = ChatOpenAI(model="gpt-4o-mini", api_key=api_key)
            await add_log("Initialized OpenAI GPT-4o-mini LLM.")
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}")
    except Exception as e:
        await add_log(f"Failed to initialize LLM: {str(e)}")
        state["agent_running"] = False
        await manager.broadcast({"type": "status", "status": "idle"})
        return
        
    # Start screenshot streaming loop in background
    asyncio.create_task(screenshot_loop())
    
    try:
        # Initialize browser-use Browser with our Phase 1 session cookie profile
        profile = BrowserProfile()
        user_data_dir = os.path.abspath(".playwright_data")
        
        await add_log(f"Loading Playwright context from: {user_data_dir}")
        active_browser = Browser(
            browser_profile=profile,
            headless=True,
            user_data_dir=user_data_dir,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        task_prompt = (
            f"Navigate to LinkedIn jobs search page. "
            f"Search for '{keywords}' in '{location}'. "
            f"Look at the search results. For each job card, click it to open the details. "
            f"Use the custom action 'Save job details to database and CSV' to extract and save the details of each job "
            f"(Title, Company, Location, Description, URL, Salary, and Employment Type). "
            f"Try to scrape at least 5-10 jobs. Go to the next page of results if necessary. "
            f"Do not click apply or perform external application steps."
        )
        
        active_agent = Agent(
            task=task_prompt,
            llm=llm,
            browser=active_browser,
            controller=controller,
            register_new_step_callback=on_agent_step,
            use_vision=True
        )
        
        await add_log("Agent initialized. Running main loop...")
        await active_agent.run()
        await add_log("Agent execution finished successfully!")
        
    except AgentStoppedException:
        await add_log("[SYSTEM] Scraper stopped successfully by user.")
    except Exception as e:
        await add_log(f"Error during agent execution: {str(e)}")
    finally:
        state["agent_running"] = False
        state["agent_paused"] = False
        await manager.broadcast({"type": "status", "status": "idle"})
        if active_browser:
            try:
                await active_browser.close()
            except Exception:
                pass
            active_browser = None
        active_agent = None

# API Routes
@app.get("/")
async def get_dashboard():
    with open("templates/index.html", "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(content=html)

@app.get("/api/jobs")
async def get_jobs():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs ORDER BY scraped_at DESC")
    rows = cursor.fetchall()
    jobs = [dict(row) for row in rows]
    conn.close()
    return jobs

# WebSocket route
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    # Send current state on connection
    await websocket.send_json({
        "type": "init",
        "agent_running": state["agent_running"],
        "agent_paused": state["agent_paused"],
        "logs": state["logs"],
        "current_screenshot": state["current_screenshot"]
    })
    
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            msg_type = msg.get("type")
            
            if msg_type == "start":
                if not state["agent_running"]:
                    mode = msg.get("mode", "fast")
                    keywords = msg.get("keywords", "Software Engineer")
                    location = msg.get("location", "United States")
                    llm_provider = msg.get("llm_provider", "gemini")
                    api_key = msg.get("api_key", "").strip()
                    
                    if mode == "ai" and not api_key:
                        await websocket.send_json({
                            "type": "log",
                            "message": "[SYSTEM] Error: LLM API Key is required to start the AI agent."
                        })
                        continue
                        
                    # Start background runner based on selected mode
                    if mode == "ai":
                        asyncio.create_task(run_linkedin_agent(keywords, location, llm_provider, api_key))
                    else:
                        asyncio.create_task(run_linkedin_fast(keywords, location))
                    
            elif msg_type == "pause":
                if state["agent_running"]:
                    state["agent_paused"] = True
                    pause_event.clear()
                    await websocket.send_json({
                        "type": "log",
                        "message": "[SYSTEM] Pause requested. Will pause on next step."
                    })
                    
            elif msg_type == "resume":
                if state["agent_running"]:
                    state["agent_paused"] = False
                    pause_event.set()
                    await websocket.send_json({
                        "type": "log",
                        "message": "[SYSTEM] Resuming execution."
                    })
                    
            elif msg_type == "stop":
                if state["agent_running"]:
                    await add_log("[SYSTEM] Stop requested. Finishing current job details before exit...")
                    state["agent_running"] = False
                    # Unblock if paused
                    pause_event.set()
                            
            elif msg_type == "input":
                text = msg.get("text", "")
                if state["agent_running"] and active_browser:
                    try:
                        page = await active_browser.get_current_page()
                        if page:
                            # Direct key insertion
                            await page.keyboard.type(text)
                            await page.keyboard.press("Enter")
                            await add_log(f"[HITL Input] Sent text '{text}' to browser focus.")
                            # Capture screenshot immediately to reflect change
                            await capture_screenshot()
                    except Exception as e:
                        await add_log(f"[HITL Input] Error sending input: {str(e)}")
                        
            elif msg_type == "click":
                x_pct = msg.get("x", 0.0)
                y_pct = msg.get("y", 0.0)
                if state["agent_running"] and active_browser:
                    try:
                        page = await active_browser.get_current_page()
                        if page:
                            viewport = page.viewport_size or {"width": 1280, "height": 800}
                            abs_x = int(viewport["width"] * x_pct)
                            abs_y = int(viewport["height"] * y_pct)
                            await page.mouse.click(abs_x, abs_y)
                            await add_log(f"[HITL Click] Clicked coordinates ({abs_x}, {abs_y}) - {int(x_pct*100)}%, {int(y_pct*100)}%")
                            await capture_screenshot()
                    except Exception as e:
                        await add_log(f"[HITL Click] Error performing click: {str(e)}")
                        
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
