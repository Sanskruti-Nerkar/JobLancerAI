import os
import spacy
import pdfplumber
import phonenumbers
import re
from typing import Dict, List, Optional, Union
from pathlib import Path

# Load spaCy model
nlp = spacy.load('en_core_web_sm')

# Load spaCy for more advanced NLP features
try:
    nlp = spacy.load('en_core_web_lg')  # Try to load the large model for better entity recognition
except OSError:
    nlp = spacy.load('en_core_web_sm')  # Fall back to small model if large isn't available

# Skill normalization mapping
SKILL_ALIASES = {
    'javascript': ['js', 'javascript', 'node.js', 'nodejs'],
    'python': ['py', 'python3', 'python 3'],
    'machine learning': ['ml', 'machine-learning', 'machinelearning'],
    'artificial intelligence': ['ai', 'artificial-intelligence'],
    'microsoft office': ['ms office', 'office', 'microsoft-office'],
    'microsoft excel': ['ms excel', 'excel'],
    'microsoft word': ['ms word', 'word'],
    'power bi': ['powerbi', 'power-bi'],
    'amazon web services': ['aws', 'amazon-web-services'],
    'sql': ['mysql', 'postgresql', 'oracle', 'sqlserver', 'sql server'],
    'data analysis': ['data analytics', 'data analyst', 'data analysis'],
    'version control': ['git', 'github', 'gitlab', 'bitbucket'],
    'deep learning': ['dl', 'deep-learning'],
    'business intelligence': ['bi', 'business-intelligence']
}

EDUCATION = [
    "bachelor's degree", "master's degree", "phd", "b.tech", "m.tech", "bsc", "msc",
    "b.e.", "m.e.", "b.s.", "m.s.", "doctorate", "bachelor", "master"
]

class ResumeParser:
    def __init__(self, resume_dir: str):
        """
        Initialize the resume parser with a directory containing resumes.
        Args:
            resume_dir (str): Path to directory containing resume PDFs
        """
        self.resume_dir = Path(resume_dir)
        if not self.resume_dir.exists():
            raise FileNotFoundError(f"Directory not found: {resume_dir}")

    def _extract_text_from_pdf(self, pdf_path: Path) -> str:
        """Extract raw text from a PDF file"""
        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            print(f"Error reading PDF {pdf_path.name}: {e}")
            return ""
        return text

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        text = re.sub(r'\s+', ' ', text)
        text = text.strip().lower()
        return text

    def _extract_name(self, text: str) -> Optional[str]:
        """Extract full name using spaCy NER"""
        # Look for PERSON entities in the first few lines
        first_page = "\n".join(text.split("\n")[:5])
        doc = nlp(first_page)
        
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                return ent.text.strip()
        return None

    def _extract_email(self, text: str) -> Optional[str]:
        """Extract email address"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        match = re.search(email_pattern, text)
        return match.group(0) if match else None

    def _extract_phone(self, text: str) -> Optional[str]:
        """Extract phone number"""
        pattern = r'[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}'
        matches = re.finditer(pattern, text)
        
        for match in matches:
            try:
                number = phonenumbers.parse(match.group(), "US")
                if phonenumbers.is_valid_number(number):
                    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
            except:
                continue
        return None

    def _extract_skills(self, text: str) -> Dict[str, List[str]]:
        """Extract skills using NLP and pattern matching"""
        text = self._clean_text(text)
        technical_skills = set()
        soft_skills = set()
        
        # Keywords that indicate technical skills sections
        tech_section_indicators = [
            "technical skills", "technologies", "programming", "languages",
            "tools", "frameworks", "software", "platforms", "databases"
        ]
        
        # Keywords that indicate soft skills sections
        soft_section_indicators = [
            "soft skills", "personal skills", "interpersonal", "professional skills",
            "core competencies", "strengths"
        ]
        
        # Common technical skill keywords
        tech_keywords = [
            "programming", "software", "database", "framework", "language",
            "tool", "platform", "system", "technology", "application", "data",
            "code", "development", "analysis", "design", "implementation"
        ]
        
        # Common soft skill keywords
        soft_keywords = [
            "communication", "leadership", "teamwork", "management", "organization",
            "problem solving", "analytical", "creativity", "interpersonal",
            "presentation", "collaboration", "adaptability"
        ]
        
        doc = nlp(text)
        current_section = None
        
        # Process each sentence
        for sent in doc.sents:
            sent_text = sent.text.lower()
            
            # Determine section type
            if any(indicator in sent_text for indicator in tech_section_indicators):
                current_section = "technical"
                continue
            elif any(indicator in sent_text for indicator in soft_section_indicators):
                current_section = "soft"
                continue
            
            # Extract noun phrases as potential skills
            for chunk in sent.noun_chunks:
                skill = chunk.text.lower().strip()
                
                # Skip if too short or contains unwanted words
                if len(skill) < 3 or any(word in skill for word in ['the', 'and', 'or', 'in', 'on', 'at', 'to', 'for']):
                    continue
                
                # Categorize based on keywords and context
                if (current_section == "technical" or 
                    any(keyword in skill for keyword in tech_keywords)):
                    technical_skills.add(skill)
                elif (current_section == "soft" or 
                      any(keyword in skill for keyword in soft_keywords)):
                    soft_skills.add(skill)
        
        # Look for specific technical patterns
        tech_patterns = [
            r'\b[A-Za-z]+[\+\#]?\+{0,2}\b',  # Programming languages (C++, C#)
            r'\b[A-Za-z]+\.?js\b',  # JavaScript frameworks
            r'\b[A-Za-z]+SQL\b',  # SQL variants
            r'\b[A-Za-z]+-?[Ss]tack\b',  # Tech stacks
            r'[A-Z][A-Za-z]*(?:\s*[A-Z][A-Za-z]*)+',  # CamelCase product names
        ]
        
        for pattern in tech_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                skill = match.group().lower()
                technical_skills.add(skill)
        
        # Clean and normalize skills
        cleaned_tech_skills = set()
        cleaned_soft_skills = set()
        
        # Months to filter out
        months = {'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'}
        
        for skill in technical_skills:
            skill = skill.strip().strip('.,;')
            
            # Skip common words, months, and noisy terms
            if (len(skill) <= 2 or 
                skill in months or
                skill.isdigit() or
                skill in {'and', 'the', 'with', 'using', 'for', 'from', 'in', 'on', 'at', 'to'} or
                any(word in skill for word in ['using', 'with', 'and', 'the', 'for', 'from'])):
                continue
                
            # Clean up compound skills
            parts = skill.split()
            if len(parts) > 1:
                # If it starts with common verbs, remove them
                if parts[0] in {'using', 'developed', 'implemented', 'built', 'designed', 'created'}:
                    skill = ' '.join(parts[1:])
            
            # Normalize skill using aliases
            normalized_skill = skill
            for main_skill, aliases in SKILL_ALIASES.items():
                if skill in aliases or skill == main_skill.lower():
                    normalized_skill = main_skill
                    break
            
            # Add clean skill
            cleaned_tech_skills.add(normalized_skill)
        
        for skill in soft_skills:
            skill = skill.strip().strip('.,;')
            if (len(skill) > 2 and 
                skill not in months and
                not skill.isdigit()):
                cleaned_soft_skills.add(skill)
        
        print("\nDebug: Skills extraction")
        print("Technical skills:", cleaned_tech_skills)
        print("Soft skills:", cleaned_soft_skills)
        
        return {
            'technical': sorted(list(cleaned_tech_skills)),
            'soft': sorted(list(cleaned_soft_skills))
        }
        
        print("\nDebug: Skills extraction")
        print(f"Found skills: {cleaned_skills}")
        
        return sorted(list(cleaned_skills))

    def _extract_education(self, text: str) -> List[str]:
        """Extract education qualifications"""
        text = self._clean_text(text)
        found_education = set()
        
        for edu in EDUCATION:
            if re.search(rf'\b{edu}\b', text):
                found_education.add(edu)
        
        return sorted(list(found_education))

    def _extract_experience_years(self, text: str) -> Optional[int]:
        """Extract total years of experience"""
        experience_patterns = [
            r'(\d+)\+?\s*(?:years|yrs|yr)(?:\s+of\s+)?(?:experience|work)',
            r'(?:experience|work)(?:\s+of\s+)?(\d+)\+?\s*(?:years|yrs|yr)',
        ]
        
        max_years = 0
        for pattern in experience_patterns:
            matches = re.finditer(pattern, text.lower())
            for match in matches:
                try:
                    years = int(match.group(1))
                    max_years = max(max_years, years)
                except:
                    continue
        
        return max_years if max_years > 0 else None

    def parse_resume(self, file_name: str) -> Dict[str, Union[str, List[str], int, None]]:
        """
        Parse a single resume and extract information.
        Args:
            file_name (str): Name of the resume PDF file in the resume directory
        Returns:
            Dict containing extracted information
        """
        pdf_path = self.resume_dir / file_name
        if not pdf_path.exists():
            return {"error": f"File not found: {file_name}"}

        # Extract text from PDF
        text = self._extract_text_from_pdf(pdf_path)
        if not text:
            return {"error": f"Could not extract text from {file_name}"}
            
        print(f"\nProcessing resume: {file_name}")
        print("Extracted text length:", len(text))

        # Extract all information
        skills_dict = self._extract_skills(text)
        
        # Return parsed information
        return {
            'file_name': file_name,
            'name': self._extract_name(text),
            'email': self._extract_email(text),
            'phone': self._extract_phone(text),
            'technical_skills': skills_dict['technical'],
            'soft_skills': skills_dict['soft'],
            'education': self._extract_education(text),
            'years_of_experience': self._extract_experience_years(text)
        }

    def parse_resumes(self) -> List[Dict]:
        """
        Parse all PDF resumes in the specified directory.
        Returns:
            List of dictionaries containing parsed information for each resume
        """
        results = []
        for pdf_file in self.resume_dir.glob('*.pdf'):
            result = self.parse_resume(pdf_file.name)
            results.append(result)
        return results

def parse_resume_file(file_path: str) -> Dict:
    """
    Standalone function to parse a single resume file.
    Args:
        file_path (str): Full path to the resume PDF file
    Returns:
        Dict containing parsed information
    """
    resume_dir = str(Path(file_path).parent)
    parser = ResumeParser(resume_dir)
    return parser.parse_resume(Path(file_path).name)

if __name__ == "__main__":
    # Example usage
    resume_folder = r"D:\Desktop\Mustafa\7th SEM\PBL\resumes"
    
    # Parse a single resume
    single_resume = "Mustafa_Husain_Resume.pdf"  # Your actual resume filename
    if os.path.exists(os.path.join(resume_folder, single_resume)):
        parser = ResumeParser(resume_folder)
        result = parser.parse_resume(single_resume)
        print("\nParsed Resume Information:")
        print(f"Name: {result.get('name')}")
        print(f"Email: {result.get('email')}")
        print(f"Phone: {result.get('phone')}")
        print(f"\nTechnical Skills: {', '.join(result.get('technical_skills', []))}")
        print(f"Soft Skills: {', '.join(result.get('soft_skills', []))}")
        print(f"Education: {', '.join(result.get('education', []))}")
        print(f"Years of Experience: {result.get('years_of_experience')}")
        

    
    # Parse all resumes in a directory
    if os.path.exists(resume_folder):
        parser = ResumeParser(resume_folder)
        all_resumes = parser.parse_resumes()
        print(f"\nProcessed {len(all_resumes)} resumes:")
        for resume in all_resumes:
            if "error" in resume:
                print(f"Error processing {resume.get('file_name', 'unknown file')}: {resume['error']}")
            else:
                print(f"\nFile: {resume['file_name']}")
                print(f"Name: {resume.get('name')}")
                print(f"Email: {resume.get('email')}")
                print("---")
