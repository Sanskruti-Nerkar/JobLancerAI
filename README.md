# <div align="center"><img src="joblancer-logo.png" width="140"></div>
# <div align="center">💼 JobLancer – AI-Powered Job Application Agent</div>

### <div align="center">Automated job search, intelligent job-resume matching, and hands-free auto-apply for LinkedIn Easy Apply.</div>

---

## 🚀 About JobLancer

JobLancer is an end-to-end AI-powered system that **reads your resume, scrapes job listings, matches jobs using ML, and auto-applies** to high-scoring jobs using LinkedIn Easy Apply.

It acts as your personal job-search agent — eliminating repetitive tasks and helping you land interviews faster.

---

## 🎯 Features

### 🔍 1. Smart Resume Parsing
Automatically extracts:
- Skills
- Keywords
- Experience
- Contact details
- Education
- Technical expertise

### 📡 2. Real-Time LinkedIn Scraping
JobLancer:
- Opens Chrome automatically  
- Logs into LinkedIn  
- Scrapes Easy-Apply jobs  
- Collects job titles, companies, skills & links  

### 🤖 3. AI Matching Engine
Using ML & NLP:
- TF-IDF similarity  
- Skill extraction via **job_description_parser.py**  
- Experience scoring  
- Title relevance  
- Location matching  
- Weighted scoring system  

### ⚙️ 4. Autonomous Auto-Apply Agent
Fully automated LinkedIn Easy Apply:
- Clicks Easy Apply  
- Fills contact info  
- Uploads resume  
- Detects additional questions  
- Pauses until user completes them  
- Submits job applications  
- Tracks applied/failed attempts  

### 🎨 5. Modern Frontend Dashboard
Includes:
- Drag & drop resume upload  
- Real-time progress  
- Match cards  
- Auto-apply controls  
- Question-detection modal  
- Light/Dark mode  
- Animated UI  

---

## 🏗️ System Architecture

```
Frontend (cute.html)
        │
        ▼
  Flask REST API (server.py)
        │
 ┌──────┴─────────┬───────────────────────┬─────────────────────────┐
 │ ResumeParser    │ JobMatcher            │ LinkedInJobApplier       │
 │ (Extract info)  │ (AI Matching ML/NLP)  │ (Automation via Selenium)│
 └─────────────────┴───────────────────────┴─────────────────────────┘
```

---

## 🛠️ Tech Stack

### **Frontend**
- HTML5 + CSS3  
- Vanilla JS  
- Animations, modals, dynamic dashboards  

### **Backend**
- Python Flask  
- Multi-threaded tasks  
- Real-time polling & state management  

### **AI/ML**
- Scikit-learn (TF-IDF Vectorizer)  
- Cosine Similarity  
- JD Skill Extraction (job_description_parser.py)  
- Experience/location matching  

### **Automation**
- Selenium WebDriver  
- ChromeDriver  

---

## 📦 Project Structure

```
project/
│
├── app/
│   ├── applier/
│   │   └── job_applier.py
│   ├── matching/
│   │   └── matcher.py
│   ├── scraping/
│   │   └── job_scraper.py
│   ├── parsers/
│   │   ├── resume_parser.py
│   │   └── job_description_parser.py
│
├── server.py
├── main.py
├── cute.html
├── joblancer-logo.png
├── uploads/
└── requirements.txt
```

---

## 🔧 Setup & Installation

### 1️⃣ Clone the repository
```bash
git clone https://github.com/<your-username>/joblancer.git
cd joblancer
```

### 2️⃣ Install dependencies using your existing requirements.txt
```bash
pip install -r requirements.txt
```

(This file already contains Selenium, Flask, Scikit-Learn, NumPy, etc.)

### 3️⃣ Install Google Chrome + ChromeDriver
Required for automation.

Ensure ChromeDriver version matches your Chrome browser.

Add ChromeDriver to PATH.

---

## ▶️ Run the Web Application

```bash
python server.py
```

Then open:

```
http://localhost:5000
```

The system will automatically launch Chrome when it begins scraping.

---

## ▶️ Run the CLI Version (Optional)

```bash
python main.py
```

The CLI includes:
- Terminal-based matching  
- Optional auto-apply mode  

---

## 🧠 Job Matching Breakdown

| Score Component        | Weight |
|------------------------|--------|
| TF-IDF Text Similarity | 30%    |
| Skill Match Accuracy   | 35%    |
| Experience Match       | 20%    |
| Location Match         | 10%    |
| Title Relevance        | 5%     |

The final score is normalized and used to rank jobs.

---

## 🧩 Auto-Apply Flow

1. Opens job link  
2. Detects Easy Apply  
3. Fills contact info  
4. Selects / uploads resume  
5. Detects additional questions  
6. Pauses & shows modal  
7. Continues auto-apply after user confirmation  
8. Tracks applied/failed jobs  

---

## ⚠️ Disclaimer

This project uses automation on LinkedIn.  
Such automation may violate platform terms.  
Use responsibly and at your own risk.

---
