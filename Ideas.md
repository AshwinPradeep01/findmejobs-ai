# FindMeJobs.ai - Future Roadmap & Feature Ideas

This document outlines the backlog of advanced features planned for **FindMeJobs.ai**. These features will be implemented iteratively to transform the application from a raw job scraper into a complete, end-to-end AI-driven job hunt assistant.

---

## 📋 Backlog Items

### 1. 🧠 AI Resume Matcher & Suitability Score
* **Goal**: Provide instant visual feedback on how well your profile matches any scraped job.
* **Details**:
  - Add a **Resume Upload** area (supporting PDF, Text, or Markdown pasting) in the dashboard settings panel.
  - After scraping a job, trigger an asynchronous background LLM run to evaluate the full job description against your resume text.
  - Calculate a **Suitability Score** (from `0%` to `100%`).
  - Output structured bullet lists showing:
    - **Matching Skills**: Technical/soft skills present in both the description and resume.
    - **Missing Skills / Gaps**: Keywords or requirements listed in the job description that your resume does not show.
  - Store the score and analysis inside the `jobs` SQLite database and display it as a color-coded badge (e.g. Green for >80%, Yellow for 50-80%, Red for <50%) in the dashboard table.

---

### 2. 📝 Custom Cover Letter & Tailored Resume Generator
* **Goal**: Automate application personalization for high-suitability jobs.
* **Details**:
  - Add a **"Generate Cover Letter"** button inside the Job Details Modal.
  - When clicked, send your resume and the job description to the LLM to draft a highly tailored cover letter utilizing professional copywriting frameworks (e.g. AIDA format).
  - Add a **"Tailor Resume"** button to suggest specific bullet edits or phrasing adjustments in your resume to better match the target job's ATS (Applicant Tracking System) criteria.
  - Provide an inline text editor to copy or export the generated text as Markdown or PDF.

---

### 3. 🔍 Enhanced Search Strategy & Smart Filters
* **Goal**: Teach the scraper agent to target high-quality job postings.
* **Details**:
  - Expose UI checkboxes for:
    - **Remote Only** (adds `f_WT=2` filter to LinkedIn query URL).
    - **Date Posted**: Past 24 hours / Past week (adds `f_TPR` filter).
    - **Experience Level**: Entry, Mid, Senior (adds `f_E` filter).
  - Teach the `browser-use` agent to dynamically interact with LinkedIn filter drop-downs if URL query parameters fail to trigger.

---

### 4. 🤖 Auto-Apply / "Easy Apply" Assistant
* **Goal**: Speed up the application submission process for LinkedIn Easy Apply listings.
* **Details**:
  - For jobs that support LinkedIn "Easy Apply", teach the agent to click the button and traverse the application form.
  - When encountering standard questions (e.g., *"How many years of experience do you have with Python?"* or *"What is your expected salary?"*), let the LLM formulate answers based on your profile.
  - **Human-in-the-Loop Intercept**: Instead of submitting automatically, the agent will pause, display the drafted answers on the dashboard, and wait for your confirmation (or correction) before clicking "Submit".
