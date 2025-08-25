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
    'skills:', 'competencies:', 'requirements:', 'qualifications:'
]

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

def extract_job_title(text: str) -> Optional[str]:
    """Extract job title from the text using spaCy's NER and pattern matching"""
    doc = nlp(text)
    
    # Look for job title patterns
    title_patterns = [
        r'(?i)(senior|junior|lead|principal)?\s*(software|data|cloud|devops|full.?stack|front.?end|back.?end)?\s*(engineer|developer|architect|scientist|analyst)',
        r'(?i)(position|role|job title|job position)[\s:]+(.*?)(\n|$)'
    ]
    
    for pattern in title_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0).strip()
            
    # Fallback to first sentence if it contains relevant keywords
    first_sent = next(doc.sents)
    if any(word in first_sent.text.lower() for word in ['engineer', 'developer', 'architect', 'analyst']):
        return first_sent.text.strip()
    
    return None

def extract_skills(text: str) -> List[str]:
    """Extract skills from text using NLP and pattern matching"""
    found_skills = set()
    
    # Clean the text while preserving structure
    text = re.sub(r'\s+', ' ', text)
    
    # Extract skills using various patterns
    for pattern in SKILL_PATTERNS:
        matches = re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE)
        for match in matches:
            skill = match.group(1).strip()
            # Convert to lowercase for comparison
            skill_lower = skill.lower()
            
            # Skip if the skill is too short or contains unwanted terms
            if len(skill) < 2 or any(term in skill_lower.split() for term in NON_SKILL_TERMS):
                continue
                
            # Add the original case version of the skill
            found_skills.add(skill)
    
    # Use spaCy for additional skill extraction
    doc = nlp(text)
    
    # Extract noun phrases that might be skills
    for chunk in doc.noun_chunks:
        # Skip if the chunk contains unwanted terms
        if any(term in chunk.text.lower().split() for term in NON_SKILL_TERMS):
            continue
        
        # Look for technical terms and proper nouns
        if any(token.pos_ in ['PROPN', 'NOUN'] for token in chunk):
            skill = chunk.text.strip()
            if len(skill) >= 2:  # Skip very short terms
                found_skills.add(skill)
    
    # Clean up skills
    cleaned_skills = set()
    for skill in found_skills:
        # Remove trailing punctuation and spaces
        skill = re.sub(r'[^\w\s\+#\.-]$', '', skill).strip()
        if skill and not any(term in skill.lower().split() for term in NON_SKILL_TERMS):
            cleaned_skills.add(skill)
    
    # Sort skills by length (shorter ones first) and then alphabetically
    return sorted(list(cleaned_skills), key=lambda x: (len(x), x.lower()))

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
        'title': extract_job_title(text),
        'skills': extract_skills(text),
        'experience': extract_experience(text),
        'education': extract_education(text),
        'location': extract_location(text)
    }

# Example usage
if __name__ == "__main__":
    # Example job description
    sample_jd = """
    Senior Software Engineer
    Location: Bangalore, Karnataka
    
    We are looking for a Senior Software Engineer with 5+ years of experience in Python and AWS.
    The ideal candidate should have a Bachelor's degree in Computer Science or related field.
    
    Required Skills:
    - Python, JavaScript
    - React, Node.js
    - AWS, Docker
    - Git, Jenkins
    
    Education: Bachelor's degree required, Master's preferred
    """
    
    # Parse the job description
    result = parse_job_description(sample_jd)
    
    # Print the results in a formatted way
    print("\nParsed Job Description:")
    print("-" * 50)
    print(f"Title: {result['title']}")
    print(f"\nLocation: {result['location']}")
    print(f"\nExperience Required: {result['experience']}")
    
    print("\nRequired Skills:")
    for skill in result['skills']:
        print(f"- {skill}")
    
    print("\nEducation Requirements:")
    for edu in result['education']:
        print(f"- {edu}")
