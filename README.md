# FindMeJobs.ai - Intelligent LinkedIn Job Scraper with HITL

FindMeJobs.ai is a state-of-the-art job search scraping dashboard that automates LinkedIn job harvesting while allowing Human-in-the-Loop (HITL) overrides. It integrates both a custom fast async Playwright scraper and a generative LLM-driven browser agent using `browser-use`.

The application features a responsive split-screen vertical glassmorphic UI layout:
- **Left Panel**: Scraper Controls (keyword/location inputs, LLM setup, runtime action triggers), CV/JD Matcher, and a dynamic Scraped Jobs Database view with quick date filters.
- **Right Panel**: A real-time viewport displaying live browser screenshots alongside streaming terminal execution logs. Includes a full-screen **Spotlight Mode** that triggers automatically during scraping or when HITL action is required.

---

## ⚡ Quick Start

> **Prerequisites**: [Python 3.10+](https://www.python.org/downloads/) (check "Add Python to PATH" during install) and [Git](https://git-scm.com/downloads).

### Option A: One-Click Scripts

**Windows:**
```
git clone <repository-url>
cd find-me-jobs-ai
setup.bat           # One-time: creates venv, installs everything (~2-3 min)
start.bat           # Launches server + opens browser automatically
```

**macOS / Linux:**
```bash
git clone <repository-url>
cd find-me-jobs-ai
chmod +x setup.sh start.sh
./setup.sh          # One-time: creates venv, installs everything (~2-3 min)
./start.sh          # Launches server + opens browser automatically
```

### Option B: Manual Step-by-Step (PowerShell / CMD)

Open **PowerShell** or **Command Prompt** in the project folder:

**Step 1 — Create Virtual Environment & Install Dependencies:**
```powershell
python -m venv .venv
.\.venv\Scripts\activate

# Install all required Python packages:
pip install -r requirements.txt

# Install the Playwright Chromium browser binary:
playwright install chromium
```

**Step 2 — Initial LinkedIn Login (One-Time Authentication):**
```powershell
.\.venv\Scripts\python.exe scrape_linkedin.py
```
> A Chrome browser window will open. Log in manually with your LinkedIn credentials, complete any security/2FA checks, and once you see your LinkedIn feed, go back to the terminal and press **Enter**. The script will cache your session and close automatically.

**Step 3 — Start the Web Dashboard:**
```powershell
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
```
Open your browser and go to: **http://127.0.0.1:8000**

---

## 🔐 LinkedIn Login — How It Works

The scraper requires a logged-in LinkedIn session. There are **two ways** to authenticate:

### Method 1: Pre-Login via Script (Recommended for First Setup)
Run `scrape_linkedin.py` directly — it opens a headed Chrome browser where you log in manually. Your session cookies are saved to `.playwright_data/` and reused automatically on all future runs.

```powershell
.\.venv\Scripts\python.exe scrape_linkedin.py
```

### Method 2: Login via Dashboard HITL (During Scraping)
1. Start the dashboard and click **Start Scraping**.
2. If the terminal shows `[HITL] LinkedIn session is not logged in`, the viewport enters **Spotlight Mode**.
3. Click the **Browser** tab, interact with the viewport to enter your credentials and solve any 2FA challenges.
4. Once logged in, click **Resume** on the Scraper Controls.

> **Note**: Each user must complete their own LinkedIn login. Session data (`.playwright_data/`) is local and must not be shared.

---

## 🌟 Key Features

### 1. Multi-Mode Scraping
- **Fast Playwright Scraper**: A highly optimized, custom async scraper utilizing raw Playwright calls. It scrolls through search cards, navigates to detailed pages, parses workplace types, and records them in under 5 seconds per job.
- **AI Agent Scraper**: Uses `browser-use` and Google Gemini/OpenAI LLM models to dynamically explore, analyze, and click through job descriptions using visual computer vision and DOM elements.

### 2. Human-In-The-Loop (HITL) Control
- **Screenshot Viewport Stream**: Streams high-fidelity browser screenshots to the UI dashboard using WebSockets.
- **Interactive Mouse/Keyboard Coordinates**: Click anywhere on the browser viewport image in the UI, and the coordinates are mapped and forwarded to the backend browser page to perform real clicks.
- **Input Text Forwarding**: Allows the user to type and send keyboard inputs directly into the active browser focus (e.g. for bypassing captchas or logging in manually).
- **Auto-Pausing & Prompts**: Automatically pauses execution and displays alerts if LinkedIn session cookies expire, prompting the user to interactively log in.

### 3. Smart Deduplication & Data Sync
- **No Duplicate Entries**: Before clicking or scraping a job card, the scraper queries the SQLite database. If a job has already been scraped, it bypasses it and logs the skip, saving tokens and network calls.
- **AI Agent Optimization**: Already-scraped Job IDs are dynamically injected into the AI Agent's system prompt, instructing the LLM to skip clicking on those cards entirely.
- **SQLite & CSV Synchronization**: SQLite acts as the single source of truth. On startup, the `jobs.csv` file is fully rebuilt and de-duplicated. During runtime, new unique jobs are written to SQLite and appended to the CSV.

### 4. CV / Job Description Matcher
- Upload your CV (PDF, DOCX) or paste text, then compare against any scraped job description.
- LLM-powered analysis returns a match score, matched skills, missing skills, and actionable improvement tips.
- Auto-fill CV from your saved profile data.

### 5. Quick Date Filters
- **Today / Yesterday** pill tags above the jobs table for instant filtering by scrape date.
- Combined with the advanced Filter & Sort modal for company, location, work mode, salary, and more.

### 6. Advanced Spotlight Mode
- Maximizes the live browser viewport into a premium full-screen glassmorphic overlay during active scraping runs or when paused for manual intervention.
- The viewport remains in Spotlight mode after scraping completes, allowing developers to inspect details and close/minimize the screen manually.

---

## 🛠️ Architecture & Technologies

- **Backend**: FastAPI, WebSockets, Python `asyncio`
- **Scraper Engine**: Playwright, `browser-use`
- **Database**: SQLite3, CSV Exporter
- **LLM Integration**: Google Gemini, OpenAI (via LangChain)
- **Frontend**: Vanilla HTML5, CSS3 (Glassmorphism), JavaScript (WebSocket API)
- **Git Branching Policy**: Centralized branching workflow.
  - `main`: Stable release branch.
  - `development`: Main development branch where features are integrated.
  - `feature/*`: Dedicated branches for individual features, fixes, or refactors.

---

## 📂 Project Directory Structure

```
find-me-jobs-ai/
├── app.py                  # Main FastAPI server and scraper loops
├── scrape_linkedin.py      # Core scraping logic and utility scripts
├── templates/
│   └── index.html          # Split-panel glassmorphic dashboard UI
├── requirements.txt        # Python dependencies
├── setup.bat / setup.sh    # One-click setup scripts
├── start.bat / start.sh    # One-click launch scripts
├── jobs.db                 # SQLite database storage (git-ignored)
├── jobs.csv                # Sync CSV file (git-ignored)
├── .playwright_data/       # Persistent browser profile state (git-ignored)
├── .gitignore              # Standard git exclusion rules
└── README.md               # Project documentation
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:
1. Always create a new feature branch off the `development` branch:
   ```bash
   git checkout development
   git pull origin development
   git checkout -b feature/your-feature-name
   ```
2. Commit your changes using Conventional Commit guidelines:
   - `feat(ui): add new dark mode theme`
   - `fix(fast): fix class locator for company name`
   - `chore(deps): update playwright version`
3. Merge your feature branch back into `development` and keep other branches rebased:
   ```bash
   git checkout development
   git merge feature/your-feature-name
   ```
4. Never commit directly to `main`. `development` will be merged into `main` only for production releases.

