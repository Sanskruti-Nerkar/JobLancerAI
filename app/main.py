import os
import sys
import time
from typing import Dict, List

# Get the absolute path of the app directory
app_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(app_dir)

# Add both app directory and project root to Python path
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from app.matching.matcher import JobMatcher
    from app.parsers.resume_parser import ResumeParser
    from app.scraping.job_scraper import JobScraperSession
    from app.applier.job_applier import LinkedInJobApplier as JobApplier
    HAS_SESSION = True
except ImportError as e:
    print(f"⚠️  Import error: {str(e)}")
    print(f"Current sys.path: {sys.path}")
    HAS_SESSION = False


def get_user_input() -> Dict[str, str]:
    """Get search preferences"""
    print("\n=== LinkedIn Job Search Parameters ===")
    
    job_title = input("\nJob Title (e.g., 'AI Engineer', 'Python Developer'): ").strip()
    while not job_title:
        job_title = input("Job Title: ").strip()
    
    location = input("Location (e.g., 'Mumbai', 'Remote') [Optional]: ").strip()
    
    num_pages = input("Pages to scrape (1-5, LinkedIn limit): ").strip()
    while not num_pages.isdigit() or not (1 <= int(num_pages) <= 5):
        num_pages = input("Pages (1-5): ").strip() or "1"
    
    return {
        'job_title': job_title,
        'location': location,
        'num_pages': int(num_pages)
    }


def setup_resume_directory() -> str:
    """Get resume directory"""
    while True:
        resume_dir = input("\nResume directory path: ").strip()
        if os.path.isdir(resume_dir):
            pdfs = [f for f in os.listdir(resume_dir) if f.lower().endswith('.pdf')]
            if pdfs:
                return resume_dir
            print("❌ No PDF files found!")
        else:
            print("❌ Invalid path!")


def process_jobs(jobs: List[Dict]) -> List[Dict]:
    """Process LinkedIn job listings"""
    processed = []
    total = len(jobs)
    print(f"\nProcessing {total} LinkedIn jobs...")
    
    for idx, job in enumerate(jobs, 1):
        if idx % 5 == 0 or idx == total:
            print(f"  {idx}/{total} processed")
        
        processed.append({
            'title': job.get('title') or 'Unknown',
            'company': job.get('company') or 'Unknown',
            'location': job.get('location') or 'Remote',
            'link': job.get('link') or '',
            'summary': '',  # LinkedIn doesn't provide full summary in search
            'key_skills': job.get('key_skills', []),
            'platform': 'LinkedIn'
        })
    
    print(f"✅ {len(processed)} jobs ready")
    return processed


def display_matches(matches: List[Dict], resume_name: str):
    """Display job matches"""
    print(f"\n{'='*80}")
    print(f"TOP LINKEDIN MATCHES FOR: {resume_name}")
    print(f"{'='*80}")
    
    if not matches:
        print("No matches found")
        return
    
    print(f"Found {len(matches)} matching jobs\n")
    
    for i, match in enumerate(matches, 1):
        job = match['job']
        print(f"{'='*60}")
        print(f"#{i} - {job.get('title')}")
        print(f"{'='*60}")
        print(f"Company: {job.get('company')}")
        print(f"Location: {job.get('location')}")
        print(f"Platform: LinkedIn (Easy Apply)")
        
        print(f"\n📊 Match Score: {match['final_score']:.1%}")
        print(f"   ├─ Content: {match['similarity_score']:.1%}")
        print(f"   ├─ Experience: {match['experience_score']:.1%}")
        print(f"   ├─ Skills: {match['skills_score']:.1%}")
        print(f"   └─ Title: {match.get('title_relevance', 0):.1%}")
        
        print(f"\n🎯 Skills Match: {match.get('skill_match_percentage', 0):.1f}%")
        if match.get('matched_skills'):
            skills_preview = ', '.join(match['matched_skills'][:5])
            print(f"   ✅ Matched: {skills_preview}")
            if len(match['matched_skills']) > 5:
                print(f"       ... and {len(match['matched_skills']) - 5} more")
        
        if match.get('missing_skills'):
            missing_preview = ', '.join(match['missing_skills'][:3])
            print(f"   ⚠️  Missing: {missing_preview}")
            if len(match['missing_skills']) > 3:
                print(f"       ... and {len(match['missing_skills']) - 3} more")
        
        print(f"\n🔗 Link: {job.get('link', 'N/A')[:70]}...")
        print(f"\n{'─'*60}")


def main():
    print("\n" + "="*70)
    print("🔵 LINKEDIN JOB-RESUME MATCHING & AUTO-APPLY SYSTEM")
    print("="*70)
    print("This system uses LinkedIn Easy Apply for applications")
    print("="*70 + "\n")
    
    if not HAS_SESSION:
        print("❌ LinkedIn modules not available")
        return
    
    # Get preferences
    prefs = get_user_input()
    
    # Ask about detail fetching
    print("\n" + "="*70)
    print("SCRAPING MODE")
    print("="*70)
    print("FAST MODE: Quick scraping from search results (3-5 seconds)")
    print("DETAILED MODE: Visits each job page for full info (30-60 seconds)")
    print("="*70)
    detail_choice = input("\nUse DETAILED mode? (y/n, default: n): ").strip().lower()
    fetch_details = (detail_choice == 'y')
    
    # Create session and scrape LinkedIn
    print(f"\n🔍 Searching LinkedIn for '{prefs['job_title']}'...")
    if prefs['location']:
        print(f"📍 Location: {prefs['location']}")
    print("\n⚠️  IMPORTANT: Chrome will open - LOGIN TO LINKEDIN!")
    print("💡 TIP: Make sure you're logged into LinkedIn for Easy Apply")
    
    session = None
    
    try:
        # Initialize session - DON'T use context manager yet
        print("\n" + "="*70)
        print("🚀 STARTING SESSION")
        print("="*70)
        session = JobScraperSession()
        session.initialize_driver()
        session.login_to_linkedin(wait_for_manual_login=True)
        
        # Verify driver is still active
        if not session.driver:
            print("❌ Driver not initialized properly")
            return
            
        print("\n✅ Session established successfully")
        
        # Search jobs
        jobs = session.search_jobs(
            query=prefs['job_title'],
            location=prefs.get('location', ''),
            num_pages=prefs['num_pages'],
            fetch_details=fetch_details  # New parameter
        )
        
        if not jobs:
            print("❌ No jobs found!")
            return
        
        print(f"✅ Found {len(jobs)} LinkedIn jobs with Easy Apply")
        
        # Parse resumes
        resume_dir = setup_resume_directory()
        parser = ResumeParser(resume_dir)
        resumes = parser.parse_resumes()
        
        if not resumes:
            print("❌ No resumes found!")
            return
        
        # Process and match
        processed_jobs = process_jobs(jobs)
        matcher = JobMatcher()
        
        for resume in resumes:
            if "error" in resume:
                continue
            
            print(f"\n{'='*70}")
            print(f"📄 Processing resume: {resume.get('name', 'Unknown')}")
            print(f"{'='*70}")
            
            resume_text = f"""
            {resume.get('name', '')}
            Skills: {', '.join(resume.get('technical_skills', []))}
            Experience: {resume.get('years_of_experience', '')} years
            """
            
            matches = matcher.get_top_matches(
                processed_jobs,
                resume_text,
                top_n=15,
                min_score=0.25,
                resume_skills=resume.get('technical_skills', [])
            )
            
            display_matches(matches, resume.get('name', 'Unknown'))
            
            # Apply to jobs
            if matches and session and session.driver:
                print("\n" + "="*70)
                choice = input("🚀 Apply to jobs using Easy Apply? (y/n): ").strip().lower()
                
                if choice == 'y':
                    # Verify driver is still active before applying
                    try:
                        # Test if driver is still responsive
                        current_url = session.driver.current_url
                        print(f"✅ Driver active (current URL: {current_url[:50]}...)")
                    except Exception as e:
                        print(f"❌ Driver session lost: {str(e)}")
                        print("⚠️  Please restart the program")
                        return
                    
                    try:
                        threshold = float(input("Min score (0-1, e.g. 0.6 for 60%): ").strip() or "0.6")
                    except:
                        threshold = 0.6
                    
                    try:
                        max_apply = int(input("Max applications (default 10): ").strip() or "10")
                    except:
                        max_apply = 10
                    
                    print("\n" + "="*70)
                    print("🚀 STARTING LINKEDIN EASY APPLY APPLICATIONS")
                    print("="*70)
                    print("✅ Using same session (you're already logged in!)")
                    print("💡 NOTE: LinkedIn may ask security questions")
                    print("⏱️  Applications may take 30-60 seconds each")
                    print("="*70 + "\n")
                    
                    input("Press ENTER to start applying...")
                    
                    # Verify driver one more time before creating applier
                    try:
                        session.driver.current_url
                    except Exception as e:
                        print(f"❌ Driver session lost before applying: {str(e)}")
                        print("⚠️  Please restart the program")
                        return
                    
                    # Create applier with existing session
                    try:
                        # Prepare resume data for applier
                        resume_file_path = os.path.join(resume_dir, resume.get('file_name', ''))
                        
                        if not os.path.exists(resume_file_path):
                            print(f"❌ Resume file not found: {resume_file_path}")
                            continue
                        
                        applier = JobApplier(
                            session=session,
                            resume_data=resume,
                            resume_path=resume_file_path,
                            max_apply=max_apply,
                            min_score=threshold
                        )
                        summary = applier.apply_to_jobs(matches)
                        
                        print("\n" + "="*70)
                        print("📊 FINAL APPLICATION SUMMARY")
                        print("="*70)
                        print(f"Attempted:           {summary['attempted']}")
                        print(f"✅ Easy Apply:       {summary['applied']}")
                        print(f"🔗 External Apply:   {summary.get('external_applied', 0)}")
                        print(f"❌ Failed:           {summary['failed']}")
                        print(f"📉 Low Score:        {summary['skipped']}")
                        print("="*70)
                        
                        total_applied = summary['applied'] + summary.get('external_applied', 0)
                        if total_applied > 0:
                            success_rate = (total_applied / summary['attempted'] * 100) if summary['attempted'] > 0 else 0
                            print(f"\n🎉 SUCCESS! Total applications: {total_applied}")
                            print(f"   - Easy Apply (completed): {summary['applied']}")
                            print(f"   - External (company site): {summary.get('external_applied', 0)}")
                            print(f"Success Rate: {success_rate:.1f}%")
                        
                        if summary['details']:
                            print(f"\nTop 10 Results:")
                            for i, r in enumerate(summary['details'][:10], 1):
                                app_type = r.get('application_type', '')
                                
                                if r.get('applied'):
                                    if 'Easy' in app_type:
                                        status = '✅ EASY APPLY'
                                    else:
                                        status = '🔗 EXTERNAL'
                                else:
                                    status = '❌ FAILED'
                                
                                title = r.get('title', 'Unknown')[:45]
                                print(f"{i:2}. {title} - {status}")
                                if r.get('error'):
                                    print(f"    Reason: {r['error'][:60]}")
                    except Exception as e:
                        print(f"\n❌ Error during application process: {str(e)}")
                        import traceback
                        traceback.print_exc()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Process cancelled by user")
    except Exception as e:
        print(f"\n\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        if session:
            print("\n🧹 Cleaning up...")
            session.cleanup()
        print("\n✅ Thank you for using the LinkedIn Job Matching System!")


if __name__ == "__main__":
    main()