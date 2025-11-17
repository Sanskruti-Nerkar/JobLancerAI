import os
import spacy
import pdfplumber
import phonenumbers
import re
from typing import Dict, List, Optional, Union
from pathlib import Path

# Load spaCy model
try:
    nlp = spacy.load('en_core_web_lg')
except OSError:
    nlp = spacy.load('en_core_web_sm')

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

# Comprehensive technical skills list
KNOWN_TECHNICAL_SKILLS = {
    # Programming Languages
    'python', 'java', 'javascript', 'typescript', 'c', 'c++', 'c#', 'php', 'ruby', 'go', 'rust',
    'swift', 'kotlin', 'scala', 'r', 'matlab', 'perl', 'shell', 'bash', 'powershell',
    
    # Web Technologies
    'html', 'css', 'react', 'angular', 'vue', 'node.js', 'express', 'django', 'flask', 'fastapi',
    'spring', 'asp.net', 'jquery', 'bootstrap', 'sass', 'webpack', 'next.js', 'nuxt.js',
    
    # Databases
    'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'cassandra', 'oracle',
    'sqlserver', 'mariadb', 'sqlite', 'dynamodb', 'neo4j', 'couchdb',
    
    # Cloud & DevOps
    'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'gitlab', 'github', 'terraform',
    'ansible', 'chef', 'puppet', 'ci/cd', 'git', 'svn', 'circleci', 'travis', 'cloudformation',
    
    # Data Science & ML
    'machine learning', 'deep learning', 'tensorflow', 'pytorch', 'keras', 'scikit-learn',
    'pandas', 'numpy', 'scipy', 'matplotlib', 'seaborn', 'plotly', 'nltk', 'spacy',
    'opencv', 'yolo', 'cnn', 'rnn', 'lstm', 'bert', 'gpt', 'llm',
    
    # Big Data
    'hadoop', 'spark', 'hive', 'kafka', 'flink', 'storm', 'airflow', 'databricks',
    
    # Business Intelligence
    'tableau', 'power bi', 'looker', 'qlik', 'sap', 'crystal reports', 'ssrs', 'cognos',
    
    # Tools & Platforms
    'linux', 'unix', 'windows', 'macos', 'jira', 'confluence', 'slack', 'trello',
    'postman', 'swagger', 'vs code', 'intellij', 'eclipse', 'pycharm', 'jupyter',
    'google colab', 'anaconda',
    
    # Testing
    'selenium', 'junit', 'testng', 'pytest', 'jest', 'mocha', 'cypress', 'cucumber',
    
    # Mobile
    'android', 'ios', 'react native', 'flutter', 'xamarin', 'ionic',
    
    # API & Microservices
    'rest', 'graphql', 'soap', 'grpc', 'microservices', 'api',
    
    # Security
    'oauth', 'jwt', 'ssl', 'encryption', 'penetration testing', 'cybersecurity',
    
    # Other
    'latex', 'autocad', 'solidworks', 'photoshop', 'illustrator', 'figma', 'sketch',
    'servicenow', 'salesforce', 'sap', 'erp', 'crm', 'agile', 'scrum', 'kanban',
    'vertex ai', 'google cloud', 'spss', 'ibm spss', 'excel', 'powerpoint', 'word'
}

EDUCATION = [
    "bachelor's degree", "master's degree", "phd", "b.tech", "m.tech", "bsc", "msc",
    "b.e.", "m.e.", "b.s.", "m.s.", "doctorate", "bachelor", "master"
]

# Words to exclude (noise)
NOISE_WORDS = {
    'the', 'and', 'or', 'in', 'at', 'by', 'for', 'with', 'to', 'from', 'using', 'used',
    'year', 'years', 'month', 'months', 'experience', 'role', 'team', 'based', 'etc',
    'including', 'other', 'various', 'well', 'work', 'worked', 'working', 'job', 'position',
    'company', 'project', 'projects', 'application', 'applications', 'system', 'systems',
    'build', 'built', 'developed', 'developing', 'development', 'designed', 'design',
    'implemented', 'implementation', 'created', 'creating', 'deployed', 'deploying',
    'world', 'out', 'place', 'time', 'real', 'basic', 'advanced', 'intermediate',
    'summary', 'profile', 'detail', 'education', 'skills', 'technical', 'tools',
    'technologies', 'frameworks', 'libraries', 'platform', 'platforms', 'solution',
    'solutions', 'code', 'programming', 'language', 'languages', 'foundation', 'foundations',
    'among', 'across', 'top', 'higher', 'school', 'institute', 'university', 'expected',
    'secured', 'ranked', 'grade', 'percentage', 'gpa', 'st', 'nd', 'rd', 'th',
    'certified', 'certification', 'certifications', 'certificate', 'course', 'specialization',
    'student', 'practitioner', 'administrator', 'developer', 'engineer', 'author',
    'interests', 'achievements', 'awards', 'publication', 'native', 'fluent', 'proficient',
    'experienced', 'solid', 'strong', 'excellent', 'good', 'website', 'web', 'model', 'models'
}


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
        """Extract skills using IMPROVED pattern matching"""
        text_lower = self._clean_text(text)
        technical_skills = set()
        
        print("\n🔍 Starting skill extraction...")
        print(f"   Text length: {len(text)} characters")
        
        # 1. Extract ALL known skills directly (more aggressive)
        for skill in KNOWN_TECHNICAL_SKILLS:
            pattern = rf'\b{re.escape(skill)}\b'
            if re.search(pattern, text_lower):
                technical_skills.add(skill)
        
        print(f"   ✅ Found {len(technical_skills)} skills from direct matching")
        
        # 2. Extract from Skills section specifically
        skills_section_patterns = [
            r'(?:technical\s+)?skills\s*:?\s*(.{0,800}?)(?:\n\n|education|experience|projects|certifications|$)',
            r'(?:core\s+)?competencies\s*:?\s*(.{0,800}?)(?:\n\n|education|experience|projects|$)',
            r'technologies\s*:?\s*(.{0,800}?)(?:\n\n|education|experience|projects|$)',
        ]
        
        skills_section_text = ""
        for pattern in skills_section_patterns:
            try:
                match = re.search(pattern, text_lower, re.IGNORECASE | re.DOTALL)
                if match:
                    skills_section_text = match.group(1)
                    print(f"   📋 Found skills section ({len(skills_section_text)} chars)")
                    break
            except Exception as e:
                print(f"   ⚠️  Error in pattern matching: {e}")
                continue
        
        # 3. Parse skills section
        if skills_section_text:
            delimiters = r'[,;|•\n\t]|\sand\s|\sor\s'
            try:
                skill_candidates = re.split(delimiters, skills_section_text)
            except Exception:
                skill_candidates = []
            
            for candidate in skill_candidates:
                try:
                    candidate = candidate.strip()
                    candidate = re.sub(r'^[\d\.\-\*\•]+\s*', '', candidate)
                    candidate = candidate.strip()
                    
                    if len(candidate) < 2 or len(candidate) > 40:
                        continue
                    
                    if self._is_valid_skill(candidate):
                        normalized = self._normalize_skill(candidate)
                        technical_skills.add(normalized)
                    
                    for known_skill in KNOWN_TECHNICAL_SKILLS:
                        if len(known_skill) > 3 and known_skill in candidate.lower():
                            technical_skills.add(known_skill)
                except Exception:
                    continue
        
        # 4. Look for skills in experience descriptions
        experience_pattern = r'(?:using|used|with|including|proficient\s+in|experience\s+with|worked\s+with)\s+([a-z0-9\s\.\+#\-,;&]+?)(?:\.|,|\n|to\s|for\s|and\s+other)'
        
        try:
            for match in re.finditer(experience_pattern, text_lower):
                skills_str = match.group(1).strip()
                for skill in re.split(r'[,;&]|\s+and\s+', skills_str):
                    skill = skill.strip()
                    if self._is_valid_skill(skill):
                        normalized = self._normalize_skill(skill)
                        technical_skills.add(normalized)
        except Exception as e:
            print(f"   ⚠️  Error in experience pattern: {e}")
        
        # 5. Check for version numbers
        version_pattern = r'\b([a-z]+)\s+\d+(?:\.\d+)?\b'
        try:
            for match in re.finditer(version_pattern, text_lower):
                base_skill = match.group(1)
                if base_skill in KNOWN_TECHNICAL_SKILLS:
                    technical_skills.add(base_skill)
        except Exception as e:
            print(f"   ⚠️  Error in version pattern: {e}")
        
        # 6. Look for framework/library patterns
        framework_patterns = [
            r'\b(react|angular|vue)(?:\s+js)?\b',
            r'\b(express|django|flask|spring)(?:\s+boot)?\b',
            r'\b(tensor|keras|pytorch|scikit)[\s\-]?(?:flow|learn)?\b',
        ]
        
        for pattern in framework_patterns:
            try:
                for match in re.finditer(pattern, text_lower):
                    skill = match.group(0).strip()
                    if self._is_valid_skill(skill):
                        technical_skills.add(skill)
            except Exception:
                continue
        
        cleaned_skills = sorted(list(technical_skills))
        
        print(f"\n✅ FINAL: Extracted {len(cleaned_skills)} technical skills")
        print(f"   Skills preview: {cleaned_skills[:15]}")
        if len(cleaned_skills) > 15:
            print(f"   ... and {len(cleaned_skills) - 15} more")
        
        return {
            'technical': cleaned_skills,
            'soft': []
        }
    
    def _is_valid_skill(self, skill: str) -> bool:
        """Check if a string is a valid technical skill"""
        try:
            skill = skill.lower().strip()
            skill = re.sub(r'^(proficient\s+in|experience\s+with|knowledge\s+of)\s+', '', skill)
            skill = skill.strip()
            
            if len(skill) < 2 or len(skill) > 35:
                return False
            
            if skill in NOISE_WORDS:
                return False
            
            if skill in KNOWN_TECHNICAL_SKILLS:
                return True
            
            for known_skill in KNOWN_TECHNICAL_SKILLS:
                if len(skill) >= 3 and len(known_skill) >= 3:
                    if skill == known_skill or \
                       (len(skill) > 4 and skill in known_skill) or \
                       (len(known_skill) > 4 and known_skill in skill):
                        return True
            
            if not any(c.isalnum() for c in skill):
                return False
            
            if skill.isdigit():
                return False
            
            words = skill.split()
            if len(words) > 0 and all(w in NOISE_WORDS for w in words):
                return False
            
            technical_indicators = [
                r'[a-z]+\+\+', r'[a-z]+#', r'[a-z]+\.js', r'[a-z]+sql',
                r'[a-z]+db', r'[a-z]+ml', r'(?:^|\s)js(?:$|\s)',
                r'(?:^|\s)ai(?:$|\s)', r'(?:^|\s)ml(?:$|\s)',
            ]
            
            for pattern in technical_indicators:
                if re.search(pattern, skill):
                    return True
            
            if len(words) >= 2:
                for word in words:
                    if word in KNOWN_TECHNICAL_SKILLS:
                        return True
            
            return False
            
        except Exception:
            return False
    
    def _normalize_skill(self, skill: str) -> str:
        """Normalize skill using aliases"""
        skill = skill.lower().strip()
        
        for main_skill, aliases in SKILL_ALIASES.items():
            if skill in aliases or skill == main_skill:
                return main_skill
        
        return skill

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
        """Parse a single resume and extract information"""
        pdf_path = self.resume_dir / file_name
        if not pdf_path.exists():
            return {"error": f"File not found: {file_name}"}

        text = self._extract_text_from_pdf(pdf_path)
        if not text:
            return {"error": f"Could not extract text from {file_name}"}
            
        print(f"\nProcessing resume: {file_name}")
        print("Extracted text length:", len(text))

        skills_dict = self._extract_skills(text)
        
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
        """Parse all PDF resumes in the specified directory"""
        results = []
        for pdf_file in self.resume_dir.glob('*.pdf'):
            result = self.parse_resume(pdf_file.name)
            results.append(result)
        return results


def parse_resume_file(file_path: str) -> Dict:
    """Standalone function to parse a single resume file"""
    resume_dir = str(Path(file_path).parent)
    parser = ResumeParser(resume_dir)
    return parser.parse_resume(Path(file_path).name)


if __name__ == "__main__":
    resume_folder = r"D:\Desktop\Mustafa\7th SEM\PBL\resumes"
    
    if os.path.exists(resume_folder):
        parser = ResumeParser(resume_folder)
        all_resumes = parser.parse_resumes()
        print(f"\nProcessed {len(all_resumes)} resumes:")
        for resume in all_resumes:
            if "error" in resume:
                print(f"Error: {resume.get('file_name', 'unknown')}: {resume['error']}")
            else:
                print(f"\nFile: {resume['file_name']}")
                print(f"Name: {resume.get('name')}")
                print(f"Technical Skills: {len(resume.get('technical_skills', []))} skills")