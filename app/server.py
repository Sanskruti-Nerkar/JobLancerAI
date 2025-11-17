import os
import sys
import time
import traceback
import uuid
import threading
import re
from pathlib import Path
from typing import Dict, List, Tuple

# Fix imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

try:
    from matching.matcher import JobMatcher
    from parsers.resume_parser import ResumeParser
    from scraping.job_scraper import JobScraperSession
    from applier.job_applier import LinkedInJobApplier as JobApplier
    print("✅ All modules imported successfully")
except ImportError as e:
    print(f"❌ IMPORT ERROR: {e}")
    try:
        from app.matching.matcher import JobMatcher
        from app.parsers.resume_parser import ResumeParser
        from app.scraping.job_scraper import JobScraperSession
        from app.applier.job_applier import LinkedInJobApplier as JobApplier
        print("✅ All modules imported successfully (with app. prefix)")
    except ImportError as e2:
        print(f"❌ Alternative import also failed: {e2}")
        raise

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
UPLOAD_DIR = PROJECT_ROOT / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf"}

# Global dict to store job session states
job_sessions = {}


class JobSession:
    """Tracks the state of a job search session"""
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.stage = 'initializing'
        self.message = 'Starting session...'
        self.progress = 0
        self.details = []
        self.results = None
        self.scraper_session = None
        self.resume_data = None
        self.resume_path = None
        self.matches = []
        self.login_confirmed = False
        self.questions_confirmed = False  # NEW: Track questions confirmation


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def serve_frontend():
        """Serve the single-page frontend."""
        try:
            return send_from_directory(BASE_DIR, "cute.html")
        except Exception as e:
            return f"Error: {e}", 500

    @app.get("/health")
    def health_check():
        return jsonify({"status": "ok"})

    @app.post("/api/match-jobs-async")
    def match_jobs_async():
        """Start async job matching process (NO AUTO-APPLY)"""
        print("=" * 60)
        print("📨 Received match-jobs-async request")
        print("=" * 60)
        
        try:
            payload, errors = _parse_form_data(request)
            if errors:
                return jsonify({"status": "error", "message": errors}), 400

            resume_file = request.files.get("resume")
            if not resume_file or not _allowed_file(resume_file.filename):
                return jsonify({"status": "error", "message": "Valid PDF resume required."}), 400

            # Create session
            session_id = str(uuid.uuid4())
            job_session = JobSession(session_id)
            job_sessions[session_id] = job_session

            # Save and parse resume
            saved_path = _save_resume(resume_file)
            resume_parser = ResumeParser(str(UPLOAD_DIR))
            resume_data = resume_parser.parse_resume(saved_path.name)

            if "error" in resume_data:
                saved_path.unlink(missing_ok=True)
                job_session.stage = 'error'
                job_session.message = resume_data["error"]
                return jsonify({"status": "error", "message": resume_data["error"]}), 400

            job_session.resume_data = resume_data
            job_session.resume_path = str(saved_path)

            # Start async processing (WITHOUT auto-apply)
            thread = threading.Thread(
                target=_process_job_search,
                args=(session_id, payload),
                daemon=True
            )
            thread.start()

            return jsonify({
                "status": "started",
                "session_id": session_id,
                "message": "Job search started"
            }), 200

        except Exception as exc:
            print(f"❌ EXCEPTION: {str(exc)}")
            traceback.print_exc()
            return jsonify({
                "status": "error",
                "message": f"Server error: {str(exc)}"
            }), 500

    @app.get("/api/job-status/<session_id>")
    def get_job_status(session_id: str):
        """Poll for job search status"""
        job_session = job_sessions.get(session_id)
        
        if not job_session:
            return jsonify({
                "status": "error",
                "message": "Session not found"
            }), 404

        response = {
            "stage": job_session.stage,
            "message": job_session.message,
            "progress": job_session.progress,
            "details": job_session.details,
        }

        if job_session.stage == 'complete':
            response["results"] = job_session.results

        return jsonify(response), 200

    @app.post("/api/confirm-login/<session_id>")
    def confirm_login(session_id: str):
        """User confirms they've logged into LinkedIn"""
        job_session = job_sessions.get(session_id)
        
        if not job_session:
            return jsonify({"status": "error", "message": "Session not found"}), 404

        if job_session.stage != 'waiting_login':
            return jsonify({"status": "error", "message": "Not waiting for login"}), 400

        job_session.login_confirmed = True
        job_session.stage = 'scraping'
        job_session.message = 'Login confirmed! Starting job search...'
        job_session.progress = 30

        return jsonify({"status": "ok"}), 200

    @app.post("/api/confirm-questions/<session_id>")
    def confirm_questions(session_id: str):
        """NEW: User confirms they've answered additional questions"""
        print(f"\n{'='*70}")
        print(f"[API] Received questions confirmation for session: {session_id}")
        print(f"{'='*70}\n")
        
        job_session = job_sessions.get(session_id)
        
        if not job_session:
            print(f"[API] ❌ Session not found: {session_id}")
            return jsonify({"status": "error", "message": "Session not found"}), 404

        # Set flag to continue application process
        print(f"[API] Setting questions_confirmed = True")
        job_session.questions_confirmed = True
        
        print(f"[API] ✅ Questions confirmed successfully\n")
        return jsonify({"status": "ok", "message": "Questions confirmed"}), 200

    @app.post("/api/batch-apply/<session_id>")
    def batch_apply(session_id: str):
        """Start batch application process based on threshold"""
        job_session = job_sessions.get(session_id)
        
        if not job_session:
            return jsonify({"status": "error", "message": "Session not found"}), 404

        if job_session.stage != 'complete':
            return jsonify({"status": "error", "message": "Job search not complete"}), 400

        try:
            data = request.get_json()
            threshold = data.get('threshold', 0.6)
            max_applications = data.get('max_applications', 10)
            
            # Start batch application in background thread
            job_session.stage = 'applying'
            job_session.apply_progress = {
                'stage': 'starting',
                'total': 0,
                'completed': 0,
                'applied': 0,
                'failed': 0,
                'current_job': None,
                'recent_results': [],
                'details': [],
                'waiting_for_questions': False,  # CRITICAL: Initialize this flag
                'current_job_title': None  # CRITICAL: Initialize this too
            }
            
            print(f"[Session {session_id}] ✅ Apply progress initialized with question flags")
            
            thread = threading.Thread(
                target=_apply_batch_jobs,
                args=(session_id, threshold, max_applications),
                daemon=True
            )
            thread.start()
            
            return jsonify({"status": "started", "message": "Batch application started"}), 200

        except Exception as exc:
            print(f"❌ Batch apply error: {str(exc)}")
            traceback.print_exc()
            return jsonify({"status": "error", "message": str(exc)}), 500

    @app.get("/api/apply-status/<session_id>")
    def get_apply_status(session_id: str):
        """Get batch application progress"""
        job_session = job_sessions.get(session_id)
        
        if not job_session:
            return jsonify({"status": "error", "message": "Session not found"}), 404

        if not hasattr(job_session, 'apply_progress'):
            return jsonify({"status": "error", "message": "No application in progress"}), 404

        return jsonify(job_session.apply_progress), 200

    @app.get("/<filename>")
    def serve_static(filename):
        """Serve static files like images from the app directory."""
        # Skip API routes and health check
        if filename.startswith('api/') or filename in ['health']:
            return "Not found", 404
        # Only serve specific static file types
        if filename.endswith(('.jpg', '.jpeg', '.png', '.gif', '.ico', '.svg', '.css', '.js')):
            try:
                return send_from_directory(BASE_DIR, filename)
            except FileNotFoundError:
                return "File not found", 404
        # For other files, return 404 to avoid conflicts
        return "Not found", 404

    return app


def _process_job_search(session_id: str, payload: Dict):
    """Background thread to process job search (NO AUTO-APPLY)"""
    job_session = job_sessions[session_id]
    session = None
    
    try:
        # Initialize driver
        job_session.stage = 'initializing'
        job_session.message = 'Opening Chrome browser...'
        job_session.progress = 10
        job_session.details = [
            'Chrome will open in a new window',
            'Please log into LinkedIn when the browser opens'
        ]

        session = JobScraperSession()
        job_session.scraper_session = session
        session.initialize_driver()

        # Wait for login
        job_session.stage = 'waiting_login'
        job_session.message = 'Please log into LinkedIn, then click Continue'
        job_session.progress = 20
        job_session.details = [
            'A Chrome window has opened',
            'Log into LinkedIn',
            'Click the Continue button below'
        ]

        while not job_session.login_confirmed:
            if job_session.stage == 'error':
                return
            threading.Event().wait(1)

        session.login_to_linkedin(wait_for_manual_login=False)

        # Search jobs
        job_session.stage = 'scraping'
        job_session.message = f'Searching LinkedIn for "{payload["job_title"]}"...'
        job_session.progress = 40
        job_session.details = [
            f'Scraping {payload["num_pages"]} pages',
            'Looking for Easy Apply jobs'
        ]

        jobs = session.search_jobs(
            query=payload['job_title'],
            location=payload.get('location', ''),
            num_pages=payload['num_pages'],
            fetch_details=payload['fetch_details']
        )

        if not jobs:
            job_session.stage = 'complete'
            job_session.message = 'No jobs found'
            job_session.progress = 100
            job_session.results = {
                "status": "no_jobs",
                "message": "No Easy Apply jobs found",
                "matches": []
            }
            session.cleanup()
            return

        # Match jobs
        job_session.stage = 'matching'
        job_session.message = f'Found {len(jobs)} jobs! Analyzing matches...'
        job_session.progress = 60

        processed_jobs = _process_jobs_for_matching(jobs)
        matcher = JobMatcher()
        resume_text = _compose_resume_text(job_session.resume_data)
        
        matches = matcher.get_top_matches(
            processed_jobs,
            resume_text,
            top_n=payload['top_n'],
            min_score=payload['min_score_filter'],
            resume_skills=job_session.resume_data.get('technical_skills', [])
        )

        job_session.matches = matches
        job_session.progress = 100

        # Complete - NO AUTO-APPLY, just show matches
        job_session.stage = 'complete'
        job_session.message = f'Found {len(matches)} matching jobs! Review and apply.'
        job_session.results = {
            "status": "success",
            "jobs_found": len(jobs),
            "matches_found": len(matches),
            "resume": _summarize_resume(job_session.resume_data),
            "matches": _format_matches(matches)
        }

        print(f"[Session {session_id}] Keeping browser and resume file for applications")

    except Exception as exc:
        print(f"[Session {session_id}] ERROR: {str(exc)}")
        traceback.print_exc()
        job_session.stage = 'error'
        job_session.message = f'Error: {str(exc)}'
        job_session.progress = 0
        
        if session:
            try:
                session.cleanup()
            except:
                pass


def _apply_batch_jobs(session_id: str, threshold: float, max_applications: int):
    """Background thread to apply to multiple jobs based on threshold"""
    job_session = job_sessions[session_id]
    
    try:
        # Filter matches by threshold
        qualifying_matches = [
            match for match in job_session.matches 
            if match['final_score'] >= threshold
        ][:max_applications]
        
        job_session.apply_progress['total'] = len(qualifying_matches)
        job_session.apply_progress['stage'] = 'applying'
        
        print(f"[Session {session_id}] Applying to {len(qualifying_matches)} jobs with threshold {threshold}")
        
        if not job_session.scraper_session or not job_session.scraper_session.driver:
            job_session.apply_progress['stage'] = 'error'
            job_session.apply_progress['error'] = 'Browser session expired'
            return
        
        # Verify resume file exists
        if not job_session.resume_path or not os.path.exists(job_session.resume_path):
            job_session.apply_progress['stage'] = 'error'
            job_session.apply_progress['error'] = f'Resume file not found: {job_session.resume_path}'
            print(f"[Session {session_id}] ❌ Resume file missing!")
            return
        
        print(f"[Session {session_id}] ✅ Resume file exists: {job_session.resume_path}")
        
        # Create applier with callback for questions
        def questions_callback(job_title: str):
            """Callback when additional questions are detected"""
            print(f"\n{'='*70}")
            print(f"[Session {session_id}] 🚨 QUESTIONS CALLBACK TRIGGERED")
            print(f"[Session {session_id}] Job: {job_title}")
            print(f"{'='*70}\n")
            
            # CRITICAL: Update the progress object that's being polled
            print(f"[Session {session_id}] Setting waiting_for_questions = True")
            job_session.apply_progress['waiting_for_questions'] = True
            job_session.apply_progress['current_job_title'] = job_title
            job_session.questions_confirmed = False
            
            print(f"[Session {session_id}] Current apply_progress state:")
            print(f"  - waiting_for_questions: {job_session.apply_progress['waiting_for_questions']}")
            print(f"  - current_job_title: {job_session.apply_progress['current_job_title']}")
            print(f"[Session {session_id}] 🔔 Modal flag set - UI should show modal now")
            
            # Wait for user confirmation
            timeout = 300  # 5 minutes timeout
            elapsed = 0
            print(f"[Session {session_id}] ⏳ Waiting for user to answer questions...")
            
            while not job_session.questions_confirmed and elapsed < timeout:
                time.sleep(1)
                elapsed += 1
                if elapsed % 10 == 0:  # Log every 10 seconds
                    print(f"[Session {session_id}] Still waiting... ({elapsed}s)")
            
            if elapsed >= timeout:
                print(f"[Session {session_id}] ⏱️ Timeout waiting for questions confirmation")
            else:
                print(f"[Session {session_id}] ✅ Questions confirmed by user after {elapsed}s")
            
            # Reset flag
            print(f"[Session {session_id}] Resetting waiting flag")
            job_session.apply_progress['waiting_for_questions'] = False
            job_session.apply_progress['current_job_title'] = None
            print(f"[Session {session_id}] Flag reset - continuing application\n")
        
        applier = JobApplier(
            session=job_session.scraper_session,
            resume_data=job_session.resume_data,
            resume_path=job_session.resume_path,
            max_apply=len(qualifying_matches),
            min_score=0.0,  # Already filtered by threshold
            questions_callback=questions_callback  # NEW: Pass callback
        )
        
        # Apply with progress tracking
        applied = 0
        failed = 0
        
        for idx, match in enumerate(qualifying_matches):
            job = match['job']
            job_session.apply_progress['current_job'] = job.get('title', 'Unknown')
            job_session.apply_progress['completed'] = idx
            
            print(f"[Session {session_id}] Applying to: {job.get('title')}")
            
            try:
                # Apply to single job
                summary = applier.apply_to_jobs([match])
                
                result = {
                    'job_title': job.get('title'),
                    'company': job.get('company'),
                    'success': summary['applied'] > 0,
                    'error': None if summary['applied'] > 0 else 'Failed'
                }
                
                if summary['applied'] > 0:
                    applied += 1
                else:
                    failed += 1
                    if summary['details']:
                        result['error'] = summary['details'][0].get('error', 'Failed')
                
                job_session.apply_progress['recent_results'].append(result)
                job_session.apply_progress['details'].append(result)
                
                # Keep only last 5 recent results for display
                if len(job_session.apply_progress['recent_results']) > 5:
                    job_session.apply_progress['recent_results'].pop(0)
                
                job_session.apply_progress['applied'] = applied
                job_session.apply_progress['failed'] = failed
                
                time.sleep(2)
                
            except Exception as e:
                print(f"[Session {session_id}] Error applying to {job.get('title')}: {str(e)}")
                failed += 1
                job_session.apply_progress['failed'] = failed
                job_session.apply_progress['recent_results'].append({
                    'job_title': job.get('title'),
                    'success': False,
                    'error': str(e)[:100]
                })
        
        # Complete
        job_session.apply_progress['stage'] = 'complete'
        job_session.apply_progress['completed'] = len(qualifying_matches)
        job_session.apply_progress['current_job'] = None
        job_session.apply_progress['results'] = {
            'attempted': len(qualifying_matches),
            'applied': applied,
            'failed': failed,
            'details': job_session.apply_progress['details']
        }
        
        print(f"[Session {session_id}] Batch apply complete: {applied} applied, {failed} failed")
        
        # Cleanup resume file
        if job_session.resume_path and os.path.exists(job_session.resume_path):
            try:
                os.unlink(job_session.resume_path)
                print(f"[Session {session_id}] Deleted resume file")
            except Exception as e:
                print(f"[Session {session_id}] Could not delete resume: {e}")
        
    except Exception as exc:
        print(f"[Session {session_id}] Batch apply error: {str(exc)}")
        traceback.print_exc()
        job_session.apply_progress['stage'] = 'error'
        job_session.apply_progress['error'] = str(exc)


def _parse_form_data(req) -> Tuple[Dict, str]:
    try:
        job_title = (req.form.get("job_title") or "").strip()
        location = (req.form.get("location") or "").strip()
        num_pages = int(req.form.get("num_pages", 1))
        fetch_details = req.form.get("fetch_details", "false").lower() == "true"
        top_n = int(req.form.get("top_n", 15))
        min_score_filter = float(req.form.get("min_score_filter", 0.25))
    except ValueError:
        return {}, "Invalid numeric value in form data."

    if not job_title:
        return {}, "Job title is required."

    num_pages = max(1, min(num_pages, 5))
    top_n = max(5, min(top_n, 25))
    min_score_filter = max(0.0, min(min_score_filter, 1.0))

    payload = {
        "job_title": job_title,
        "location": location,
        "num_pages": num_pages,
        "fetch_details": fetch_details,
        "top_n": top_n,
        "min_score_filter": min_score_filter
    }
    return payload, ""


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _save_resume(file_storage) -> Path:
    safe_name = secure_filename(file_storage.filename) or "resume.pdf"
    unique_name = f"{Path(safe_name).stem}_{uuid.uuid4().hex}.pdf"
    save_path = UPLOAD_DIR / unique_name
    file_storage.save(save_path)
    return save_path


def _compose_resume_text(resume: Dict) -> str:
    skills = ", ".join(resume.get("technical_skills", []))
    experience = resume.get("years_of_experience") or "N/A"
    name = resume.get("name", "Unknown")
    return f"""
    {name}
    Skills: {skills}
    Experience: {experience} years
    """


def _process_jobs_for_matching(jobs: List[Dict]) -> List[Dict]:
    processed = []
    for job in jobs:
        processed.append({
            "title": job.get("title") or "Unknown",
            "company": job.get("company") or "Unknown",
            "location": job.get("location") or "Remote",
            "link": job.get("link") or "",
            "summary": job.get("summary") or "",
            "key_skills": job.get("key_skills", []),
            "platform": job.get("platform", "LinkedIn")
        })
    return processed


def _summarize_resume(resume: Dict) -> Dict:
    return {
        "name": resume.get("name"),
        "email": resume.get("email"),
        "phone": resume.get("phone"),
        "technical_skills": resume.get("technical_skills", []),
        "years_of_experience": resume.get("years_of_experience"),
        "education": resume.get("education", [])
    }


def _format_matches(matches: List[Dict]) -> List[Dict]:
    formatted = []
    for match in matches:
        job = match.get("job", {})
        
        # BACKUP: Clean title if still duplicated
        title = job.get("title", "")
        if title:
            # Method 1: Check for word-level duplicates
            words = title.split()
            if len(words) >= 4:
                # Check if first half words repeat
                half = len(words) // 2
                first_half = words[:half]
                second_half = words[half:half*2] if half*2 <= len(words) else words[half:]
                
                if first_half == second_half:
                    # Remove duplicate, keep any remaining words
                    remaining = words[half*2:] if half*2 < len(words) else []
                    title = ' '.join(first_half + remaining)
                else:
                    # Check for repeated phrases with extra text
                    # Pattern: "Python Developer Python Developer with verification"
                    for i in range(len(words) - 3):
                        for j in range(i + 2, len(words)):
                            if words[i:j] == words[j:j+(j-i)]:
                                # Found duplicate, remove it
                                title = ' '.join(words[:j] + words[j+(j-i):])
                                break
                        else:
                            continue
                        break
            
            # Method 2: Regex pattern for common duplicates
            # Pattern like "Developer Developer" or "Python Developer Python Developer"
            patterns = [
                (r'\b([A-Za-z]+\s+Developer)\s+\1\b', r'\1'),
                (r'\b([A-Za-z]+\s+Engineer)\s+\1\b', r'\1'),
                (r'\b(Python\s+Developer)\s+\1\b', r'\1'),
            ]
            for pattern, replacement in patterns:
                title = re.sub(pattern, replacement, title, flags=re.IGNORECASE)
        
        # Clean company name
        company = job.get("company", "Company not specified")
        if company and company.strip() and company != "Company not specified":
            company = re.sub(r'\s+', ' ', company.strip())
        
        formatted.append({
            "title": title,
            "company": company,
            "location": job.get("location"),
            "link": job.get("link"),
            "platform": job.get("platform", "LinkedIn"),
            "final_score": round(match.get("final_score", 0) or 0, 4),
            "similarity_score": round(match.get("similarity_score", 0) or 0, 4),
            "experience_score": round(match.get("experience_score", 0) or 0, 4),
            "skills_score": round(match.get("skills_score", 0) or 0, 4),
            "title_relevance": round(match.get("title_relevance", 0) or 0, 4),
            "skill_match_percentage": round(match.get("skill_match_percentage", 0.0) or 0.0, 2),
            "matched_skills": match.get("matched_skills", [])[:10],
            "missing_skills": match.get("missing_skills", [])[:10]
        })
    return formatted


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)