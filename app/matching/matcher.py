import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict


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
        
        # REMOVED CACHING - This was causing same scores!
        # Caching meant same vectors were reused even for different resumes

    def preprocess_text(self, text: str) -> str:
        """Clean and preprocess text"""
        if not text:
            return ""
        text = text.lower()
        text = re.sub(r'[^a-zA-Z0-9\s\.\,\!\?]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def extract_skills(self, text: str, key_skills: List[str] = None) -> List[str]:
        """
        Extract skills from text or use provided key_skills.
        Prioritizes explicit key_skills from scraper.
        """
        # If explicit key_skills provided, use them
        if key_skills and len(key_skills) > 0:
            cleaned = []
            for s in key_skills:
                if isinstance(s, str) and len(s.strip()) > 1:
                    cleaned.append(s.lower().strip())
            return cleaned
        
        # Fallback: Extract from text
        skill_keywords = [
            'python', 'java', 'javascript', 'react', 'angular', 'vue', 'node.js', 'nodejs',
            'sql', 'mongodb', 'postgresql', 'mysql', 'aws', 'azure', 'docker', 'kubernetes',
            'git', 'jenkins', 'agile', 'scrum', 'machine learning', 'ai', 'data science',
            'pandas', 'numpy', 'tensorflow', 'pytorch', 'flask', 'django', 'fastapi',
            'selenium', 'beautifulsoup', 'scrapy', 'html', 'css', 'bootstrap', 'jquery',
            'typescript', 'php', 'c++', 'c#', 'go', 'rust', 'swift', 'kotlin', 'scala',
            'r', 'matlab', 'tableau', 'powerbi', 'power bi', 'excel', 'spss', 'sas',
            'hadoop', 'spark', 'kafka', 'elasticsearch', 'redis', 'api', 'rest', 'graphql',
            'linux', 'unix', 'windows', 'bash', 'shell', 'devops', 'ci/cd', 'terraform'
        ]
        
        text_lower = text.lower()
        found_skills = set()
        
        for skill in skill_keywords:
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, text_lower):
                found_skills.add(skill)
        
        return list(found_skills)
    
    def calculate_experience_match_advanced(self, job_text: str, resume_text: str, resume_experience: int) -> float:
        """Advanced experience matching"""
        job_experience_patterns = [
            (r'(\d+)[-+]?\s*(?:to\s*)?(\d+)?\s*(?:years?|yrs?)', 'range'),
            (r'(?:minimum|min|at\s*least)\s*(\d+)\s*(?:years?|yrs?)', 'minimum'),
            (r'(\d+)\+\s*(?:years?|yrs?)', 'plus'),
            (r'fresher|entry\s*level|0[-\s]2\s*years?', 'entry'),
            (r'2[-\s]5\s*years?|mid\s*level', 'mid'),
            (r'5\+\s*years?|senior|lead', 'senior')
        ]
        
        job_min_exp = 0
        job_max_exp = 10
        
        for pattern, type_ in job_experience_patterns:
            match = re.search(pattern, job_text.lower())
            if match:
                if type_ == 'entry':
                    job_min_exp, job_max_exp = 0, 2
                elif type_ == 'mid':
                    job_min_exp, job_max_exp = 2, 5
                elif type_ == 'senior':
                    job_min_exp, job_max_exp = 5, 15
                elif type_ == 'range' and match.group(2):
                    job_min_exp = int(match.group(1))
                    job_max_exp = int(match.group(2))
                elif type_ == 'minimum' or type_ == 'plus':
                    job_min_exp = int(match.group(1))
                    job_max_exp = job_min_exp + 5
                break
        
        # Calculate match score
        if job_min_exp <= resume_experience <= job_max_exp:
            return 1.0
        elif resume_experience < job_min_exp:
            gap = job_min_exp - resume_experience
            return max(0.0, 1.0 - (gap * 0.15))
        else:
            gap = resume_experience - job_max_exp
            return max(0.5, 1.0 - (gap * 0.08))
    
    def calculate_location_match(self, job_location: str, resume_location: str) -> float:
        """Calculate location match score"""
        if not job_location or not resume_location:
            return 0.5
        
        job_loc = job_location.lower().strip()
        resume_loc = resume_location.lower().strip()
        
        if job_loc == resume_loc:
            return 1.0
        if job_loc in resume_loc or resume_loc in job_loc:
            return 0.8
        
        # Handle remote
        if 'remote' in job_loc or 'remote' in resume_loc:
            return 0.7
        
        city_variations = {
            'bangalore': ['bengaluru', 'blore'],
            'mumbai': ['bombay'],
            'kolkata': ['calcutta'],
            'chennai': ['madras'],
            'delhi': ['new delhi', 'ncr']
        }
        
        for city, variations in city_variations.items():
            if (job_loc in [city] + variations and resume_loc in [city] + variations):
                return 0.9
        
        return 0.0
    
    def extract_resume_location(self, resume_text: str) -> str:
        """Extract location from resume"""
        location_patterns = [
            r'location\s*:\s*([^,\n]+)',
            r'address\s*:\s*([^,\n]+)',
            r'based\s+in\s+([^,\n]+)',
            r'residing\s+in\s+([^,\n]+)'
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
    
    def calculate_skills_match_advanced(self, job_skills: List[str], resume_skills: List[str]) -> Dict:
        """
        Advanced skills matching with detailed analysis.
        FIXED: Properly handles empty skill lists.
        """
        # CRITICAL FIX: Return 0 score if no job skills
        if not job_skills or len(job_skills) == 0:
            return {
                'overall_score': 0.0,
                'matched_skills': [],
                'missing_skills': [],
                'match_percentage': 0.0
            }
        
        # Normalize skills - remove empty strings
        job_skills_set = {skill.lower().strip() for skill in job_skills if skill and len(skill.strip()) > 0}
        resume_skills_set = {skill.lower().strip() for skill in resume_skills if skill and len(skill.strip()) > 0}
        
        if not job_skills_set:
            return {
                'overall_score': 0.0,
                'matched_skills': [],
                'missing_skills': [],
                'match_percentage': 0.0
            }
        
        # Find exact matches
        exact_matches = job_skills_set & resume_skills_set
        
        # Find partial matches
        partial_matches = set()
        missing_skills = job_skills_set - exact_matches
        
        for job_skill in list(missing_skills):
            for resume_skill in resume_skills_set:
                # Match if one contains the other and both are meaningful
                if len(job_skill) > 2 and len(resume_skill) > 2:
                    if job_skill in resume_skill or resume_skill in job_skill:
                        partial_matches.add(job_skill)
                        missing_skills.discard(job_skill)
                        break
        
        # Calculate scores
        total_matches = len(exact_matches) + len(partial_matches)
        match_percentage = (total_matches / len(job_skills_set)) * 100
        
        # Weight exact matches higher than partial
        overall_score = (len(exact_matches) * 1.0 + len(partial_matches) * 0.7) / len(job_skills_set)
        overall_score = min(1.0, overall_score)
        
        return {
            'overall_score': overall_score,
            'matched_skills': list(exact_matches | partial_matches),
            'missing_skills': list(missing_skills),
            'match_percentage': match_percentage
        }
    
    def calculate_title_relevance(self, job_title: str, resume_text: str) -> float:
        """Calculate how relevant the job title is to resume"""
        if not job_title:
            return 0.0
        
        # Extract key terms from job title
        title_terms = set(job_title.lower().split())
        
        # Remove common words
        common_words = {'developer', 'engineer', 'analyst', 'manager', 'specialist', 
                       'consultant', 'lead', 'senior', 'junior', 'associate', 'entry'}
        title_terms = title_terms - common_words
        
        if not title_terms:
            return 0.5
        
        # Count matches in resume
        resume_lower = resume_text.lower()
        matches = sum(1 for term in title_terms if term in resume_lower and len(term) > 2)
        
        return min(1.0, matches / len(title_terms))
    
    def scale_score_realistically(self, raw_score: float, skills_analysis: Dict) -> float:
        """Scale scores to be more realistic (most jobs should score 20-80%)"""
        # Base scaling to prevent extreme scores
        scaled_score = raw_score * 0.85 + 0.10
        
        # Adjust based on skills match
        skill_percentage = skills_analysis.get('match_percentage', 0)
        
        if skill_percentage == 0:
            # No skills matched - cap score low
            scaled_score = min(scaled_score, 0.35)
        elif skill_percentage < 20:
            # Very low skill match
            scaled_score = min(scaled_score, 0.45)
        elif skill_percentage < 40:
            # Low skill match
            scaled_score = min(scaled_score, 0.60)
        elif skill_percentage > 80:
            # Very high skill match - boost
            scaled_score = min(0.92, scaled_score * 1.08)
        
        return max(0.05, min(0.95, scaled_score))
    
    def fit_transform(self, jobs: List[Dict], resume_text: str) -> None:
        """
        Fit vectorizer and transform job and resume texts
        FIXED: Removed caching that caused same scores
        """
        # ALWAYS rebuild vectors - no caching!
        job_descriptions: List[str] = []
        
        for job in jobs:
            # Get key skills from scraper
            key_skills = job.get('key_skills', []) or job.get('skills', [])
            
            # Build job text
            title = job.get('title', '')
            company = job.get('company', '')
            summary = job.get('summary', '')
            skills_text = ' '.join(key_skills) if key_skills else ''
            
            job_text = f"{title} {company} {summary} {skills_text}"
            job_descriptions.append(self.preprocess_text(job_text))

        resume_processed = self.preprocess_text(resume_text)

        # CRITICAL: Always fit_transform fresh
        # This ensures each resume gets unique vectorization
        all_texts = job_descriptions + [resume_processed]
        
        # Fit on all texts together for consistent vocabulary
        vectors = self.vectorizer.fit_transform(all_texts)
        
        # Split back into jobs and resume
        self.job_vectors = vectors[:-1]  # All except last
        self.resume_vector = vectors[-1:]  # Just the last one
    
    def calculate_similarity_scores(self, jobs: List[Dict], resume_text: str, 
                                   resume_skills_external: List[str] = None) -> List[Dict]:
        """Calculate comprehensive similarity scores for all jobs"""
        if not jobs:
            return []
        
        # ALWAYS fit and transform (no caching)
        self.fit_transform(jobs, resume_text)
        
        # Calculate cosine similarity
        similarities = cosine_similarity(self.resume_vector, self.job_vectors).flatten()
        
        print(f"\n🔍 Debug: Similarity scores range: {similarities.min():.3f} to {similarities.max():.3f}")
        
        # Extract resume information
        if resume_skills_external is not None:
            resume_skills = [s.lower().strip() for s in resume_skills_external if isinstance(s, str)]
        else:
            resume_skills = self.extract_skills(resume_text)
        
        print(f"📊 Resume has {len(resume_skills)} skills: {resume_skills[:5]}")
        
        resume_location = self.extract_resume_location(resume_text)
        resume_experience = self.extract_resume_experience(resume_text)
        
        print(f"📍 Resume location: {resume_location}, Experience: {resume_experience} years")
        
        # Calculate scores for each job
        results = []
        for i, job in enumerate(jobs):
            # Basic similarity score
            similarity_score = max(0.0, min(1.0, float(similarities[i])))
            
            # Build job text for experience matching
            job_text = f"{job.get('title', '')} {job.get('summary', '')}"
            experience_score = self.calculate_experience_match_advanced(
                job_text, resume_text, resume_experience
            )
            
            # Location match
            location_score = self.calculate_location_match(
                job.get('location', ''), resume_location
            )
            
            # Skills match - extract fresh for each job
            job_skills = self.extract_skills(job_text, job.get('key_skills', []))
            
            skills_analysis = self.calculate_skills_match_advanced(job_skills, resume_skills)
            skills_score = skills_analysis['overall_score']
            
            # Job title relevance
            title_relevance = self.calculate_title_relevance(
                job.get('title', ''), resume_text
            )
            
            # Calculate weighted final score with MORE VARIANCE
            final_score = (
                similarity_score * 0.30 +    # Text similarity
                experience_score * 0.20 +    # Experience match
                location_score * 0.10 +      # Location match
                skills_score * 0.35 +        # Skills match (weighted heavily)
                title_relevance * 0.05       # Title relevance
            )
            
            # Apply realistic scaling
            final_score = self.scale_score_realistically(final_score, skills_analysis)
            
            # Debug output for first few jobs
            if i < 3:
                print(f"\n  Job {i+1}: {job.get('title', 'Unknown')[:40]}")
                print(f"    Skills: {len(job_skills)} found")
                print(f"    Similarity: {similarity_score:.3f}, Skills: {skills_score:.3f}, Final: {final_score:.3f}")
            
            # Build result
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
                'skill_match_percentage': round(skills_analysis['match_percentage'], 1)
            }
            
            results.append(result)
        
        print(f"\n✅ Calculated scores for {len(results)} jobs")
        print(f"   Final scores range: {min(r['final_score'] for r in results):.1%} to {max(r['final_score'] for r in results):.1%}")
        
        return results
    
    def rank_jobs(self, jobs: List[Dict], resume_text: str, 
                  min_score: float = 0.3, resume_skills: List[str] = None) -> List[Dict]:
        """Rank jobs by match score and filter by minimum score"""
        results = self.calculate_similarity_scores(jobs, resume_text, resume_skills)
        
        # Sort by final score (descending)
        results.sort(key=lambda x: x['final_score'], reverse=True)
        
        # Filter by minimum score
        filtered_results = [r for r in results if r['final_score'] >= min_score]
        
        return filtered_results
    
    def get_top_matches(self, jobs: List[Dict], resume_text: str, 
                       top_n: int = 10, min_score: float = 0.3, 
                       resume_skills: List[str] = None) -> List[Dict]:
        """Get top N job matches above minimum score"""
        ranked_jobs = self.rank_jobs(jobs, resume_text, min_score, resume_skills=resume_skills)
        return ranked_jobs[:top_n]


def match_jobs_with_resume(jobs: List[Dict], resume_text: str, 
                          top_n: int = 10, min_score: float = 0.3) -> List[Dict]:
    """Convenience function to match jobs with resume"""
    matcher = JobMatcher()
    return matcher.get_top_matches(jobs, resume_text, top_n, min_score)