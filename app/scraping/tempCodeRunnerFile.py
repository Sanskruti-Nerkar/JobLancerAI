import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup


def init_driver(headless=True):
    """
    Initialize and return a Selenium WebDriver instance.
    """
    chrome_options = Options()
    if headless:
        chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    # Specify ChromeDriver path in the project folder (nested structure)
    chromedriver_path = r"D:\Desktop\Mustafa\7th SEM\PBL\chromedriver-win64\chromedriver-win64\chromedriver.exe"
    
    driver = webdriver.Chrome(executable_path=chromedriver_path, chrome_options=chrome_options)
    return driver


def search_jobs(driver, query, location, num_pages=1):
    """
    Search for jobs on Naukri.com and return a list of job card elements.
    """
    base_url = f"https://www.naukri.com/{query}-jobs-in-{location}"
    jobs = []
    for page in range(1, num_pages + 1):
        url = f"{base_url}?k={query}&l={location}&page={page}"
        driver.get(url)
        time.sleep(3)  # Wait for page to load
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        cards = soup.find_all('article', {'class': 'jobTuple bgWhite br4 mb-8'})
        jobs.extend(cards)
    return jobs


def parse_job_card(card):
    """
    Parse a single job card BeautifulSoup element and return a dict of job info.
    """
    try:
        title = card.find('a', {'class': 'title'}).text.strip()
    except AttributeError:
        title = None
    try:
        company = card.find('a', {'class': 'subTitle'}).text.strip()
    except AttributeError:
        company = None
    try:
        location = card.find('li', {'class': 'location'}).text.strip()
    except AttributeError:
        location = None
    try:
        summary = card.find('div', {'class': 'job-description fs12 grey-text'}).text.strip()
    except AttributeError:
        summary = None
    try:
        link = card.find('a', {'class': 'title'})['href']
    except (AttributeError, TypeError):
        link = None
    return {
        'title': title,
        'company': company,
        'location': location,
        'summary': summary,
        'link': link
    }


def scrape_jobs(query, location, num_pages=1, headless=True):
    """
    Main function to scrape jobs from Naukri.com.
    Returns a list of job dicts.
    """
    driver = init_driver(headless=headless)
    try:
        cards = search_jobs(driver, query, location, num_pages)
        jobs = [parse_job_card(card) for card in cards]
    finally:
        driver.quit()
    return jobs


if __name__ == "__main__":
    # Example usage
    jobs = scrape_jobs("python-developer", "bangalore", num_pages=2, headless=False)
    for job in jobs:
        print(job)
