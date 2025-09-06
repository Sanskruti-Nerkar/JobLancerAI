import os
from typing import Dict, List
from app.scraping.job_scraper import scrape_jobs
from app.parsers.resume_parser import ResumeParser
from app.parsers.job_description_parser import parse_job_description
from app.matching.matcher import JobMatcher

def get_user_input() -> Dict[str, str]:
    """Get search preferences from user"""
    print("\n=== Job Search Parameters ===")
    print("Enter the following details to search for jobs:")
    
    job_title = input("\nJob Title (e.g., python developer, data scientist): ").strip()
    while not job_title:
        print("Job title cannot be empty!")
        job_title = input("Job Title: ").strip()
    
    num_pages = input("Number of pages to scrape (1-20): ").strip()
    while not num_pages.isdigit() or not (1 <= int(num_pages) <= 20):
        print("Please enter a number between 1 and 20!")
        num_pages = input("Number of pages to scrape (1-20): ").strip()
    
    return {
        'job_title': job_title,
        'num_pages': int(num_pages)
    }

def setup_resume_directory() -> str:
    """Setup and validate resume directory"""
    while True:
        resume_dir = input("\nEnter the path to your resume directory: ").strip()
        if os.path.isdir(resume_dir):
            # Check if directory contains PDF files
            pdf_files = [f for f in os.listdir(resume_dir) if f.lower().endswith('.pdf')]
            if pdf_files:
                return resume_dir
            else:
                print("No PDF files found in the specified directory!")
        else:
            print("Invalid directory path! Please enter a valid path.")

def process_jobs(jobs: List[Dict]) -> List[Dict]:
    """Process job listings and extract structured information"""
    processed_jobs = []
    print(f"\nProcessing {len(jobs)} job listings...")
    
    for job in jobs:
        if job['summary']:
            job_details = parse_job_description(job['summary'])
            job_details.update({
                'original_title': job['title'],
                'company': job['company'],
                'location': job['location'],
                'link': job['link']
            })
            processed_jobs.append(job_details)
    
    print(f"Successfully processed {len(processed_jobs)} job descriptions")
    return processed_jobs

def display_matches(matches: List[Dict], resume_name: str):
    """Display matching results in a formatted way with detailed analysis"""
    print(f"\n{'='*80}")
    print(f"MATCHING RESULTS for Resume: {resume_name}")
    print(f"{'='*80}")
    
    if not matches:
        print("No matching jobs found above the minimum score threshold.")
        return
    
    print(f"Found {len(matches)} matching jobs with detailed analysis:\n")
    
    for i, match in enumerate(matches, 1):
        job = match['job']
        print(f"{'='*60}")
        print(f"#{i} - {job.get('title', 'Unknown Title')}")
        print(f"{'='*60}")
        print(f"Company: {job.get('company', 'Unknown')}")
        print(f"Location: {job.get('location', 'Unknown')}")
        print(f"Job Link: {job.get('link', 'No link available')}")
        
        print(f"\n📊 MATCH ANALYSIS:")
        print(f"   Overall Match Score: {match['final_score']:.1%}")
        print(f"   ├─ Content Similarity: {match['similarity_score']:.1%}")
        print(f"   ├─ Experience Match: {match['experience_score']:.1%}")
        print(f"   ├─ Location Match: {match['location_score']:.1%}")
        print(f"   ├─ Skills Match: {match['skills_score']:.1%}")
        print(f"   └─ Title Relevance: {match.get('title_relevance', 0):.1%}")
        
        print(f"\n🎯 SKILLS ANALYSIS:")
        matched_skills = match.get('matched_skills', [])
        missing_skills = match.get('missing_skills', [])
        skill_percentage = match.get('skill_match_percentage', 0)
        
        print(f"   Skills Match: {skill_percentage:.1f}%")
        if matched_skills:
            print(f"   ✅ Matched Skills: {', '.join(matched_skills[:5])}")
            if len(matched_skills) > 5:
                print(f"      ... and {len(matched_skills) - 5} more")
        else:
            print(f"   ❌ No skills matched")
            
        if missing_skills:
            print(f"   ⚠️  Missing Skills: {', '.join(missing_skills[:3])}")
            if len(missing_skills) > 3:
                print(f"      ... and {len(missing_skills) - 3} more")
        
        # Display job's key skills if available
        job_key_skills = job.get('key_skills', [])
        if job_key_skills:
            print(f"\n🔧 JOB KEY SKILLS:")
            print(f"   {', '.join(job_key_skills[:8])}")
            if len(job_key_skills) > 8:
                print(f"   ... and {len(job_key_skills) - 8} more skills")
        
        # Job description preview
        summary = job.get('summary', '')
        if summary:
            print(f"\n📝 JOB DESCRIPTION PREVIEW:")
            preview = summary[:200] + "..." if len(summary) > 200 else summary
            print(f"   {preview}")
        
        print(f"\n{'─'*60}")

def main():
    print("\n=== Job-Resume Matching System ===")
    
    # 1. Get user preferences
    preferences = get_user_input()
    
    # 2. Scrape job listings
    print(f"\nScraping job listings for '{preferences['job_title']}'...")
    print(f"This will search through {preferences['num_pages']} pages...")
    
    jobs = scrape_jobs(
        preferences['job_title'],
        location="India",  # Default location
        num_pages=preferences['num_pages'],
        headless=False  # Show browser for visibility
    )
    
    if not jobs:
        print("No jobs found! Please try different search parameters.")
        return
    
    print(f"Found {len(jobs)} job listings!")
    
    # 3. Setup resume parsing
    resume_dir = setup_resume_directory()
    parser = ResumeParser(resume_dir)
    print("\nParsing resumes...")
    resumes = parser.parse_resumes()
    
    if not resumes:
        print("No valid resumes found! Please check your resume directory.")
        return
    
    print(f"\n=== Resume Parsing Results ===")
    for resume in resumes:
        if "error" in resume:
            print(f"\nError processing resume {resume.get('file_name', 'Unknown')}:")
            print(f"Error: {resume['error']}")
        else:
            print(f"\nResume: {resume.get('file_name', 'Unknown')}")
            print(f"Name: {resume.get('name', 'Not found')}")
            print(f"Email: {resume.get('email', 'Not found')}")
            print(f"Phone: {resume.get('phone', 'Not found')}")
            print("\nSkills found:")
            for skill in resume.get('skills', []):
                print(f"- {skill}")
            print("\nEducation:")
            for edu in resume.get('education', []):
                print(f"- {edu}")
            print(f"\nYears of Experience: {resume.get('years_of_experience', 'Not found')}")
    
    print(f"\nSuccessfully parsed {len(resumes)} resumes!")
    
    # 4. Process job descriptions
    processed_jobs = process_jobs(jobs)
    
    if not processed_jobs:
        print("Failed to process any job descriptions!")
        return
    
    # 5. Initialize matcher
    matcher = JobMatcher()
    
    # 6. Process each resume
    print("\nMatching resumes with jobs...")
    for resume in resumes:
        if "error" in resume:
            print(f"\nError processing resume: {resume.get('file_name', 'Unknown')}")
            print(f"Error: {resume['error']}")
            continue
        
        # Create text representation of resume
        resume_text = f"""
        {resume.get('name', '')}
        Skills: {', '.join(resume.get('skills', []))}
        Education: {', '.join(resume.get('education', []))}
        Experience: {resume.get('years_of_experience', '')} years
        """
        
        # Get matches for this resume with more realistic threshold
        matches = matcher.get_top_matches(
            processed_jobs,
            resume_text,
            top_n=15,  # Show more matches
            min_score=0.25  # Lower threshold for more realistic results
        )
        
        # Display results
        display_matches(matches, resume.get('name', 'Unknown'))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        print(f"\n\nAn error occurred: {str(e)}")
    finally:
        print("\nThank you for using the Job-Resume Matching System!")
