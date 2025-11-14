import spacy
import re
from typing import Dict, Optional, List

# Load spaCy model
nlp = spacy.load('en_core_web_sm')

# Common technical terms that often indicate a skill
SKILL_INDICATORS = [
    'proficient in', 'experience with', 'knowledge of', 'skilled in', 'expertise in',
    'working knowledge', 'technical skills', 'technologies', 'languages', 'frameworks',
    'tools', 'platforms', 'programming', 'software', 'development', 'technologies:',
    'skills:', 'competencies:', 'requirements:', 'qualifications:', 'proficiency in',
    'familiarity with', 'background in', 'understanding of', 'mastery of',
    'ability to use', 'strong', 'advanced', 'intermediate', 'basic'
]

# Common skills by role categories
ROLE_SKILLS = {
    'technical': {
        # Programming Languages
        'python': ['python', 'django', 'flask', 'fastapi', 'pandas', 'numpy'],
        'java': ['java', 'spring', 'hibernate', 'maven', 'gradle'],
        'javascript': ['javascript', 'typescript', 'node.js', 'react', 'angular', 'vue'],
        'cpp': ['c++', 'c', 'c#', '.net'],
        
        # Data Skills
        'sql': ['sql', 'mysql', 'postgresql', 'oracle', 'mongodb', 'database'],
        'data_analysis': ['excel', 'power bi', 'tableau', 'data visualization', 'statistics'],
        'big_data': ['hadoop', 'spark', 'hive', 'kafka', 'big data'],
        
        # Cloud & DevOps
        'cloud': ['aws', 'azure', 'gcp', 'cloud computing', 'cloud native'],
        'devops': ['docker', 'kubernetes', 'jenkins', 'ci/cd', 'terraform'],
        
        # AI/ML
        'machine_learning': ['machine learning', 'deep learning', 'ai', 'neural networks'],
        'ml_frameworks': ['tensorflow', 'pytorch', 'scikit-learn', 'keras'],
        
        # Mobile
        'mobile': ['android', 'ios', 'swift', 'kotlin', 'react native', 'flutter'],
        
        # Web
        'frontend': ['html', 'css', 'javascript', 'react', 'angular', 'vue'],
        'backend': ['api', 'rest', 'graphql', 'microservices', 'server'],
        
        # Security
        'security': ['cybersecurity', 'encryption', 'security', 'penetration testing'],
        
        # Tools
        'version_control': ['git', 'github', 'gitlab', 'bitbucket'],
        'ide': ['vs code', 'intellij', 'eclipse', 'pycharm'],
        'office': ['microsoft office', 'excel', 'powerpoint', 'word']
    },
    'soft': {
        # Common soft skills across roles
        'communication': ['communication', 'presentation', 'verbal', 'written'],
        'analytical': ['analytical', 'problem solving', 'critical thinking', 'attention to detail'],
        'leadership': ['leadership', 'team management', 'mentoring', 'strategic thinking'],
        'project_mgmt': ['project management', 'agile', 'scrum', 'jira'],
        'interpersonal': ['teamwork', 'collaboration', 'interpersonal', 'relationship building'],
        'business': ['business acumen', 'stakeholder management', 'client relations'],
        'time_mgmt': ['time management', 'prioritization', 'multitasking', 'organization'],
        'learning': ['continuous learning', 'adaptability', 'quick learner', 'self-motivated']
    }
}

# Patterns that might indicate a skill
SKILL_PATTERNS = [
    r'[\•\-\★\✓\✔\→\♦\♠\◆\◊\∙\○\●\⚬\⦿\⬤\⚫\⚪\⭐]\s*([A-Za-z0-9#\+\.\-]+(?:\s*[A-Za-z0-9#\+\.\-]+)*)',  # Bullet points
    r'(?:^|\n)([A-Za-z0-9#\+\.\-]+(?:\s*[A-Za-z0-9#\+\.\-]+)*?)(?:\s*,|\s*$|\s*\n)',  # Comma-separated or newline
    r'(?:' + '|'.join(SKILL_INDICATORS) + r')\s*[:-]?\s*([A-Za-z0-9#\+\.\-]+(?:\s*[A-Za-z0-9#\+\.\-]+)*)'  # After skill indicators
]

# Terms that are likely not skills
NON_SKILL_TERMS = {
    'the', 'and', 'or', 'in', 'at', 'by', 'for', 'with', 'to', 'from',
    'year', 'years', 'month', 'months', 'experience', 'role', 'team',
    'based', 'using', 'etc', 'including', 'other', 'various', 'well'
}

# Education qualifications
EDUCATION = [
    "bachelor's degree", "master's degree", "phd", "b.tech", "m.tech", "bsc", "msc",
    "b.e.", "m.e.", "b.s.", "m.s.", "doctorate", "bachelor", "master"
]

def clean_text(text: str) -> str:
    """Clean the input text by removing extra whitespace and normalizing"""
    text = re.sub(r'\s+', ' ', text)
    text = text.strip().lower()
    return text

def extract_job_title(text: str) -> Dict[str, str]:
    """
    Extract job title and role details from the text using NLP and pattern matching.
    Returns a dictionary containing title components.
    """
    # Define role patterns
    SENIORITY_LEVELS = [
        'senior', 'junior', 'lead', 'principal', 'staff', 'associate', 'entry level',
        'mid level', 'director', 'head', 'chief', 'vp', 'manager'
    ]
    
    ROLE_DOMAINS = [
        'software', 'data', 'cloud', 'devops', 'full.?stack', 'front.?end', 'back.?end',
        'mobile', 'web', 'ai', 'ml', 'security', 'system', 'network', 'database',
        'ui', 'ux', 'qa', 'test', 'product', 'project', 'business', 'sales',
        'marketing', 'hr', 'finance', 'operations', 'research'
    ]
    
    ROLE_TYPES = [
        'engineer', 'developer', 'architect', 'scientist', 'analyst', 'administrator',
        'manager', 'designer', 'consultant', 'specialist', 'coordinator', 'lead',
        'director', 'officer', 'associate', 'technician', 'head', 'evangelist'
    ]
    
    doc = nlp(text)
    
    # Initialize result
    result = {
        'full_title': None,
        'seniority': None,
        'domain': None,
        'role_type': None
    }
    
    # Look for job title patterns
    title_patterns = [
        # Standard format: [seniority] [domain] [role]
        r'(?i)([A-Za-z\s]*(?:' + '|'.join(ROLE_DOMAINS) + r')?\s*(?:' + '|'.join(ROLE_TYPES) + r'))',
        # Role with explicit title
        r'(?i)(position|role|job title|job position|opening)[\s:]+(.*?)(?:\n|$)',
        # Job posting header format
        r'(?i)^([^:\n]+?)(?::\s|\n|$)'
    ]
    
    # Try to extract full title
    for pattern in title_patterns:
        match = re.search(pattern, text)
        if match:
            result['full_title'] = match.group(1).strip()
            break
            
    # If no match found, try first sentence if it looks like a title
    if not result['full_title']:
        first_sent = next(doc.sents).text.strip()
        if len(first_sent.split()) <= 10:  # Reasonable length for a title
            result['full_title'] = first_sent
    
    if result['full_title']:
        # Clean the title
        title_text = result['full_title'].lower()
        
        # Extract seniority
        for level in SENIORITY_LEVELS:
            if level in title_text:
                result['seniority'] = level
                break
        
        # Extract domain
        for domain in ROLE_DOMAINS:
            if domain in title_text:
                result['domain'] = domain
                break
        
        # Extract role type
        for role in ROLE_TYPES:
            if role in title_text:
                result['role_type'] = role
                break
    
    return result

def extract_skills(text: str) -> Dict[str, Dict[str, List[str]]]:
    """
    Extract and categorize skills from text using NLP and pattern matching.
    Returns skills categorized by both type (technical/soft) and domain.
    """
    found_skills = {
        'technical': {},
        'soft': {},
        'other': set()  # For skills that don't match our predefined categories
    }
    
    # Clean and normalize the text
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    doc = nlp(text)
    
    # Extract all potential skills using various methods
    potential_skills = set()
    
    # 1. Extract from bullet points and skill sections
    for pattern in SKILL_PATTERNS:
        matches = re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE)
        for match in matches:
            skill = match.group(1).strip().lower()
            if len(skill) > 2 and not any(term in skill.split() for term in NON_SKILL_TERMS):
                potential_skills.add(skill)
    
    # 2. Extract from noun phrases using spaCy
    for chunk in doc.noun_chunks:
        if len(chunk.text) > 2 and not any(term in chunk.text.lower().split() for term in NON_SKILL_TERMS):
            potential_skills.add(chunk.text.strip().lower())
    
    # 3. Look for known skills from our ROLE_SKILLS dictionary
    for skill_type, categories in ROLE_SKILLS.items():
        for category, skill_list in categories.items():
            category_skills = []
            for skill in skill_list:
                # Look for exact matches
                if skill in text:
                    category_skills.append(skill)
                    continue
                
                # Look for variations
                skill_pattern = rf'\b{re.escape(skill)}\b'
                if re.search(skill_pattern, text, re.IGNORECASE):
                    category_skills.append(skill)
            
            if category_skills:
                found_skills[skill_type][category] = category_skills
    
    # 4. Process potential skills that weren't categorized
    for skill in potential_skills:
        # Skip if already categorized
        if any(skill in skills for skills_dict in found_skills.values() 
               if isinstance(skills_dict, dict) 
               for skills in skills_dict.values()):
            continue
        
        # Try to categorize the skill
        categorized = False
        for skill_type, categories in ROLE_SKILLS.items():
            for category, known_skills in categories.items():
                # Check if the skill is similar to any known skills
                if any(known_skill in skill or skill in known_skill for known_skill in known_skills):
                    if category not in found_skills[skill_type]:
                        found_skills[skill_type][category] = []
                    found_skills[skill_type][category].append(skill)
                    categorized = True
                    break
            if categorized:
                break
        
        # If not categorized, add to other
        if not categorized and len(skill.split()) <= 3:  # Limit to reasonable length terms
            found_skills['other'].add(skill)
    
    # Convert other skills set to sorted list
    found_skills['other'] = sorted(list(found_skills['other']))
    
    # Sort skills within each category
    for skill_type in ['technical', 'soft']:
        for category in found_skills[skill_type]:
            found_skills[skill_type][category] = sorted(list(set(found_skills[skill_type][category])))
    
    return found_skills

def extract_experience(text: str) -> Optional[str]:
    """Extract experience requirements using regex patterns"""
    patterns = [
        r'(\d+[\+]?\s*[-]?\s*\d*\s*(?:years|yrs|yr)(?:\s+(?:of\s+)?experience)?)',
        r'(?:minimum|min|at\s*least)\s*(\d+)\s*(?:years|yrs|yr)',
        r'experience\s*(?:of|for)?\s*(\d+[\+]?\s*[-]?\s*\d*\s*(?:years|yrs|yr))'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            return match.group(0).strip()
    
    return None

def extract_education(text: str) -> List[str]:
    """Extract education requirements"""
    text = clean_text(text)
    found_education = set()
    
    for edu in EDUCATION:
        if re.search(rf'\b{edu}\b', text):
            found_education.add(edu)
    
    return sorted(list(found_education))

def extract_location(text: str) -> Optional[str]:
    """Extract location if mentioned with 'Location:' pattern"""
    patterns = [
        r'location\s*:\s*([^,\n]+(?:,\s*[^,\n]+)?)',
        r'(?:based\s+in|working\s+from)\s+([^,\n]+(?:,\s*[^,\n]+)?)',
        r'(?:location|city|place)[\s:]+([\w\s,]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            return match.group(1).strip().title()  # Title case for location names
    
    return None

def parse_job_description(text: str) -> Dict:
    """Main function to parse job description and extract all required information"""
    return {
        'job_details': extract_job_title(text),
        'skills': extract_skills(text),
        'experience': extract_experience(text),
        'education': extract_education(text),
        'location': extract_location(text)
    }

# Example usage
if __name__ == "__main__":
    # Example job descriptions for different roles
    sample_jds = [
        """
        Senior Software Engineer
        Location: Bangalore, Karnataka
        
        We are looking for a Senior Software Engineer with 5+ years of experience in Python and AWS.
        The ideal candidate should have a Bachelor's degree in Computer Science or related field.
        
        Required Skills:
        - Python, JavaScript
        - React, Node.js
        - AWS, Docker
        - Git, Jenkins
        
        Soft Skills:
        - Strong problem-solving abilities
        - Excellent communication skills
        - Team player with leadership qualities
        
        Education: Bachelor's degree required, Master's preferred
        """,
        
        """
        Data Analyst
        Location: Mumbai, Maharashtra
        
        Looking for a Data Analyst to join our analytics team. Fresh graduates welcome.
        
        Technical Requirements:
        - Proficient in Excel and SQL
        - Experience with Power BI or Tableau
        - Python/R knowledge is a plus
        
        Key Responsibilities:
        - Analyze large datasets
        - Create visualizations and dashboards
        - Prepare reports for stakeholders
        
        Education: Bachelor's degree in any quantitative field
        """,
        
        """
        UI/UX Designer
        Location: Pune
        
        Join our creative team as a UI/UX Designer!
        
        Required Skills:
        - Figma, Adobe XD
        - HTML/CSS
        - User Research
        - Wireframing and Prototyping
        
        Qualities we're looking for:
        - Creative mindset
        - Attention to detail
        - User-centric approach
        
        Experience: 2-3 years in similar role
        Education: Degree in Design/HCI preferred
        """
    ]
    
    # Parse each job description
    for i, jd in enumerate(sample_jds, 1):
        result = parse_job_description(jd)
        
        print(f"\nParsed Job Description #{i}")
        print("-" * 50)
        
        # Print job details
        job_details = result['job_details']
        print(f"Full Title: {job_details['full_title']}")
        print(f"Seniority: {job_details['seniority']}")
        print(f"Domain: {job_details['domain']}")
        print(f"Role Type: {job_details['role_type']}")
        
        # Print location and experience
        print(f"\nLocation: {result['location']}")
        print(f"Experience Required: {result['experience']}")
        
        # Print skills by category
        print("\nRequired Skills:")
        skills = result['skills']
        
        print("\nTechnical Skills:")
        for category, category_skills in skills['technical'].items():
            print(f"  {category.replace('_', ' ').title()}:")
            for skill in category_skills:
                print(f"    - {skill}")
        
        print("\nSoft Skills:")
        for category, category_skills in skills['soft'].items():
            print(f"  {category.replace('_', ' ').title()}:")
            for skill in category_skills:
                print(f"    - {skill}")
        
        if skills['other']:
            print("\nOther Skills/Keywords:")
            for skill in skills['other']:
                print(f"  - {skill}")
        
        print("\nEducation Requirements:")
        for edu in result['education']:
            print(f"- {edu}")
        
        print("\n" + "="*50)
