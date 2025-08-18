import re
import pdfplumber


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract all text from a PDF file.
    """
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text


def extract_name(text: str) -> str:
    """
    Very basic name extraction (assumes name is the first line).
    Can be improved with NLP later.
    """
    lines = text.strip().split("\n")
    if lines:
        return lines[0].strip()
    return None


def extract_email(text: str) -> str:
    """
    Extract email address from resume text using regex.
    """
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    return match.group(0) if match else None


def extract_phone(text: str) -> str:
    """
    Extract phone number (10–15 digits).
    """
    match = re.search(r'(\+?\d{1,3}[-.\s]?)?\d{10,15}', text)
    return match.group(0) if match else None


def extract_skills(text: str) -> list:
    """
    Extract common technical skills by keyword matching.
    Extend the skill list as needed.
    """
    skill_keywords = [
        "python", "java", "c++", "c#", "javascript", "html", "css",
        "sql", "mongodb", "react", "angular", "node", "flask", "django",
        "tensorflow", "pytorch", "machine learning", "data analysis",
        "excel", "git", "docker", "aws"
    ]
    found_skills = []
    text_lower = text.lower()
    for skill in skill_keywords:
        if skill in text_lower:
            found_skills.append(skill)
    return list(set(found_skills))


def extract_education(text: str) -> list:
    """
    Extract education details using regex for common degrees.
    """
    education_keywords = [
        "bachelor", "master", "b.tech", "m.tech", "phd", "b.sc", "m.sc",
        "mba", "bca", "mca", "b.com", "m.com", "engineering", "degree"
    ]
    found_education = []
    text_lower = text.lower()
    for edu in education_keywords:
        if edu in text_lower:
            found_education.append(edu)
    return list(set(found_education))


def parse_resume(file_path: str) -> dict:
    """
    Main function to parse resume and return structured data.
    """
    text = extract_text_from_pdf(file_path)

    resume_data = {
        "name": extract_name(text),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "skills": extract_skills(text),
        "education": extract_education(text),
    }
    return resume_data


if __name__ == "__main__":
    # Example usage
    sample_resume = r"D:\Desktop\Mustafa\7th SEM\PBL\sample_resume.pdf"
    parsed = parse_resume(sample_resume)
    for key, value in parsed.items():
        print(f"{key}: {value}")

