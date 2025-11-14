import os
import traceback
import uuid
from pathlib import Path
from typing import Dict, List, Tuple

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

from app.matching.matcher import JobMatcher
from app.parsers.resume_parser import ResumeParser
from app.scraping.job_scraper import JobScraperSession
from app.applier.job_applier import LinkedInJobApplier as JobApplier

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
UPLOAD_DIR = PROJECT_ROOT / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf"}


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def serve_frontend():
        """Serve the single-page frontend."""
        return send_from_directory(BASE_DIR, "cute.html")

    @app.get("/health")
    def health_check():
        return jsonify({"status": "ok"})

    @app.post("/api/match-jobs")
    def match_jobs():
        """Main endpoint: accepts resume + search params, returns matches."""
        try:
            payload, errors = _parse_form_data(request)
            if errors:
                return jsonify({"status": "error", "message": errors}), 400

            resume_file = request.files.get("resume")
            if not resume_file:
                return jsonify({"status": "error", "message": "Resume file is required."}), 400

            if not _allowed_file(resume_file.filename):
                return jsonify({"status": "error", "message": "Only PDF resumes are supported."}), 400

            saved_path = _save_resume(resume_file)
            resume_parser = ResumeParser(str(UPLOAD_DIR))
            resume_data = resume_parser.parse_resume(saved_path.name)

            if "error" in resume_data:
                saved_path.unlink(missing_ok=True)
                return jsonify({"status": "error", "message": resume_data["error"]}), 400

            resume_text = _compose_resume_text(resume_data)

            session = JobScraperSession()
            matches: List[Dict] = []
            jobs = []
            application_summary = None
            try:
                session.initialize_driver()
                session.login_to_linkedin(wait_for_manual_login=True)

                jobs = session.search_jobs(
                    query=payload["job_title"],
                    location=payload.get("location", ""),
                    num_pages=payload["num_pages"],
                    fetch_details=payload["fetch_details"]
                )

                if not jobs:
                    return jsonify({
                        "status": "no_jobs",
                        "message": "No Easy Apply jobs were found. Try changing the filters."
                    }), 200

                processed_jobs = _process_jobs_for_matching(jobs)
                matcher = JobMatcher()
                matches = matcher.get_top_matches(
                    processed_jobs,
                    resume_text,
                    top_n=payload["top_n"],
                    min_score=payload["min_score_filter"],
                    resume_skills=resume_data.get("technical_skills", [])
                )

                if payload["auto_apply"] and matches:
                    resume_path = str(saved_path)
                    application_summary = _apply_to_jobs(
                        session=session,
                        resume_data=resume_data,
                        resume_path=resume_path,
                        matches=matches,
                        min_score=payload["apply_score_threshold"],
                        max_apply=payload["apply_limit"]
                    )
            finally:
                session.cleanup()
                saved_path.unlink(missing_ok=True)

            response = {
                "status": "success",
                "jobs_found": len(jobs),
                "matches_found": len(matches),
                "resume": _summarize_resume(resume_data),
                "matches": _format_matches(matches),
                "application_summary": application_summary,
                "messages": _build_messages(payload)
            }
            return jsonify(response), 200

        except Exception as exc:
            traceback.print_exc()
            return jsonify({
                "status": "error",
                "message": str(exc)
            }), 500

    return app


def _parse_form_data(req) -> Tuple[Dict, str]:
    try:
        job_title = (req.form.get("job_title") or "").strip()
        location = (req.form.get("location") or "").strip()
        num_pages = int(req.form.get("num_pages", 1))
        fetch_details = req.form.get("fetch_details", "false").lower() == "true"
        top_n = int(req.form.get("top_n", 15))
        min_score_filter = float(req.form.get("min_score_filter", 0.25))
        auto_apply = req.form.get("auto_apply", "false").lower() == "true"
        apply_score_threshold = float(req.form.get("apply_score_threshold", 0.6))
        apply_limit = int(req.form.get("apply_limit", 10))
    except ValueError:
        return {}, "Invalid numeric value in form data."

    if not job_title:
        return {}, "Job title is required."

    num_pages = max(1, min(num_pages, 5))
    top_n = max(5, min(top_n, 25))
    min_score_filter = max(0.0, min(min_score_filter, 1.0))
    apply_score_threshold = max(0.0, min(apply_score_threshold, 1.0))
    apply_limit = max(1, min(apply_limit, 30))

    payload = {
        "job_title": job_title,
        "location": location,
        "num_pages": num_pages,
        "fetch_details": fetch_details,
        "top_n": top_n,
        "min_score_filter": min_score_filter,
        "auto_apply": auto_apply,
        "apply_score_threshold": apply_score_threshold,
        "apply_limit": apply_limit
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
        formatted.append({
            "title": job.get("title"),
            "company": job.get("company"),
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


def _apply_to_jobs(
    session: JobScraperSession,
    resume_data: Dict,
    resume_path: str,
    matches: List[Dict],
    min_score: float,
    max_apply: int
) -> Dict:
    applier = JobApplier(
        session=session,
        resume_data=resume_data,
        resume_path=resume_path,
        max_apply=max_apply,
        min_score=min_score
    )
    summary = applier.apply_to_jobs(matches)
    summary["success_rate"] = (
        (summary.get("applied", 0) + summary.get("external_applied", 0))
        / summary["attempted"] * 100
    ) if summary.get("attempted") else 0
    return summary


def _build_messages(payload: Dict) -> List[str]:
    messages = [
        "Chrome will open for LinkedIn scraping. Complete login when prompted in the console.",
        f"Scraping up to {payload['num_pages']} LinkedIn pages for '{payload['job_title']}'."
    ]
    if payload["fetch_details"]:
        messages.append("Detailed scraping is ON (slower but richer job descriptions).")
    if payload["auto_apply"]:
        messages.append(
            f"Auto-apply enabled. Minimum score {payload['apply_score_threshold']*100:.0f}% "
            f"with max {payload['apply_limit']} Easy Apply submissions."
        )
    return messages


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

