import time
import os
import tempfile
import uuid
import shutil
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from bs4 import BeautifulSoup
import re


class JobScraperSession:
    """
    Enhanced LinkedIn job scraper with detailed job information extraction
    """
    
    def __init__(self):
        self.driver = None
        self.temp_profile_dir = None
        self.is_logged_in = False
        
    def __enter__(self):
        self.initialize_driver()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
        
    def initialize_driver(self):
        """Initialize Chrome WebDriver with temporary profile"""
        print("\n" + "="*60)
        print("🔧 INITIALIZING CHROME SESSION")
        print("="*60)
        
        try:
            temp_base = tempfile.gettempdir()
            self.temp_profile_dir = os.path.join(temp_base, f"chrome_linkedin_session_{uuid.uuid4().hex[:8]}")
            os.makedirs(self.temp_profile_dir, exist_ok=True)
            print(f"📁 Created temporary profile: {self.temp_profile_dir}")
            
            chrome_options = Options()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--ignore-certificate-errors")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--remote-allow-origins=*")
            chrome_options.add_argument(f"--user-data-dir={self.temp_profile_dir}")
            chrome_options.add_argument("--profile-directory=Default")
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option("useAutomationExtension", False)
            chrome_options.add_argument(
                "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            )
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--disable-popup-blocking")
            chrome_options.add_argument("--disable-infobars")
            
            print("✅ Chrome options configured")
            print("🚀 Starting Chrome browser...")
            
            options = webdriver.ChromeOptions()
            options.add_experimental_option('excludeSwitches', ['enable-logging'])
            
            for arg in chrome_options.arguments:
                options.add_argument(arg)
            for k, v in chrome_options.experimental_options.items():
                options.add_experimental_option(k, v)
            
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.driver = webdriver.Chrome(options=options)
                    self.driver.set_page_load_timeout(30)
                    self.driver.implicitly_wait(3)
                    
                    self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                        "source": """
                            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                            window.chrome = { runtime: {} };
                        """
                    })
                    
                    print("✅ Chrome browser initialized")
                    break
                except Exception as e:
                    print(f"⚠️ Attempt {attempt + 1} failed: {str(e)}")
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(2)
                    
            print("🔍 Testing browser...")
            self.driver.get("https://www.linkedin.com/login")
            time.sleep(2)
            print("✅ Browser test successful")
                
        except Exception as e:
            print(f"\n❌ Failed to initialize Chrome: {str(e)}")
            if hasattr(self, 'driver') and self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
            raise
        
        print("="*60 + "\n")
        
    def login_to_linkedin(self, wait_for_manual_login: bool = True):
        """Navigate to LinkedIn and wait for user to log in manually"""
        print("\n" + "="*60)
        print("🔐 LINKEDIN LOGIN")
        print("="*60)
        
        if not self.driver:
            raise RuntimeError("Driver not initialized")
        
        print("🌐 Navigating to LinkedIn login...")
        self.driver.get("https://www.linkedin.com/login")
        time.sleep(3)
        
        print("\n" + "-"*60)
        print("🔧 MANUAL LOGIN REQUIRED")
        print("-"*60)
        print("Please complete the following steps:")
        print("1. Enter your LinkedIn email/phone")
        print("2. Enter your password")
        print("3. Complete any verification if prompted")
        print("4. Wait until you see your LinkedIn feed")
        print("-"*60)
        
        if wait_for_manual_login:
            input("\n⏸️  Press ENTER after you have logged in successfully...")
        
        print("\n🔍 Verifying login status...")
        time.sleep(2)
        
        login_verified = False
        try:
            indicators = [
                (By.CSS_SELECTOR, "[data-control-name='nav.settings_signout']"),
                (By.CSS_SELECTOR, ".global-nav__me"),
                (By.XPATH, "//img[contains(@alt, 'Photo of')]"),
                (By.CSS_SELECTOR, ".feed-identity-module"),
            ]
            
            for by, selector in indicators:
                try:
                    element = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((by, selector))
                    )
                    if element:
                        login_verified = True
                        break
                except:
                    continue
                    
            if "feed" in self.driver.current_url or "mynetwork" in self.driver.current_url:
                login_verified = True
                
        except Exception as e:
            print(f"⚠️  Could not verify login: {e}")
        
        if login_verified:
            print("✅ Login verified successfully!")
            self.is_logged_in = True
        else:
            print("⚠️  Could not verify login. Proceeding anyway...")
            self.is_logged_in = False
        
        print("="*60 + "\n")
    
    def search_jobs(self, query: str, location: str = "", num_pages: int = 1, 
                   fetch_details: bool = False) -> List[Dict]:
        """
        Search for jobs on LinkedIn
        
        Args:
            query: Job title or keywords
            location: Job location (optional)
            num_pages: Number of pages to scrape
            fetch_details: If True, fetches full job description (slower but more accurate)
            
        Returns:
            List of job dictionaries
        """
        print("\n" + "="*60)
        print("🔎 SEARCHING FOR JOBS ON LINKEDIN")
        print("="*60)
        print(f"Query: {query}")
        print(f"Location: {location if location else 'Any'}")
        print(f"Pages: {num_pages}")
        print(f"Details Mode: {'ON (slower, more accurate)' if fetch_details else 'OFF (fast)'}")
        print("="*60 + "\n")
        
        if not self.driver:
            raise RuntimeError("Driver not initialized")
        
        all_jobs = []
        seen_job_ids = set()
        
        # Build LinkedIn search URL with Easy Apply filter
        base_url = "https://www.linkedin.com/jobs/search/?"
        params = []
        
        if query:
            params.append(f"keywords={query.replace(' ', '%20')}")
        if location:
            params.append(f"location={location.replace(' ', '%20')}")
        params.append("f_AL=true")  # Easy Apply filter
        
        search_url = base_url + "&".join(params)
        
        for page in range(num_pages):
            try:
                print(f"\n📄 Page {page + 1}/{num_pages}")
                
                page_url = f"{search_url}&start={page * 25}"
                print(f"🌐 Loading jobs...")
                self.driver.get(page_url)
                time.sleep(3)
                
                try:
                    WebDriverWait(self.driver, 8).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "ul.jobs-search__results-list, div.job-card-container"))
                    )
                except TimeoutException:
                    print("⚠️  Timeout waiting for jobs")
                
                # Quick scroll
                for _ in range(2):
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(0.5)
                
                # Parse with BeautifulSoup (fast)
                print("⚡ Parsing job listings...")
                page_source = self.driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                
                page_jobs = self._parse_jobs_with_beautifulsoup(soup, seen_job_ids)
                
                # Optionally fetch detailed info
                if fetch_details and page_jobs:
                    print(f"📋 Fetching details for {len(page_jobs)} jobs...")
                    page_jobs = self._enrich_jobs_with_details(page_jobs)
                
                all_jobs.extend(page_jobs)
                
                print(f"✅ Collected {len(page_jobs)} jobs from this page")
                print(f"📊 Total: {len(all_jobs)} jobs")
                
            except Exception as e:
                print(f"❌ Error on page {page + 1}: {str(e)}")
                continue
        
        print("\n" + "="*60)
        print("✅ SCRAPING COMPLETE")
        print(f"📈 Total: {len(all_jobs)} jobs")
        print("="*60 + "\n")
        
        return all_jobs
    
    def _parse_jobs_with_beautifulsoup(self, soup: BeautifulSoup, seen_ids: set) -> List[Dict]:
        """Parse all jobs from page HTML using BeautifulSoup - FIXED COMPANY EXTRACTION"""
        jobs = []
        
        job_cards = soup.find_all(['li', 'div'], class_=lambda x: x and any(
            cls in x for cls in ['job-card-container', 'jobs-search-results__list-item', 'scaffold-layout__list-item']
        ))
        
        if not job_cards:
            job_cards = soup.find_all(['li', 'div'], attrs={'data-occludable-job-id': True})
        
        print(f"  Found {len(job_cards)} job cards on page")
        
        for idx, card in enumerate(job_cards, 1):
            try:
                # Check for Easy Apply
                card_text = card.get_text().lower()
                is_easy_apply = 'easy apply' in card_text
                
                # Extract job ID
                job_id = (
                    card.get('data-occludable-job-id') or 
                    card.get('data-job-id') or
                    card.get('data-id')
                )
                
                if job_id and job_id in seen_ids:
                    continue
                
                # Extract title
                title = None
                title_selectors = [
                    ('a', lambda x: x and 'job-card-list__title' in x),
                    ('h3', lambda x: x and 'base-search-card__title' in x),
                    ('a', 'base-card__full-link'),
                    ('span', lambda x: x and 'job-card-container__link' in x),
                ]
                
                for tag, class_filter in title_selectors:
                    title_elem = card.find(tag, class_=class_filter)
                    if title_elem:
                        title = title_elem.get_text().strip()
                        if title:
                            title = re.sub(r'\s+', ' ', title).strip()
                            
                            # Remove duplicate text if present
                            title_length = len(title)
                            if title_length > 0 and title_length % 2 == 0:
                                half = title_length // 2
                                first_half = title[:half].strip()
                                second_half = title[half:].strip()
                                if first_half == second_half:
                                    title = first_half
                            break
                
                if not title:
                    continue
                
                # ==================== FIXED COMPANY EXTRACTION ====================
                company = None
                
                # STRATEGY 1: Primary subtitle (most reliable for current LinkedIn)
                company_elem = card.find('h4', class_=lambda x: x and 'base-search-card__subtitle' in x)
                if company_elem:
                    company_text = company_elem.get_text().strip()
                    company_text = re.sub(r'\s+', ' ', company_text)
                    
                    # Clean up - remove location if it's in same element (format: "Company • Location")
                    if '•' in company_text:
                        parts = [p.strip() for p in company_text.split('•')]
                        company = parts[0] if parts[0] else None
                    else:
                        company = company_text
                
                # STRATEGY 2: Company link with specific class
                if not company or len(company) < 2:
                    company_link = card.find('a', class_=lambda x: x and 'job-card-container__primary-description' in x)
                    if company_link:
                        company = company_link.get_text().strip()
                
                # STRATEGY 3: Look for company links (multiple patterns)
                if not company or len(company) < 2:
                    company_link_selectors = [
                        ('a', lambda x: x and 'hidden-nested-link' in x),
                        ('a', lambda x: x and '/company/' in str(x)),
                    ]
                    
                    for tag, class_filter in company_link_selectors:
                        links = card.find_all(tag, class_=class_filter) if callable(class_filter) else card.find_all(tag, href=lambda x: '/company/' in str(x))
                        
                        for link in links:
                            # Check aria-label (very reliable)
                            aria_label = link.get('aria-label', '')
                            if aria_label:
                                # Remove "logo" suffix if present
                                company_candidate = re.sub(r'\s+logo$', '', aria_label, flags=re.IGNORECASE).strip()
                                if len(company_candidate) > 2 and not re.search(r'\d+\s*(hour|day|week)', company_candidate, re.IGNORECASE):
                                    company = company_candidate
                                    break
                            
                            # Check link text
                            link_text = link.get_text().strip()
                            link_text = re.sub(r'\s+', ' ', link_text)
                            if len(link_text) > 2 and not re.search(r'\d+\s*(hour|day|week)', link_text, re.IGNORECASE):
                                company = link_text
                                break
                        
                        if company and len(company) > 2:
                            break
                
                # STRATEGY 4: Extract from data attributes
                if not company or len(company) < 2:
                    # Check for entity-urn which often contains company info
                    for link in card.find_all('a', href=lambda x: x and '/company/' in str(x)):
                        href = link.get('href', '')
                        # Extract company name from URL path
                        match = re.search(r'/company/([^/?]+)', href)
                        if match:
                            company_slug = match.group(1)
                            # Convert slug to readable name (e.g., "microsoft-corporation" -> "Microsoft Corporation")
                            company = company_slug.replace('-', ' ').title()
                            break
                
                # STRATEGY 5: Look in parent containers
                if not company or len(company) < 2:
                    # Find the info section
                    info_section = card.find('div', class_=lambda x: x and 'base-search-card__info' in x)
                    if info_section:
                        # Get all h4 elements
                        h4_elements = info_section.find_all('h4')
                        # First h4 after title is usually company
                        if len(h4_elements) >= 1:
                            company_text = h4_elements[0].get_text().strip()
                            company_text = re.sub(r'\s+', ' ', company_text)
                            
                            # Validate it's not location or time
                            if (company_text and len(company_text) > 2 and
                                not re.search(r'\d+\s*(hour|day|week|month)', company_text, re.IGNORECASE) and
                                not re.search(r'(remote|hybrid|on-site)', company_text, re.IGNORECASE)):
                                company = company_text
                
                # STRATEGY 6: Fallback - look for any text between title and location
                if not company or len(company) < 2:
                    # Get all text nodes and find company by position
                    all_text_elements = card.find_all(['h3', 'h4', 'span', 'div'])
                    found_title = False
                    
                    for elem in all_text_elements:
                        text = elem.get_text().strip()
                        text = re.sub(r'\s+', ' ', text)
                        
                        if not text or len(text) < 2:
                            continue
                        
                        # Skip if it's the title
                        if title and text in title:
                            found_title = True
                            continue
                        
                        # After finding title, next valid text is likely company
                        if found_title:
                            # Validate it's not noise
                            if (not re.search(r'\d+\s*(hour|day|week|month|minute)', text, re.IGNORECASE) and
                                not re.search(r'^(remote|hybrid|on-site)$', text, re.IGNORECASE) and
                                not re.search(r'^\d+$', text) and
                                '•' not in text):
                                company = text
                                break
                
                # Final cleanup
                if company:
                    # Remove extra whitespace
                    company = re.sub(r'\s+', ' ', company).strip()
                    
                    # Remove noise patterns
                    noise_patterns = [
                        r'\d+\s*employee.*',
                        r'\d+\s*connection.*',
                        r'\d+\s*follower.*',
                        r'Posted\s+\d+.*',
                        r'Reposted\s+\d+.*',
                    ]
                    
                    for pattern in noise_patterns:
                        company = re.sub(pattern, '', company, flags=re.IGNORECASE).strip()
                    
                    # Remove separators at the end
                    company = re.sub(r'[•·|]+$', '', company).strip()
                    
                    # If it looks like a location, discard
                    if re.search(r',\s*[A-Z]{2}$', company):  # e.g., "New York, NY"
                        company = None
                
                # Set default if still not found
                if not company or len(company) < 2:
                    company = 'Company not specified'
                
                # ==================== END COMPANY EXTRACTION ====================
                
                # Extract location
                location = 'Remote/Not specified'
                location_selectors = [
                    ('span', lambda x: x and 'job-search-card__location' in x),
                    ('div', lambda x: x and 'metadata' in x),
                    ('span', lambda x: x and 'location' in x.lower() if x else False),
                ]
                
                for tag, class_filter in location_selectors:
                    location_elem = card.find(tag, class_=class_filter)
                    if location_elem:
                        loc_text = location_elem.get_text().strip()
                        loc_text = re.sub(r'\s+', ' ', loc_text).strip()
                        if loc_text and len(loc_text) > 3:
                            location = loc_text
                            break
                
                # Extract link
                link = None
                link_elem = card.find('a', href=lambda x: x and '/jobs/view/' in x)
                if link_elem:
                    href = link_elem.get('href')
                    if href:
                        link = href if href.startswith('http') else f"https://www.linkedin.com{href}"
                        if '?' in link:
                            link = link.split('?')[0]
                
                if not link and job_id:
                    link = f"https://www.linkedin.com/jobs/view/{job_id}"
                
                if not link:
                    continue
                
                # Create job dict
                job = {
                    'job_id': job_id or link,
                    'title': title,
                    'company': company,
                    'location': location,
                    'link': link,
                    'is_easy_apply': is_easy_apply,
                    'key_skills': [],
                    'summary': '',
                    'platform': 'LinkedIn'
                }
                
                jobs.append(job)
                if job_id:
                    seen_ids.add(job_id)
                
                # Debug output
                if idx <= 3:
                    print(f"    Job {idx}: {title[:35]} | {company[:25]} | {location[:20]}")
                    
            except Exception as e:
                print(f"    ⚠️  Error parsing card {idx}: {str(e)[:50]}")
                continue
        
        return jobs
        
        def _enrich_jobs_with_details(self, jobs: List[Dict]) -> List[Dict]:
            """
            Fetch detailed information for each job by visiting the job page
            """
            enriched_jobs = []
            
            for i, job in enumerate(jobs, 1):
                try:
                    print(f"  [{i}/{len(jobs)}] Fetching: {job['title'][:40]}...")
                    
                    # Navigate to job page
                    self.driver.get(job['link'])
                    time.sleep(2)
                    
                    # Get page source
                    page_source = self.driver.page_source
                    soup = BeautifulSoup(page_source, 'html.parser')
                    
                    # Extract full description
                    description_elem = soup.find('div', class_=lambda x: x and 'jobs-description' in x)
                    if description_elem:
                        job['summary'] = description_elem.get_text(separator=' ').strip()
                        
                        # Extract skills from description
                        job['key_skills'] = self._extract_skills_from_text(job['summary'])
                    
                    # Check if it's actually Easy Apply
                    apply_button = soup.find('button', string=re.compile(r'Easy Apply', re.I))
                    job['is_easy_apply'] = apply_button is not None
                    
                    enriched_jobs.append(job)
                    
                except Exception as e:
                    print(f"    ⚠️ Failed to fetch details: {str(e)[:50]}")
                    enriched_jobs.append(job)
                    continue
            
            return enriched_jobs
    
    def _extract_skills_from_text(self, text: str) -> List[str]:
        """Extract technical skills from job description text"""
        if not text:
            return []
        
        text_lower = text.lower()
        
        # Common technical skills
        skill_keywords = [
            'python', 'pandas', 'numpy', 'matplotlib', 'seaborn', 'scikit-learn', 'tensorflow', 'pytorch',
            'java', 'javascript', 'typescript', 'react', 'angular', 'vue', 'node.js', 'nodejs',
            'sql', 'mysql', 'postgresql', 'mongodb', 'oracle', 'nosql',
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins',
            'power bi', 'tableau', 'excel', 'powerpoint',
            'machine learning', 'deep learning', 'data analysis', 'data visualization',
            'git', 'github', 'agile', 'scrum',
            'r', 'matlab', 'spss', 'sas',
            'html', 'css', 'bootstrap', 'django', 'flask', 'fastapi',
            'spark', 'hadoop', 'kafka', 'airflow',
            'linux', 'unix', 'bash', 'shell'
        ]
        
        found_skills = []
        for skill in skill_keywords:
            pattern = rf'\b{re.escape(skill)}\b'
            if re.search(pattern, text_lower):
                found_skills.append(skill)
        
        return found_skills
    
    def cleanup(self):
        """Clean up resources"""
        print("\n" + "="*60)
        print("🧹 CLEANING UP")
        print("="*60)
        
        if self.driver:
            try:
                print("🔒 Closing browser...")
                self.driver.quit()
                print("✅ Browser closed")
            except Exception as e:
                print(f"⚠️  Error closing browser: {e}")
        
        if self.temp_profile_dir and os.path.exists(self.temp_profile_dir):
            try:
                print(f"🗑️  Deleting temporary profile...")
                time.sleep(2)
                shutil.rmtree(self.temp_profile_dir, ignore_errors=True)
                print("✅ Temporary profile deleted")
            except Exception as e:
                print(f"⚠️  Could not delete temp profile: {e}")
        
        print("="*60 + "\n")


# Convenience functions
def scrape_jobs(query: str, location: str = "", num_pages: int = 1, 
                fetch_details: bool = False, **kwargs) -> List[Dict]:
    """Main scraping function for LinkedIn"""
    with JobScraperSession() as session:
        session.login_to_linkedin(wait_for_manual_login=True)
        jobs = session.search_jobs(query, location, num_pages, fetch_details)
        return jobs


def init_driver(**kwargs):
    """Initialize and return a session"""
    session = JobScraperSession()
    session.initialize_driver()
    return session