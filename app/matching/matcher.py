import re
import os
import sys
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict

# FIXED: Import job_description_parser from parsers folder
HAVE_JD_PARSER = False

# Try multiple import strategies
try:
    # Strategy 1: Import from parsers module (correct location)
    from parsers.job_description_parser import extract_skills_from_jd
    HAVE_JD_PARSER = True
except ImportError:
    try:
        # Strategy 2: Relative import from parent
        from ..parsers.job_description_parser import extract_skills_from_jd
        HAVE_JD_PARSER = True
        print("✅ Job description parser imported (relative from parsers)")
    except (ImportError, ValueError):
        try:
            # Strategy 3: Add paths and try direct import
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            parsers_dir = os.path.join(parent_dir, 'parsers')
            
            for path in [current_dir, parent_dir, parsers_dir]:
                if path not in sys.path:
                    sys.path.insert(0, path)
            
            from job_description_parser import extract_skills_from_jd
            HAVE_JD_PARSER = True
            print("✅ Job description parser imported (path manipulation from parsers)")
        except ImportError as e:
            print(f"⚠️ job_description_parser not found in parsers/ - using fallback")
            print(f"   Error: {e}")
            HAVE_JD_PARSER = False


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
        print(f"🔧 JobMatcher initialized | JD Parser: {'✅ Available' if HAVE_JD_PARSER else '⚠️ Fallback mode'}")

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
        Uses IMPROVED JD PARSER when available.
        """
        print(f"\n🔍 Extracting skills...")
        print(f"   - Parser available: {HAVE_JD_PARSER}")
        print(f"   - Key skills provided: {len(key_skills) if key_skills else 0}")
        
        all_skills = set()
        
        # Priority 1: If explicit key_skills provided from scraper, use them
        if key_skills and len(key_skills) > 0:
            cleaned = []
            for s in key_skills:
                if isinstance(s, str) and len(s.strip()) > 1:
                    cleaned.append(s.lower().strip())
            all_skills.update(cleaned)
            print(f"   ✅ Added {len(cleaned)} skills from key_skills")
        
        # Priority 2: Use JD parser if available (MOST IMPORTANT)
        if HAVE_JD_PARSER and text:
            try:
                print(f"   🚀 Running JD parser on text ({len(text)} chars)...")
                parsed_skills = extract_skills_from_jd(text)
                all_skills.update(parsed_skills)
                print(f"   ✅ JD parser extracted {len(parsed_skills)} skills")
            except Exception as e:
                print(f"   ⚠️ JD parser error: {e}")
        
        # Priority 3: Fallback to basic extraction if no skills found yet
        if len(all_skills) == 0:
            print(f"   ⚠️ No skills found, using fallback extraction")
            all_skills.update(self._fallback_extract_skills(text))
        
        result = list(all_skills)
        print(f"   📊 Final: {len(result)} unique skills extracted")
        if result:
            print(f"   Sample: {result[:5]}")
        
        return result
    
    def _fallback_extract_skills(self, text: str) -> List[str]:
        """Fallback skill extraction when JD parser is not available"""
        if not text:
            return []
        
        skill_keywords = [
            'python', 'java', 'javascript', 'react', 'angular', 'vue', 'node.js', 'nodejs',
            'sql', 'mongodb', 'postgresql', 'mysql', 'aws', 'azure', 'docker', 'kubernetes',
            'git', 'jenkins', 'agile', 'scrum', 'machine learning', 'ai', 'data science',
            'pandas', 'numpy', 'tensorflow', 'pytorch', 'flask', 'django', 'fastapi',
            'selenium', 'beautifulsoup', 'scrapy', 'html', 'css', 'bootstrap', 'jquery',
            'typescript', 'php', 'c++', 'c#', 'go', 'rust', 'swift', 'kotlin', 'scala',
            'r', 'matlab', 'tableau', 'powerbi', 'power bi', 'excel', 'spss', 'sas',
            'hadoop', 'spark', 'kafka', 'elasticsearch', 'redis', 'api', 'rest', 'graphql',
            'linux', 'unix', 'windows', 'bash', 'shell', 'devops', 'ci/cd', 'terraform',
            'html5', 'ajax', 'razorpay', 'paypal', 'htaccess', 'json', 'soap'
        ]
        
        text_lower = text.lower()
        found_skills = set()
        
        for skill in skill_keywords:
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
        """
        # Return 0 score if no job skills
        if not job_skills or len(job_skills) == 0:
            print(f"      ⚠️ No job skills to match against")
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
            print(f"      ⚠️ No valid job skills after normalization")
            return {
                'overall_score': 0.0,
                'matched_skills': [],
                'missing_skills': [],
                'match_percentage': 0.0
            }
        
        # Find exact matches
        exact_matches = job_skills_set & resume_skills_set
        
        # Find partial matches (e.g., "node.js" matches "nodejs")
        partial_matches = set()
        missing_skills = job_skills_set - exact_matches
        
        for job_skill in list(missing_skills):
            for resume_skill in resume_skills_set:
                if len(job_skill) > 2 and len(resume_skill) > 2:
                    # Handle variations like "node.js" vs "nodejs"
                    job_skill_clean = job_skill.replace('.', '').replace('-', '').replace(' ', '')
                    resume_skill_clean = resume_skill.replace('.', '').replace('-', '').replace(' ', '')
                    
                    if job_skill_clean == resume_skill_clean or \
                       job_skill in resume_skill or resume_skill in job_skill:
                        partial_matches.add(job_skill)
                        missing_skills.discard(job_skill)
                        break
        
        # Calculate scores
        total_matches = len(exact_matches) + len(partial_matches)
        match_percentage = (total_matches / len(job_skills_set)) * 100
        
        # Weight exact matches higher than partial
        overall_score = (len(exact_matches) * 1.0 + len(partial_matches) * 0.7) / len(job_skills_set)
        overall_score = min(1.0, overall_score)
        
        print(f"      📊 Skills Match: {total_matches}/{len(job_skills_set)} ({match_percentage:.0f}%)")
        
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
            scaled_score = min(scaled_score, 0.35)
        elif skill_percentage < 20:
            scaled_score = min(scaled_score, 0.45)
        elif skill_percentage < 40:
            scaled_score = min(scaled_score, 0.60)
        elif skill_percentage > 80:
            scaled_score = min(0.92, scaled_score * 1.08)
        
        return max(0.05, min(0.95, scaled_score))
    
    def fit_transform(self, jobs: List[Dict], resume_text: str) -> None:
        """Fit vectorizer and transform job and resume texts"""
        job_descriptions: List[str] = []
        
        for job in jobs:
            # Get key skills from scraper or summary
            key_skills = job.get('key_skills', []) or job.get('skills', [])
            
            # Build job text
            title = job.get('title', '')
            company = job.get('company', '')
            summary = job.get('summary', '')
            skills_text = ' '.join(key_skills) if key_skills else ''
            
            job_text = f"{title} {company} {summary} {skills_text}"
            job_descriptions.append(self.preprocess_text(job_text))

        resume_processed = self.preprocess_text(resume_text)

        # Always fit_transform fresh
        all_texts = job_descriptions + [resume_processed]
        
        # Fit on all texts together for consistent vocabulary
        vectors = self.vectorizer.fit_transform(all_texts)
        
        # Split back into jobs and resume
        self.job_vectors = vectors[:-1]
        self.resume_vector = vectors[-1:]
    
    def calculate_similarity_scores(self, jobs: List[Dict], resume_text: str, 
                                   resume_skills_external: List[str] = None) -> List[Dict]:
        """Calculate comprehensive similarity scores for all jobs"""
        if not jobs:
            return []
        
        print(f"\n{'='*70}")
        print(f"🎯 MATCHING {len(jobs)} JOBS WITH RESUME")
        print(f"{'='*70}")
        
        # Always fit and transform
        self.fit_transform(jobs, resume_text)
        
        # Calculate cosine similarity
        similarities = cosine_similarity(self.resume_vector, self.job_vectors).flatten()
        
        print(f"\n📊 Similarity Analysis:")
        print(f"   Range: {similarities.min():.3f} to {similarities.max():.3f}")
        
        # Extract resume information
        if resume_skills_external is not None:
            resume_skills = [s.lower().strip() for s in resume_skills_external if isinstance(s, str)]
        else:
            resume_skills = self.extract_skills(resume_text)
        
        print(f"   Resume skills: {len(resume_skills)}")
        if resume_skills:
            print(f"   Sample: {resume_skills[:5]}")
        
        resume_location = self.extract_resume_location(resume_text)
        resume_experience = self.extract_resume_experience(resume_text)
        
        # Calculate scores for each job
        results = []
        for i, job in enumerate(jobs):
            print(f"\n{'─'*70}")
            print(f"   Job {i+1}: {job.get('title', 'Unknown')[:50]}")
            print(f"   Company: {job.get('company', 'Unknown')[:40]}")
            
            # Basic similarity score
            similarity_score = max(0.0, min(1.0, float(similarities[i])))
            
            # Build job text for experience matching and skill extraction
            job_title = job.get('title', '')
            job_summary = job.get('summary', '')
            job_text = f"{job_title} {job_summary}"
            
            experience_score = self.calculate_experience_match_advanced(
                job_text, resume_text, resume_experience
            )
            
            # Location match
            location_score = self.calculate_location_match(
                job.get('location', ''), resume_location
            )
            
            # CRITICAL: Extract skills using JD parser
            job_key_skills = job.get('key_skills', [])
            print(f"      Key skills from scraper: {len(job_key_skills)}")
            
            job_skills = self.extract_skills(job_text, job_key_skills)
            print(f"      Total job skills: {len(job_skills)}")
            
            skills_analysis = self.calculate_skills_match_advanced(job_skills, resume_skills)
            skills_score = skills_analysis['overall_score']
            
            # Job title relevance
            title_relevance = self.calculate_title_relevance(job_title, resume_text)
            
            # Calculate weighted final score
            final_score = (
                similarity_score * 0.30 +
                experience_score * 0.20 +
                location_score * 0.10 +
                skills_score * 0.35 +
                title_relevance * 0.05
            )
            
            # Apply realistic scaling
            final_score = self.scale_score_realistically(final_score, skills_analysis)
            
            print(f"      Final Match: {final_score:.1%}")
            
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
        
        print(f"\n{'='*70}")
        print(f"✅ MATCHING COMPLETE")
        if results:
            final_scores = [r['final_score'] for r in results]
            print(f"   Score range: {min(final_scores):.1%} to {max(final_scores):.1%}")
            print(f"   Average: {sum(final_scores)/len(final_scores):.1%}")
        print(f"{'='*70}\n")
        
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