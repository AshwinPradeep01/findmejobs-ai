# FindMeJobs.ai - Intelligent LinkedIn Job Scraper with HITL

FindMeJobs.ai is a state-of-the-art job search scraping dashboard that automates LinkedIn job harvesting while allowing Human-in-the-Loop (HITL) overrides. It integrates both a custom fast async Playwright scraper and a generative LLM-driven browser agent using `browser-use`.

The application features a responsive split-screen vertical glassmorphic UI layout:
- **Left Panel**: Scraper Controls (keyword/location inputs, LLM setup, runtime action triggers) and a dynamic Scraped Jobs Database view.
- **Right Panel**: A real-time viewport displaying live browser screenshots alongside streaming terminal execution logs. Includes a full-screen **Spotlight Mode** that triggers automatically during scraping or when HITL action is required.

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

### 4. Advanced Spotlight Mode
- Maximizes the live browser viewport into a premium full-screen glassmorphic overlay during active scraping runs or when paused for manual intervention.
- The viewport remains in Spotlight mode after scraping completes, allowing developers to inspect details and close/minimize the screen manually.

---

## 🛠️ Architecture & Technologies

- **Backend**: FastAPI, WebSockets, Python `asyncio`
- **Scraper Engine**: Playwright, `browser-use`
- **Database**: SQLite3, CSV Exporter
- **Frontend**: Vanilla HTML5, CSS3 (Glassmorphism), JavaScript (WebSocket API, relative coordinate calculators)
- **Git Branching Policy**: Centralized branching workflow.
  - `main`: Stable release branch.
  - `development`: Main development branch where features are integrated.
  - `feature/*`: Dedicated branches for individual features, fixes, or refactors.

---

## 🚀 Getting Started

### 📋 Prerequisites
- Python 3.10 or higher
- Google Gemini API Key (or OpenAI API Key)
- LinkedIn account logged in (Playwright profile state saves auth session)

### ⚙️ Installation

1. **Clone the Repository**:
   ```bash
   git clone <repository-url>
   cd find-me-jobs-ai
   ```

2. **Set Up Python Virtual Environment**:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   # Or using uv:
   uv pip install -r requirements.txt
   ```

4. **Install Playwright Browsers**:
   ```bash
   playwright install chromium
   ```

---

## 💻 Running the Application

1. **Start the FastAPI Backend**:
   ```bash
   python -m uvicorn app:app --host 127.0.0.1 --port 8000
   ```

2. **Open the Dashboard**:
   Open your browser and navigate to: [http://127.0.0.1:8000](http://127.0.0.1:8000)

3. **Perform Initial Login**:
   - Start the **Fast Scraper** with your keyword and location.
   - If the terminal shows `[HITL] LinkedIn session is not logged in`, the viewport will automatically enter **Spotlight Mode**.
   - Select the **Browser** tab, interact with the screen to enter your credentials, and solve any 2FA/security verification challenges.
   - Once logged in, click **Resume** on the Scraper Controls. The session state is saved to the local directory `.playwright_data/` and will be loaded automatically on future runs.

---

## 📂 Project Directory Structure

```
find-me-jobs-ai/
├── app.py                  # Main FastAPI server and scraper loops
├── scrape_linkedin.py      # Core scraping logic and utility scripts
├── templates/
│   └── index.html          # Split-panel glassmorphic dashboard UI
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
