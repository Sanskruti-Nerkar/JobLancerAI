import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize
import pandas as pd
from typing import List, Dict, Tuple


class JobMatcher:
    """
    A class to match job descriptions with resume content using TF-IDF and cosine similarity.
    """
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.95
        )
        self.job_vectors = None
        self.resume_vector = None
        
    def preprocess_text(self, text: str) -> str:
        """
        Clean and preprocess text by removing special characters, 
        converting to lowercase, and removing extra whitespace.
        """
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters but keep spaces and basic punctuation
        text = re.sub(r'[^a-zA-Z0-9\s\.\,\!\?]', ' ', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def extract_skills(self, text: str) -> List[str]:
        """
        Extract potential skills from text using common programming/technical keywords.
        """
        # Common technical skills and keywords
        skill_keywords = [
            'python', 'java', 'javascript', 'react', 'angular', 'vue', 'node.js',
            'sql', 'mongodb', 'postgresql', 'mysql', 'aws', 'azure', 'docker',
            'kubernetes', 'git', 'jenkins', 'agile', 'scrum', 'machine learning',
            'ai', 'data science', 'pandas', 'numpy', 'tensorflow', 'pytorch',
            'flask', 'django', 'fastapi', 'selenium', 'beautifulsoup', 'scrapy',
            'html', 'css', 'bootstrap', 'jquery', 'typescript', 'php', 'c++',
            'c#', 'go', 'rust', 'swift', 'kotlin', 'scala', 'r', 'matlab',
            'tableau', 'powerbi', 'excel', 'word', 'powerpoint', 'photoshop',
            'illustrator', 'figma', 'sketch', 'invision', 'zeplin'
        ]
        
        text_lower = text.lower()
        found_skills = []
        
        for skill in skill_keywords:
            if skill in text_lower:
                found_skills.append(skill)
        
        return found_skills
    
    def calculate_experience_match(self, job_description: str, resume_text: str) -> float:
        """
        Calculate experience level match based on keywords and years mentioned.
        """
        # Experience level keywords
        experience_keywords = {
            'entry': ['entry level', 'junior', '0-2 years', 'fresher', 'graduate'],
            'mid': ['mid level', 'intermediate', '2-5 years', 'experienced'],
            'senior': ['senior', 'lead', '5+ years', 'expert', 'principal'],
            'manager': ['manager', 'director', 'head of', 'vp', 'cto']
        }
        
        job_lower = job_description.lower()
        resume_lower = resume_text.lower()
        
        # Find experience level in job description
        job_level = None
        for level, keywords in experience_keywords.items():
            if any(keyword in job_lower for keyword in keywords):
                job_level = level
                break
        
        # Find experience level in resume
        resume_level = None
        for level, keywords in experience_keywords.items():
            if any(keyword in resume_lower for keyword in keywords):
                resume_level = level
                break
        
        # Calculate match score
        if job_level == resume_level:
            return 1.0
        elif job_level and resume_level:
            # Simple scoring based on level proximity
            levels = ['entry', 'mid', 'senior', 'manager']
            job_idx = levels.index(job_level)
            resume_idx = levels.index(resume_level)
            distance = abs(job_idx - resume_idx)
            return max(0.0, 1.0 - (distance * 0.3))
        
        return 0.5  # Default score if no clear level found
    
    def calculate_location_match(self, job_location: str, resume_location: str) -> float:
        """
        Calculate location match score.
        """
        if not job_location or not resume_location:
            return 0.5
        
        job_loc = job_location.lower().strip()
        resume_loc = resume_location.lower().strip()
        
        # Exact match
        if job_loc == resume_loc:
            return 1.0
        
        # Partial match (e.g., "Bangalore" vs "Bengaluru")
        if job_loc in resume_loc or resume_loc in job_loc:
            return 0.8
        
        # Check for common city variations
        city_variations = {
            'bangalore': ['bengaluru', 'blore'],
            'mumbai': ['bombay'],
            'kolkata': ['calcutta'],
            'chennai': ['madras'],
            'delhi': ['new delhi', 'ncr']
        }
        
        for city, variations in city_variations.items():
            if (job_loc in [city] + variations and 
                resume_loc in [city] + variations):
                return 0.9
        
        return 0.0
    
    def extract_resume_location(self, resume_text: str) -> str:
        """Extract location from resume text"""
        location_patterns = [
            r'location\s*:\s*([^,\n]+)',
            r'address\s*:\s*([^,\n]+)',
            r'based\s+in\s+([^,\n]+)',
            r'residing\s+in\s+([^,\n]+)',
            r'from\s+([^,\n]+)'
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, resume_text.lower())
            if match:
                return match.group(1).strip()
        return ""
    
    def extract_resume_experience(self, resume_text: str) -> int:
        """Extract years of experience from resume"""
        experience_patterns = [
            r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|work)',
            r'(?:experience|work)\s*(?:of\s+)?(\d+)\+?\s*(?:years?|yrs?)',
            r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:in|of)'
        ]
        
        max_years = 0
        for pattern in experience_patterns:
            matches = re.finditer(pattern, resume_text.lower())
            for match in matches:
                try:
                    years = int(match.group(1))
                    max_years = max(max_years, years)
                except:
                    continue
        return max_years
    
    def calculate_experience_match_advanced(self, job_description: str, resume_text: str, resume_experience: int) -> float:
        """Advanced experience matching with more nuanced scoring"""
        # Extract experience requirements from job
        job_experience_patterns = [
            r'(\d+)[-+]?\s*(?:to\s*)?(\d+)?\s*(?:years?|yrs?)',
            r'(?:minimum|min|at\s*least)\s*(\d+)\s*(?:years?|yrs?)',
            r'(\d+)\+\s*(?:years?|yrs?)',
            r'fresher|entry\s*level|0-2\s*years?',
            r'2-5\s*years?|mid\s*level',
            r'5\+\s*years?|senior|lead'
        ]
        
        job_min_exp = 0
        job_max_exp = 10
        
        for pattern in job_experience_patterns:
            match = re.search(pattern, job_description.lower())
            if match:
                if 'fresher' in pattern or 'entry' in pattern:
                    job_min_exp, job_max_exp = 0, 2
                elif '2-5' in pattern or 'mid' in pattern:
                    job_min_exp, job_max_exp = 2, 5
                elif '5+' in pattern or 'senior' in pattern or 'lead' in pattern:
                    job_min_exp, job_max_exp = 5, 15
                else:
                    try:
                        if match.group(2):  # Range like "3-5 years"
                            job_min_exp = int(match.group(1))
                            job_max_exp = int(match.group(2))
                        else:  # Single number
                            job_min_exp = int(match.group(1))
                            job_max_exp = job_min_exp + 2
                    except:
                        continue
                break
        
        # Calculate match score
        if resume_experience >= job_min_exp and resume_experience <= job_max_exp:
            return 1.0  # Perfect match
        elif resume_experience < job_min_exp:
            # Underqualified - score based on how close they are
            gap = job_min_exp - resume_experience
            return max(0.0, 1.0 - (gap * 0.2))
        else:
            # Overqualified - still good but not perfect
            gap = resume_experience - job_max_exp
            return max(0.3, 1.0 - (gap * 0.1))
    
    def calculate_skills_match_advanced(self, job_skills: List[str], resume_skills: List[str]) -> Dict:
        """Advanced skills matching with detailed analysis"""
        if not job_skills:
            return {
                'overall_score': 1.0,
                'matched_skills': [],
                'missing_skills': [],
                'match_percentage': 100.0
            }
        
        # Normalize skills
        job_skills_set = {skill.lower().strip() for skill in job_skills}
        resume_skills_set = {skill.lower().strip() for skill in resume_skills}
        
        # Find exact matches
        exact_matches = job_skills_set & resume_skills_set
        
        # Find partial matches (e.g., "python" matches "python developer")
        partial_matches = set()
        missing_skills = job_skills_set - exact_matches
        
        for job_skill in missing_skills.copy():
            for resume_skill in resume_skills_set:
                if (job_skill in resume_skill or resume_skill in job_skill) and len(job_skill) > 2:
                    partial_matches.add(job_skill)
                    missing_skills.remove(job_skill)
                    break
        
        # Calculate scores
        total_matches = len(exact_matches) + len(partial_matches)
        match_percentage = (total_matches / len(job_skills_set)) * 100
        
        # Weight exact matches higher than partial matches
        overall_score = (len(exact_matches) * 1.0 + len(partial_matches) * 0.7) / len(job_skills_set)
        
        return {
            'overall_score': min(1.0, overall_score),
            'matched_skills': list(exact_matches | partial_matches),
            'missing_skills': list(missing_skills),
            'match_percentage': match_percentage
        }
    
    def calculate_title_relevance(self, job_title: str, resume_text: str) -> float:
        """Calculate how relevant the job title is to the resume content"""
        if not job_title:
            return 0.0
        
        # Extract key terms from job title
        title_terms = set(job_title.lower().split())
        
        # Remove common words
        common_words = {'developer', 'engineer', 'analyst', 'manager', 'specialist', 'consultant', 'lead', 'senior', 'junior'}
        title_terms = title_terms - common_words
        
        if not title_terms:
            return 0.5  # Default score if no meaningful terms
        
        # Count how many title terms appear in resume
        resume_lower = resume_text.lower()
        matches = sum(1 for term in title_terms if term in resume_lower)
        
        return matches / len(title_terms)
    
    def scale_score_realistically(self, raw_score: float, skills_analysis: Dict) -> float:
        """Scale scores to be more realistic (most jobs should score 20-80%)"""
        # Base scaling
        scaled_score = raw_score * 0.8 + 0.1  # Scale to 10-90% range
        
        # Adjust based on skills match
        skill_percentage = skills_analysis.get('match_percentage', 0)
        
        if skill_percentage < 30:
            # Very low skill match - cap the score
            scaled_score = min(scaled_score, 0.4)
        elif skill_percentage > 80:
            # Very high skill match - boost the score
            scaled_score = min(0.95, scaled_score * 1.1)
        
        # Ensure score is within realistic bounds
        return max(0.05, min(0.95, scaled_score))
    
    def fit_transform(self, jobs: List[Dict], resume_text: str) -> None:
        """
        Fit the vectorizer on job descriptions and transform both jobs and resume.
        Updated to include key_skills from separate section.
        """
        # Preprocess all texts
        job_descriptions = []
        for job in jobs:
            # Combine title, company, summary, and key_skills for better matching
            key_skills_text = ' '.join(job.get('key_skills', []))
            job_text = f"{job.get('title', '')} {job.get('company', '')} {job.get('summary', '')} {key_skills_text}"
            job_descriptions.append(self.preprocess_text(job_text))
        
        resume_processed = self.preprocess_text(resume_text)
        
        # Fit and transform job descriptions
        self.job_vectors = self.vectorizer.fit_transform(job_descriptions)
        
        # Transform resume
        self.resume_vector = self.vectorizer.transform([resume_processed])
    
    def calculate_similarity_scores(self, jobs: List[Dict], resume_text: str) -> List[Dict]:
        """
        Calculate comprehensive and accurate similarity scores for all jobs.
        """
        if not jobs:
            return []
        
        # Fit and transform the data
        self.fit_transform(jobs, resume_text)
        
        # Calculate cosine similarity
        similarities = cosine_similarity(self.resume_vector, self.job_vectors).flatten()
        
        # Extract resume information for better matching
        resume_skills = self.extract_skills(resume_text)
        resume_location = self.extract_resume_location(resume_text)
        resume_experience = self.extract_resume_experience(resume_text)
        
        # Calculate additional matching scores
        results = []
        for i, job in enumerate(jobs):
            # Basic similarity score (normalize to 0-1 range)
            similarity_score = max(0.0, min(1.0, float(similarities[i])))
            
            # Experience match with more sophisticated logic
            key_skills_text = ' '.join(job.get('key_skills', []))
            job_text = f"{job.get('title', '')} {job.get('company', '')} {job.get('summary', '')} {key_skills_text}"
            experience_score = self.calculate_experience_match_advanced(job_text, resume_text, resume_experience)
            
            # Location match with resume location
            location_score = self.calculate_location_match(job.get('location', ''), resume_location)
            
            # Skills match with more detailed analysis - prioritize key_skills if available
            if job.get('key_skills'):
                # Use the separate key_skills section if available
                job_skills = job['key_skills']
            else:
                # Fallback to extracting skills from text
                job_skills = self.extract_skills(job_text)
            
            skills_analysis = self.calculate_skills_match_advanced(job_skills, resume_skills)
            skills_score = skills_analysis['overall_score']
            
            # Job title relevance (how well the job title matches resume content)
            title_relevance = self.calculate_title_relevance(job.get('title', ''), resume_text)
            
            # Calculate weighted final score with more realistic weights
            final_score = (
                similarity_score * 0.25 +     # Content similarity (reduced weight)
                experience_score * 0.25 +     # Experience level
                location_score * 0.15 +       # Location (reduced weight)
                skills_score * 0.30 +         # Skills match (increased weight)
                title_relevance * 0.05        # Job title relevance
            )
            
            # Apply realistic score scaling (most jobs should score 20-80%)
            final_score = self.scale_score_realistically(final_score, skills_analysis)
            
            # Create result dictionary with detailed breakdown
            result = {
                'job': job,
                'similarity_score': round(similarity_score, 3),
                'experience_score': round(experience_score, 3),
                'location_score': round(location_score, 3),
                'skills_score': round(skills_score, 3),
                'title_relevance': round(title_relevance, 3),
                'final_score': round(final_score, 3),
                'matched_skills': skills_analysis['matched_skills'],
                'missing_skills': skills_analysis['missing_skills'],
                'skill_match_percentage': skills_analysis['match_percentage']
            }
            
            results.append(result)
        
        return results
    
    def rank_jobs(self, jobs: List[Dict], resume_text: str, 
                  min_score: float = 0.3) -> List[Dict]:
        """
        Rank jobs by match score and filter by minimum score.
        """
        results = self.calculate_similarity_scores(jobs, resume_text)
        
        # Sort by final score (descending)
        results.sort(key=lambda x: x['final_score'], reverse=True)
        
        # Filter by minimum score
        filtered_results = [r for r in results if r['final_score'] >= min_score]
        
        return filtered_results
    
    def get_top_matches(self, jobs: List[Dict], resume_text: str, 
                       top_n: int = 10, min_score: float = 0.3) -> List[Dict]:
        """
        Get top N job matches above minimum score.
        """
        ranked_jobs = self.rank_jobs(jobs, resume_text, min_score)
        return ranked_jobs[:top_n]


def match_jobs_with_resume(jobs: List[Dict], resume_text: str, 
                          top_n: int = 10, min_score: float = 0.3) -> List[Dict]:
    """
    Convenience function to match jobs with resume and return top matches.
    """
    matcher = JobMatcher()
    return matcher.get_top_matches(jobs, resume_text, top_n, min_score)


# Example usage and testing
if __name__ == "__main__":
    # Sample jobs (from your scraper)
    sample_jobs = [
        {
            'title': 'Python Developer',
            'company': 'Tech Corp',
            'location': 'Bangalore',
            'summary': 'We are looking for a Python developer with experience in Django, Flask, and SQL.'
        },
        {
            'title': 'Frontend Developer',
            'company': 'Web Solutions',
            'location': 'Mumbai',
            'summary': 'React, JavaScript, HTML, CSS developer needed for frontend development.'
        },
        {
            'title': 'Data Scientist',
            'company': 'AI Labs',
            'location': 'Delhi',
            'summary': 'Machine learning, Python, pandas, numpy, scikit-learn experience required.'
        }
    ]
    
    # Sample resume text
    sample_resume = """
    Experienced Python developer with 3 years of experience in web development.
    Skills: Python, Django, Flask, SQL, JavaScript, React, HTML, CSS.
    Worked on machine learning projects using pandas, numpy, and scikit-learn.
    Location: Bangalore, India.
    """
    
    # Test the matcher
    matcher = JobMatcher()
    top_matches = matcher.get_top_matches(sample_jobs, sample_resume, top_n=3)
    
    print("Top Job Matches:")
    for i, match in enumerate(top_matches, 1):
        print(f"\n{i}. {match['job']['title']} at {match['job']['company']}")
        print(f"   Final Score: {match['final_score']}")
        print(f"   Similarity: {match['similarity_score']}")
        print(f"   Experience: {match['experience_score']}")
        print(f"   Skills: {match['skills_score']}")
        print(f"   Matched Skills: {', '.join(match['matched_skills'])}") 