import spacy
import re
from typing import Dict, Optional, List

# Load spaCy model
try:
    nlp = spacy.load('en_core_web_sm')
except:
    print("⚠️ spaCy model not loaded")
    nlp = None

# COMPREHENSIVE technical skills list (matching resume_parser.py)
KNOWN_TECHNICAL_SKILLS = {
    # Programming Languages
    'python', 'java', 'javascript', 'typescript', 'c', 'c++', 'c#', 'php', 'ruby', 'go', 'rust',
    'swift', 'kotlin', 'scala', 'r', 'matlab', 'perl', 'shell', 'bash', 'powershell',
    
    # Web Technologies
    'html', 'html5', 'css', 'css3', 'react', 'angular', 'vue', 'vue.js', 'node.js', 'nodejs',
    'express', 'django', 'flask', 'fastapi', 'spring', 'asp.net', 'jquery', 'bootstrap',
    'sass', 'webpack', 'next.js', 'nuxt.js', 'ajax',
    
    # Databases
    'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'cassandra', 'oracle',
    'sqlserver', 'mariadb', 'sqlite', 'dynamodb', 'neo4j', 'couchdb',
    
    # Cloud & DevOps
    'aws', 'azure', 'gcp', 'google cloud', 'docker', 'kubernetes', 'jenkins', 'gitlab', 'github',
    'terraform', 'ansible', 'chef', 'puppet', 'ci/cd', 'git', 'svn', 'circleci', 'travis',
    'cloudformation', 'linux', 'unix', 'windows',
    
    # Data Science & ML
    'machine learning', 'deep learning', 'tensorflow', 'pytorch', 'keras', 'scikit-learn',
    'pandas', 'numpy', 'scipy', 'matplotlib', 'seaborn', 'plotly', 'nltk', 'spacy',
    'opencv', 'yolo', 'cnn', 'rnn', 'lstm', 'bert', 'gpt', 'llm',
    
    # Big Data
    'hadoop', 'spark', 'hive', 'kafka', 'flink', 'storm', 'airflow', 'databricks',
    
    # Business Intelligence
    'tableau', 'power bi', 'powerbi', 'looker', 'qlik', 'sap', 'crystal reports', 'ssrs',
    
    # Tools & Platforms
    'jira', 'confluence', 'slack', 'trello', 'postman', 'swagger', 'vs code', 'intellij',
    'eclipse', 'pycharm', 'jupyter', 'google colab', 'anaconda',
    
    # Testing
    'selenium', 'junit', 'testng', 'pytest', 'jest', 'mocha', 'cypress', 'cucumber',
    
    # Mobile
    'android', 'ios', 'react native', 'flutter', 'xamarin', 'ionic',
    
    # API & Microservices
    'rest', 'restful', 'soap', 'graphql', 'grpc', 'microservices', 'api',
    
    # Security
    'oauth', 'jwt', 'ssl', 'encryption', 'penetration testing', 'cybersecurity',
    
    # Payment & Integration
    'paypal', 'razorpay', 'stripe', 'payment gateway',
    
    # Other
    'latex', 'autocad', 'solidworks', 'photoshop', 'illustrator', 'figma', 'sketch',
    'servicenow', 'salesforce', 'erp', 'crm', 'agile', 'scrum', 'kanban',
    'excel', 'powerpoint', 'word', 'htaccess', 'json', 'xml', 'yaml'
}

# Noise words to exclude
NON_SKILL_TERMS = {
    'the', 'and', 'or', 'in', 'at', 'by', 'for', 'with', 'to', 'from', 'using', 'used',
    'year', 'years', 'month', 'months', 'experience', 'role', 'team', 'based', 'etc',
    'including', 'other', 'various', 'well', 'work', 'worked', 'working', 'job', 'position',
    'company', 'project', 'projects', 'application', 'applications', 'system', 'systems',
    'strong', 'excellent', 'good', 'knowledge', 'skills', 'requirements', 'required',
    'preferred', 'must', 'should', 'ability', 'experience', 'developing', 'implementing'
}

# Education qualifications
EDUCATION = [
    "bachelor's degree", "master's degree", "phd", "b.tech", "m.tech", "bsc", "msc",
    "b.e.", "m.e.", "b.s.", "m.s.", "doctorate", "bachelor", "master"
]


def clean_text(text: str) -> str:
    """Clean the input text"""
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text


def extract_skills_from_jd(text: str) -> List[str]:
    """
    Extract technical skills from job description.
    Optimized for LinkedIn "About this job" format.
    """
    text_lower = text.lower()
    found_skills = set()
    
    print("\n🔍 Extracting skills from job description...")
    
    # 1. Direct matching with known skills (most reliable)
    for skill in KNOWN_TECHNICAL_SKILLS:
        # Create pattern with word boundaries
        pattern = rf'\b{re.escape(skill)}\b'
        if re.search(pattern, text_lower):
            found_skills.add(skill)
    
    print(f"   ✅ Found {len(found_skills)} skills from direct matching")
    
    # 2. Extract from bullet points and lists
    # LinkedIn often uses bullet points for skills
    bullet_patterns = [
        r'[•\-\*]\s*([A-Za-z0-9\s\.\+#/\-]+)',  # Bullet points
        r'(?:^|\n)\s*[\d]+[\.\)]\s*([A-Za-z0-9\s\.\+#/\-]+)',  # Numbered lists
    ]
    
    for pattern in bullet_patterns:
        matches = re.finditer(pattern, text, re.MULTILINE)
        for match in matches:
            item = match.group(1).strip().lower()
            # Check if item contains known skills
            for skill in KNOWN_TECHNICAL_SKILLS:
                if skill in item:
                    found_skills.add(skill)
    
    # 3. Extract from skill sections
    # Look for sections like "Required Skills:", "Technologies:", etc.
    skill_section_patterns = [
        r'(?:required\s+skills?|technologies?|technical\s+skills?|tools?)\s*[:\-]?\s*(.{0,500}?)(?:\n\n|\n[A-Z]|$)',
        r'(?:knowledge\s+of|experience\s+with|proficient\s+in)\s*[:\-]?\s*(.{0,300}?)(?:\.|,|\n|$)',
    ]
    
    for pattern in skill_section_patterns:
        matches = re.finditer(pattern, text_lower, re.IGNORECASE | re.DOTALL)
        for match in matches:
            section_text = match.group(1)
            # Extract skills from this section
            for skill in KNOWN_TECHNICAL_SKILLS:
                if skill in section_text:
                    found_skills.add(skill)
    
    # 4. Extract from comma-separated lists
    # LinkedIn often lists skills like "Python, Django, REST API"
    comma_list_pattern = r'(?:skills?|technologies?|tools?|experience)\s*[:\-]?\s*([A-Za-z0-9\s\.,/\+#\-]+?)(?:\n|$)'
    matches = re.finditer(comma_list_pattern, text_lower, re.MULTILINE)
    
    for match in matches:
        items = match.group(1).split(',')
        for item in items:
            item_clean = item.strip()
            # Check if this item is a known skill
            for skill in KNOWN_TECHNICAL_SKILLS:
                if skill == item_clean or (len(skill) > 3 and skill in item_clean):
                    found_skills.add(skill)
    
    # 5. Extract version numbers (Python 3, Django 4.x, etc.)
    version_pattern = r'\b([a-z]+)\s+[\d\.x]+\b'
    for match in re.finditer(version_pattern, text_lower):
        base_skill = match.group(1)
        if base_skill in KNOWN_TECHNICAL_SKILLS:
            found_skills.add(base_skill)
    
    # 6. Extract compound skills (e.g., "REST/SOAP API", "HTML5/CSS3")
    compound_pattern = r'\b([a-z]+)[/\-]([a-z]+)\b'
    for match in re.finditer(compound_pattern, text_lower):
        for skill_part in match.groups():
            if skill_part in KNOWN_TECHNICAL_SKILLS:
                found_skills.add(skill_part)
    
    # 7. Handle abbreviations in parentheses (e.g., "Application Programming Interface (API)")
    abbrev_pattern = r'\(([A-Z]+)\)'
    for match in re.finditer(abbrev_pattern, text):
        abbrev = match.group(1).lower()
        if abbrev in KNOWN_TECHNICAL_SKILLS:
            found_skills.add(abbrev)
    
    cleaned_skills = sorted(list(found_skills))
    
    print(f"✅ FINAL: Extracted {len(cleaned_skills)} skills from job description")
    print(f"   Skills: {cleaned_skills[:10]}")
    if len(cleaned_skills) > 10:
        print(f"   ... and {len(cleaned_skills) - 10} more")
    
    return cleaned_skills


def extract_job_title(text: str) -> str:
    """Extract job title from text"""
    # Look for common patterns
    patterns = [
        r'job\s+title\s*[:\-]\s*(.+?)(?:\n|$)',
        r'^([A-Za-z\s/]+(?:engineer|developer|analyst|designer|manager|architect|scientist))',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            title = match.group(1).strip()
            # Clean up
            title = re.sub(r'\s+', ' ', title)
            return title
    
    # Fallback: First line if it looks like a title
    first_line = text.split('\n')[0].strip()
    if len(first_line.split()) <= 8 and not first_line.startswith(('About', 'Job', 'Company')):
        return first_line
    
    return "Position Not Specified"


def extract_experience(text: str) -> Optional[str]:
    """Extract experience requirements"""
    patterns = [
        r'(\d+[\+\-]?\s*(?:to|\-)?\s*\d*\s*years?\s+(?:of\s+)?(?:work\s+)?experience)',
        r'(?:minimum|min|at\s*least)\s*(\d+)\s*(?:\+)?\s*years?',
        r'experience\s*[:\-]\s*(\d+[\+\-]?\s*(?:to|\-)?\s*\d*\s*years?)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            return match.group(1).strip()
    
    return None


def extract_location(text: str) -> Optional[str]:
    """Extract location"""
    patterns = [
        r'location\s*[:\-]\s*([^\n]+?)(?:\n|$)',
        r'based\s+in\s+([^\n,]+)',
        r'city\s*[:\-]\s*([^\n]+?)(?:\n|$)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            location = match.group(1).strip()
            # Clean up
            location = re.sub(r'\s*[\-–]\s*$', '', location)
            return location
    
    return None


def extract_education(text: str) -> List[str]:
    """Extract education requirements"""
    text_lower = text.lower()
    found_education = set()
    
    for edu in EDUCATION:
        if re.search(rf'\b{re.escape(edu)}\b', text_lower):
            found_education.add(edu)
    
    return sorted(list(found_education))


def parse_job_description(text: str) -> Dict:
    """
    Main function to parse LinkedIn job description.
    Optimized for LinkedIn's "About this job" format.
    """
    
    skills = extract_skills_from_jd(text)
    
    result = {
        'title': extract_job_title(text),
        'skills': skills,
        'experience': extract_experience(text),
        'education': extract_education(text),
        'location': extract_location(text),
        'raw_text': text[:500]  # Keep first 500 chars for debugging
    }
    
    return result


# Test with your example
if __name__ == "__main__":
    sample_jd = """
Job Title – Sr. Python Developer
Company - Sum Circle Technologies Pvt Ltd
Location - Mumbai-
Job type - Full-time in office
Minimum Experience- 3-4 Years

Design and implement robust and scalable web applications using Python and the Django
framework.
Excellent debugging, optimisation, problem-solving skills & Interpersonal skills,
Able to work under pressure, use own initiative and motivation to meet deadlines.
Create and maintain project documentation, including technical specifications and user guides.
Knowledge of front-end frameworks (e.g., React, Vue.js).
Developing API (REST/SOAP) with JSON .
Payment gateway integration like PayPal, Razor-pay, etc.
API implementation For Social Media Platforms.
Well known with technologies such as Html5 ,Ajax, JQUERY
Well versed with GIT repository
Working Knowledge of .htaccess, and linux

Requirements added by the job poster
• 3+ years of work experience with Django
• Can start immediately
• 3+ years of work experience with Python (Programming Language)
"""
    
    result = parse_job_description(sample_jd)
    
    print("\n" + "="*70)
    print("PARSED JOB DESCRIPTION")
    print("="*70)
    print(f"Title: {result['title']}")
    print(f"Location: {result['location']}")
    print(f"Experience: {result['experience']}")
    print(f"\nSkills Extracted ({len(result['skills'])}):")
    for skill in result['skills']:
        print(f"  • {skill}")
    print(f"\nEducation: {result['education']}")
    print("="*70)