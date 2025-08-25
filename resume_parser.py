import os
import spacy
import pdfplumber
import phonenumbers
import re
from typing import Dict, List, Optional, Union
from pathlib import Path

# Load spaCy model
nlp = spacy.load('en_core_web_sm')

# Define skill categories and keywords
SKILLS = {
    'programming': ['python', 'java', 'javascript', 'c++', 'ruby', 'php', 'swift', 'kotlin', 'golang', 'rust'],
    'web': ['html', 'css', 'react', 'angular', 'vue', 'node.js', 'django', 'flask', 'spring'],
    'database': ['sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'oracle'],
    'cloud': ['aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform'],
    'tools': ['git', 'jenkins', 'jira', 'confluence', 'bitbucket', 'gitlab']
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

    def _extract_skills(self, text: str) -> List[str]:
        """Extract technical skills"""
        text = self._clean_text(text)
        found_skills = set()
        
        for category, skills in SKILLS.items():
            for skill in skills:
                if re.search(rf'\b{skill}\b', text):
                    found_skills.add(skill)
        
        return sorted(list(found_skills))

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

        # Return parsed information
        return {
            'file_name': file_name,
            'name': self._extract_name(text),
            'email': self._extract_email(text),
            'phone': self._extract_phone(text),
            'skills': self._extract_skills(text),
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
    resume_folder = r"c:\Users\devya\OneDrive\Documents\PBL 3 (Job Lancer)\resumes"
    
    # Parse a single resume
    single_resume = "example_resume.pdf"  # Replace with actual filename
    if os.path.exists(os.path.join(resume_folder, single_resume)):
        parser = ResumeParser(resume_folder)
        result = parser.parse_resume(single_resume)
        print("\nParsed Resume Information:")
        print(f"Name: {result.get('name')}")
        print(f"Email: {result.get('email')}")
        print(f"Phone: {result.get('phone')}")
        print(f"Skills: {', '.join(result.get('skills', []))}")
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
