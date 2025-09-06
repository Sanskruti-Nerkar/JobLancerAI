import time
import json
import requests
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

# Import statements will be handled locally to avoid circular imports


def init_driver(headless=False):
    """
    Initialize and return a Selenium WebDriver instance.
    """
    from selenium.webdriver.chrome.service import Service
    
    chrome_options = Options()
    if headless:
        chrome_options.add_argument('--headless=new')
        
    # Add options to avoid detection and improve stability
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--start-maximized')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--disable-web-security')
    chrome_options.add_argument('--allow-running-insecure-content')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Add custom user agent
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # Specify ChromeDriver path
    chromedriver_path = r"D:\Desktop\Mustafa\7th SEM\PBL\chromedriver-win64\chromedriver-win64\chromedriver.exe"
    
    try:
        service = Service(executable_path=chromedriver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Set timeouts
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(10)
        
        print("✓ ChromeDriver initialized successfully")
        return driver
        
    except Exception as e:
        print(f"Error initializing ChromeDriver: {str(e)}")
        print("Make sure ChromeDriver is installed and the path is correct")
        raise


def highlight_element(driver, element, duration=0.5):
    """Highlight an element being processed"""
    original_style = element.get_attribute('style')
    driver.execute_script("""
        arguments[0].style.border = '3px solid red';
        arguments[0].style.backgroundColor = 'yellow';
    """, element)
    driver.execute_script("arguments[0].scrollIntoView(true);", element)
    time.sleep(duration)
    driver.execute_script(f"arguments[0].style = '{original_style}';", element)

def normalize_skill(skill):
    """Normalize a skill name for better matching"""
    skill = skill.lower().strip()
    # Common variations of skills
    skill_variations = {
        'js': 'javascript',
        'py': 'python',
        'react.js': 'react',
        'reactjs': 'react',
        'node.js': 'node',
        'nodejs': 'node',
        'aws': 'amazon web services',
        'postgres': 'postgresql',
        'mongo': 'mongodb',
        'vue.js': 'vue',
        'vuejs': 'vue',
        'ts': 'typescript',
        'k8s': 'kubernetes',
        'ml': 'machine learning',
        'ai': 'artificial intelligence'
    }
    return skill_variations.get(skill, skill)

def calculate_skills_match(job_skills: Dict, resume_skills: Dict) -> Dict:
    """
    Calculate detailed matching scores between job skills and resume skills.
    Now handles both technical and soft skills separately.
    
    Args:
        job_skills: Dict with 'technical', 'soft', and 'other' skill categories
        resume_skills: Dict with 'technical', 'soft', and 'other' skill categories
    
    Returns:
        Dict containing match scores and details
    """
    def normalize_skills(skills_list):
        """Helper to normalize a list of skills"""
        return {normalize_skill(skill) for skill in skills_list}
    
    def calculate_category_match(job_category_skills, resume_category_skills):
        """Calculate match score for a single category of skills"""
        if not job_category_skills:
            return {'score': 100.0, 'matches': set(), 'missing': set()}
            
        job_set = normalize_skills(job_category_skills)
        resume_set = normalize_skills(resume_category_skills)
        
        # Direct matches
        direct_matches = job_set.intersection(resume_set)
        
        # Partial matches (e.g., "python developer" matches "python")
        partial_matches = set()
        missing_skills = job_set - direct_matches
        
        for job_skill in missing_skills.copy():
            for resume_skill in resume_set:
                if (job_skill in resume_skill or resume_skill in job_skill):
                    partial_matches.add(job_skill)
                    missing_skills.remove(job_skill)
                    break
        
        # Calculate score
        matches = direct_matches.union(partial_matches)
        score = (len(matches) / len(job_set)) * 100 if job_set else 100
        
        return {
            'score': score,
            'matches': matches,
            'missing': missing_skills
        }
    
    # Initialize result structure
    result = {
        'overall_score': 0.0,
        'technical': {'score': 0.0, 'matches': set(), 'missing': set()},
        'soft': {'score': 0.0, 'matches': set(), 'missing': set()},
        'other': {'score': 0.0, 'matches': set(), 'missing': set()}
    }
    
    # Calculate matches for each category
    print("\nCalculating skill matches...")
    
    # Technical skills (60% weight)
    tech_result = calculate_category_match(
        job_skills.get('technical', []),
        resume_skills.get('technical', [])
    )
    result['technical'] = tech_result
    print(f"\nTechnical Skills Match: {tech_result['score']:.1f}%")
    print(f"Matching: {', '.join(tech_result['matches'])}")
    print(f"Missing: {', '.join(tech_result['missing'])}")
    
    # Soft skills (30% weight)
    soft_result = calculate_category_match(
        job_skills.get('soft', []),
        resume_skills.get('soft', [])
    )
    result['soft'] = soft_result
    print(f"\nSoft Skills Match: {soft_result['score']:.1f}%")
    print(f"Matching: {', '.join(soft_result['matches'])}")
    print(f"Missing: {', '.join(soft_result['missing'])}")
    
    # Other skills (10% weight)
    other_result = calculate_category_match(
        job_skills.get('other', []),
        resume_skills.get('other', [])
    )
    result['other'] = other_result
    print(f"\nOther Skills Match: {other_result['score']:.1f}%")
    print(f"Matching: {', '.join(other_result['matches'])}")
    print(f"Missing: {', '.join(other_result['missing'])}")
    
    # Calculate weighted overall score
    result['overall_score'] = (
        (tech_result['score'] * 0.6) +
        (soft_result['score'] * 0.3) +
        (other_result['score'] * 0.1)
    )
    
    print(f"\nOverall Match Score: {result['overall_score']:.1f}%")
    
    return result

def search_jobs(driver, query, location="India", num_pages=1):
    """
    Search for jobs on Naukri.com and return a list of job card elements.
    """
    print(f"\nSearching for {query} jobs in {location}...")
    jobs = []
    
    # Build search URL for Naukri - use the correct format
    search_url = f"https://www.naukri.com/{query.replace(' ', '-')}-jobs-in-{location.replace(' ', '-')}"
    print(f"Search URL: {search_url}")
    
    for page in range(1, num_pages + 1):
        print(f"\nScraping page {page}/{num_pages}...")
        
        # Build URL for each page
        if page == 1:
            url = search_url
        else:
            url = f"{search_url}-{page}"
        
        print(f"Loading URL: {url}")
        driver.get(url)
        
        # Wait for page to load
        time.sleep(5)
        
        # Check if page loaded successfully
        if "naukri.com" not in driver.current_url:
            print(f"Failed to load page {page}. Current URL: {driver.current_url}")
            continue
        
        # Scroll to load dynamic content
        print("Scrolling to load all jobs...")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        
        # Parse the page
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Try multiple selectors for job cards - updated for current Naukri layout
        cards = []
        
        # Primary selectors for current Naukri structure (based on actual analysis)
        card_selectors = [
            'div.srp-jobtuple-wrapper',             # Current Naukri job wrapper
            'div[class*="srp-jobtuple"]',           # Job tuple wrapper
            'div[class*="cust-job-tuple"]',         # Custom job tuple
            'div[class*="job-listing-container"]',  # Job listing container
            'article[class*="jobTuple"]',           # Original jobTuple articles
            'div[class*="jobTuple"]',               # JobTuple divs
            'article[class*="job"]',                # Job articles
            'div[class*="job"]',                    # Job divs
            'div[class*="jobCard"]',                # Job card divs
            'article[class*="jobCard"]',            # Job card articles
            'div[class*="job-item"]',               # Job item divs
            'div[class*="job-listing"]',            # Job listing divs
            'div[class*="search-result"]',          # Search result divs
            'div[data-testid*="job"]',              # Data test ID selectors
            'article[data-testid*="job"]'           # Data test ID articles
        ]
        
        for selector in card_selectors:
            cards = soup.select(selector)
            if cards:
                print(f"Found {len(cards)} job cards using selector: {selector}")
                break
        
        # If still no cards, try to find any job-related containers
        if not cards:
            cards = soup.find_all('div', {'class': lambda x: x and 'job' in x.lower()})
            if cards:
                print(f"Found {len(cards)} job cards using fallback selector")
        
        # Additional fallback: look for any container with job-related content
        if not cards:
            # Look for containers that might contain job information
            potential_cards = soup.find_all(['div', 'article'], {
                'class': lambda x: x and any(keyword in x.lower() for keyword in 
                    ['result', 'item', 'card', 'listing', 'posting', 'tuple'])
            })
            cards = [card for card in potential_cards if len(card.find_all('a')) >= 2]  # Should have at least 2 links
            if cards:
                print(f"Found {len(cards)} potential job cards using content-based detection")
        
        if not cards:
            print(f"No job cards found on page {page}")
            print("Page source preview:", driver.page_source[:500])
            continue
        
        print(f"Found {len(cards)} job cards on page {page}")
        jobs.extend(cards)
        
        # Debug: Show first card structure
        if cards:
            first_card = cards[0]
            print(f"First card classes: {first_card.get('class', [])}")
            print(f"First card tag: {first_card.name}")
            print(f"First card preview: {str(first_card)[:300]}...")
            
            # Debug: Show all links and text in first card
            print("\nDebug - First card analysis:")
            all_links = first_card.find_all('a')
            print(f"Found {len(all_links)} links in first card")
            for i, link in enumerate(all_links[:3]):  # Show first 3 links
                print(f"  Link {i+1}: {link.get('href', 'No href')} - Text: {link.text.strip()[:50]}")
            
            all_spans = first_card.find_all('span')
            print(f"Found {len(all_spans)} spans in first card")
            for i, span in enumerate(all_spans[:3]):  # Show first 3 spans
                print(f"  Span {i+1}: {span.get('class', [])} - Text: {span.text.strip()[:50]}")
    
    print(f"\nTotal jobs collected: {len(jobs)}")
    return jobs


def extract_skills_from_text(text):
    """Extract potential skills from text using common technical keywords"""
    common_skills = {
        'python', 'java', 'javascript', 'js', 'react', 'node', 'angular', 'vue',
        'html', 'css', 'sql', 'mysql', 'postgresql', 'mongodb', 'aws', 'azure',
        'docker', 'kubernetes', 'git', 'rest', 'api', 'django', 'flask', 'spring',
        'bootstrap', 'jquery', 'php', 'c++', 'c#', 'ruby', 'rails', 'typescript',
        'golang', 'rust', 'scala', 'hadoop', 'spark', 'tensorflow', 'pytorch',
        'ml', 'ai', 'devops', 'agile', 'scrum', 'jira', 'jenkins'
    }
    
    words = text.lower().split()
    found_skills = set()
    
    for word in words:
        word = word.strip('.,()[]{}')
        if word in common_skills:
            found_skills.add(word)
    
    return list(found_skills)

def parse_job_card(card) -> Optional[Dict]:
    """
    Parse a single job card and return job details.
    Updated for new Naukri layout with separate skills section.
    """
    try:
        job_info = {}
        
        # Extract title - updated selectors for new Naukri layout
        title_elem = None
        
        # Try multiple selectors for job title (new Naukri structure)
        title_selectors = [
            'a[class*="title"]',           # Links with title class
            'a[class*="jobTitle"]',        # Job title links
            'h2 a',                        # Links inside h2
            'h3 a',                        # Links inside h3
            'a[data-testid*="title"]',     # Data test ID selectors
            'a[title]',                    # Links with title attribute
            'h2',                          # Direct h2 elements
            'h3',                          # Direct h3 elements
            'div[class*="title"] a',       # Links in title divs
            'span[class*="title"] a'       # Links in title spans
        ]
        
        for selector in title_selectors:
            title_elem = card.select_one(selector)
            if title_elem and title_elem.text.strip():
                break
        
        # If still no title, try finding any link that looks like a job title
        if not title_elem:
            all_links = card.find_all('a')
            for link in all_links:
                text = link.text.strip()
                # Check if link text looks like a job title (not too long, not empty)
                if text and len(text) < 100 and len(text.split()) >= 2:
                    # Skip common non-title links
                    if not any(skip in text.lower() for skip in ['apply', 'view', 'more', 'details', 'company']):
                        title_elem = link
                        break
        
        if not title_elem:
            print("No title found in job card")
            return None
        
        # Extract company - updated selectors
        company_elem = None
        company_selectors = [
            'a[class*="subTitle"]',
            'a[class*="companyName"]', 
            'a[class*="comp-name"]',
            'a[class*="company-name"]',
            'div[class*="company"] a',
            'span[class*="company"] a',
            'div[class*="comp-name"]',
            'span[class*="comp-name"]',
            'a[data-testid*="company"]'
        ]
        
        for selector in company_selectors:
            company_elem = card.select_one(selector)
            if company_elem and company_elem.text.strip():
                break
        
        # Extract location - updated selectors
        location_elem = None
        location_selectors = [
            'li[class*="location"]',
            'span[class*="location"]',
            'div[class*="location"]',
            'li[class*="loc"]',
            'span[class*="loc"]',
            'div[class*="loc"]',
            'span[class*="job-location"]',
            'div[class*="job-location"]',
            'span[data-testid*="location"]'
        ]
        
        for selector in location_selectors:
            location_elem = card.select_one(selector)
            if location_elem and location_elem.text.strip():
                break
        
        # Extract job description/summary - updated selectors
        summary_elem = None
        summary_selectors = [
            'div[class*="job-description"]',
            'div[class*="jobDescription"]',
            'p[class*="description"]',
            'div[class*="summary"]',
            'span[class*="job-desc"]',
            'div[class*="snippet"]',
            'p[class*="snippet"]'
        ]
        
        for selector in summary_selectors:
            summary_elem = card.select_one(selector)
            if summary_elem and summary_elem.text.strip():
                break
        
        # Extract Key Skills from separate section (NEW FEATURE)
        key_skills = []
        skills_selectors = [
            'div[class*="skills"]',
            'div[class*="key-skills"]',
            'div[class*="tag"]',
            'span[class*="skill"]',
            'div[class*="chip"]',
            'ul[class*="skills"] li',
            'div[class*="skill-tag"]'
        ]
        
        for selector in skills_selectors:
            skill_elements = card.select(selector)
            for elem in skill_elements:
                skill_text = elem.text.strip()
                if skill_text and len(skill_text) < 50:  # Reasonable skill length
                    key_skills.append(skill_text)
        
        # Remove duplicates and clean skills
        key_skills = list(set([skill.strip() for skill in key_skills if skill.strip()]))
        
        # Extract link
        link = title_elem.get('href', '') if title_elem.name == 'a' else ''
        if not link and title_elem.find('a'):
            link = title_elem.find('a').get('href', '')
        
        # Make sure link is absolute
        if link and not link.startswith('http'):
            link = 'https://www.naukri.com' + link
        
        job_info.update({
            'title': title_elem.text.strip(),
            'link': link,
            'company': company_elem.text.strip() if company_elem else 'Unknown',
            'location': location_elem.text.strip() if location_elem else 'Unknown',
            'summary': summary_elem.text.strip() if summary_elem else '',
            'key_skills': key_skills  # NEW: Separate skills section
        })
        
        print(f"✓ Parsed job: {job_info['title']} at {job_info['company']}")
        if job_info['summary']:
            print(f"  Description: {job_info['summary'][:100]}...")
        if key_skills:
            print(f"  Key Skills: {', '.join(key_skills[:5])}{'...' if len(key_skills) > 5 else ''}")
        
        return job_info
        
    except Exception as e:
        print(f"Error parsing job card: {str(e)}")
        print(f"Card content: {str(card)[:200]}...")
        return None


def scrape_jobs(query: str, location: str = "India", num_pages: int = 1, headless: bool = False) -> List[Dict]:
    """
    Main job scraping function for Naukri.com
    
    Args:
        query (str): Job title or keywords to search for
        location (str): Location to search in
        num_pages (int): Number of pages to scrape
        headless (bool): Whether to run browser in headless mode
    
    Returns:
        List of job dictionaries
    """
    print(f"\nInitializing job search for: {query} in {location}")
    driver = init_driver(headless=headless)
    jobs = []
    
    try:
        # Search for jobs
        cards = search_jobs(driver, query, location, num_pages)
        
        # Parse each job card
        for card in cards:
            job = parse_job_card(card)
            if job and job.get('title') and job.get('company'):
                jobs.append(job)
        
        print(f"\nFound {len(jobs)} jobs")
        
        # Print summary
        if jobs:
            print("\nTop Jobs Found:")
            for i, job in enumerate(jobs[:5], 1):
                print(f"\n{i}. {job['title']}")
                print(f"   Company: {job['company']}")
                print(f"   Location: {job['location']}")
                print(f"   Link: {job['link']}")
        
        return jobs
        
    except Exception as e:
        print(f"\nError during job scraping: {str(e)}")
        return []
        
    finally:
        print("\nClosing browser...")
        driver.quit()

def extract_resume_skills(resume_text):
    """Extract skills from resume text"""
    # You can enhance this with more sophisticated skill extraction
    return extract_skills_from_text(resume_text)

def format_job_details(job: Dict, detailed: bool = False) -> str:
    """
    Format job details for display with optional detailed view.
    
    Args:
        job: Dictionary containing job information
        detailed: Whether to include detailed match analysis
    
    Returns:
        Formatted string with job details
    """
    # Basic details
    details = [
        f"\n{'='*50}",
        f"Job Title: {job['title']}",
        f"Company: {job['company']}",
        f"Location: {job['location']}",
        f"Experience Required: {job.get('requirements', {}).get('experience', 'Not specified')}",
        f"\nRole Details:",
        f"  Seniority: {job['role_details'].get('seniority', 'Not specified')}",
        f"  Domain: {job['role_details'].get('domain', 'Not specified')}",
        f"  Role Type: {job['role_details'].get('role_type', 'Not specified')}",
    ]
    
    # Skills section
    details.extend([
        "\nRequired Skills:",
        "  Technical Skills:",
        "    " + ", ".join(job['skills']['technical']) if job['skills']['technical'] else "    None specified",
        "  Soft Skills:",
        "    " + ", ".join(job['skills']['soft']) if job['skills']['soft'] else "    None specified"
    ])
    
    # Education requirements
    if job.get('requirements', {}).get('education'):
        details.extend([
            "\nEducation Requirements:",
            "  " + "\n  ".join(job['requirements']['education'])
        ])
    
    # Match analysis if available
    if 'match_analysis' in job and detailed:
        analysis = job['match_analysis']
        details.extend([
            "\nSkills Match Analysis:",
            f"  Overall Match: {job['overall_match']:.1f}%",
            f"  Technical Skills: {analysis['technical']['score']:.1f}%",
            f"    Matching: {', '.join(analysis['technical']['matches'])}",
            f"    Missing: {', '.join(analysis['technical']['missing'])}",
            f"  Soft Skills: {analysis['soft']['score']:.1f}%",
            f"    Matching: {', '.join(analysis['soft']['matches'])}",
            f"    Missing: {', '.join(analysis['soft']['missing'])}"
        ])
    
    # Link
    details.extend([
        f"\nJob Link: {job['link']}",
        "=" * 50
    ])
    
    return "\n".join(details)
if __name__ == "__main__":
    # Example usage
    jobs = scrape_jobs("python-developer", "bangalore", num_pages=2, headless=False)
    for job in jobs:
        print(job)
