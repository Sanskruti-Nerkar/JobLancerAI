import time
from typing import List, Dict
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from app.scraping.job_scraper import init_driver


class JobApplier:
    """
    Automates applying to jobs above a given score threshold.
    Expects each job dict to include: title, company, link, and a score field.
    """

    def __init__(self, headless: bool = False, max_apply: int = 10, per_job_timeout: int = 25,
                 user_data_dir: str = None, profile_directory: str = None, debugger_address: str = None):
        self.headless = headless
        self.max_apply = max_apply
        self.per_job_timeout = per_job_timeout
        self.user_data_dir = user_data_dir
        self.profile_directory = profile_directory
        self.debugger_address = debugger_address

    def _click_first_apply(self, driver) -> bool:
        """Try several common selectors for Apply buttons/links with better debugging."""
        print("  🔍 Searching for Apply button...")
        
        # First, let's see what's actually on the page
        try:
            page_source_preview = driver.page_source[:1000]
            print(f"  📄 Page source preview: {page_source_preview[:200]}...")
        except:
            pass
        
        # Naukri-specific selectors based on actual site structure
        selectors = [
            # Naukri job detail page specific selectors
            (By.XPATH, "//button[contains(@class, 'apply') or contains(@id, 'apply')]"),
            (By.XPATH, "//a[contains(@class, 'apply') or contains(@id, 'apply')]"),
            (By.XPATH, "//button[contains(text(), 'Apply') or contains(text(), 'APPLY') or contains(text(), 'Apply Now')]"),
            (By.XPATH, "//a[contains(text(), 'Apply') or contains(text(), 'APPLY') or contains(text(), 'Apply Now')]"),
            (By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'apply')]"),
            (By.XPATH, "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'apply')]"),
            # Naukri specific class patterns
            (By.CSS_SELECTOR, ".applyBtn, .apply-btn, .apply-button"),
            (By.CSS_SELECTOR, "button.apply, a.apply"),
            (By.CSS_SELECTOR, "[class*='apply']"),
            (By.CSS_SELECTOR, "[id*='apply']"),
            # Generic selectors
            (By.CSS_SELECTOR, "button[class*='apply'], button[id*='apply']"),
            (By.CSS_SELECTOR, "a[class*='apply'], a[id*='apply']"),
            (By.CSS_SELECTOR, "button[title*='Apply'], button[aria-label*='Apply']"),
            (By.CSS_SELECTOR, "a[title*='Apply'], a[aria-label*='Apply']"),
            (By.CSS_SELECTOR, "input[type='button'][value*='Apply']"),
            (By.CSS_SELECTOR, "input[type='submit'][value*='Apply']"),
            # Data attributes
            (By.CSS_SELECTOR, "[data-testid*='apply'], [data-qa*='apply']"),
            # More generic patterns
            (By.XPATH, "//*[contains(@class, 'btn') and contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'apply')]"),
            # Look for any clickable element with "apply" in text
            (By.XPATH, "//*[@onclick and contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'apply')]"),
        ]
        
        for i, (by, selector) in enumerate(selectors):
            try:
                print(f"    Trying selector {i+1}/{len(selectors)}: {selector[:50]}...")
                elem = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((by, selector)))
                
                # Scroll to element and highlight it
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
                driver.execute_script("arguments[0].style.border='3px solid red';", elem)
                time.sleep(1)
                
                # Try clicking
                elem.click()
                print(f"    ✅ Successfully clicked Apply button using selector {i+1}")
                return True
                
            except TimeoutException:
                print(f"    ⏰ Timeout for selector {i+1}")
                continue
            except NoSuchElementException:
                print(f"    ❌ Element not found for selector {i+1}")
                continue
            except Exception as e:
                print(f"    ❌ Error with selector {i+1}: {str(e)[:100]}")
                continue
        
        print("  ❌ No Apply button found with any selector")
        
        # Fallback: Look for any element containing "apply" text
        print("  🔄 Trying fallback method - looking for any element with 'apply' text...")
        try:
            # Get all elements and check their text content
            all_elements = driver.find_elements(By.XPATH, "//*")
            for elem in all_elements:
                try:
                    text = elem.text.lower()
                    if 'apply' in text and len(text) < 50:  # Reasonable length for button text
                        print(f"    Found potential apply element: '{elem.text}'")
                        if elem.is_displayed() and elem.is_enabled():
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
                            driver.execute_script("arguments[0].style.border='3px solid green';", elem)
                            time.sleep(1)
                            elem.click()
                            print(f"    ✅ Successfully clicked fallback element: '{elem.text}'")
                            return True
                except:
                    continue
        except Exception as e:
            print(f"    ❌ Fallback method failed: {str(e)[:100]}")
        
        print("  ❌ No Apply button found with any method")
        return False

    def apply_to_jobs(self, matches: List[Dict], min_score: float = 0.6) -> Dict:
        """
        Open each job link whose final_score >= min_score and attempt to apply.
        Returns a summary with per-job status.
        """
        print(f"\n🚀 Starting auto-application process...")
        print(f"   Min Score: {min_score:.1%}")
        print(f"   Max Applications: {self.max_apply}")
        print(f"   Headless Mode: {self.headless}")
        
        driver = init_driver(headless=self.headless,
                             user_data_dir=self.user_data_dir,
                             profile_directory=self.profile_directory,
                             debugger_address=self.debugger_address)
        results = []
        applied_count = 0
        skipped_count = 0

        try:
            for i, match in enumerate(matches, 1):
                if applied_count >= self.max_apply:
                    print(f"\n⏹️  Reached max applications limit ({self.max_apply})")
                    break

                job = match.get('job', {})
                score = match.get('final_score', 0.0)
                link = job.get('link') or ''
                title = job.get('title') or 'Unknown Title'
                company = job.get('company') or 'Unknown'

                print(f"\n📋 Job {i}/{len(matches)}: {title} at {company}")
                print(f"   Score: {score:.1%} | Link: {link[:50]}...")

                # Check if job meets criteria
                if not link:
                    print("   ❌ Skipping: No link provided")
                    skipped_count += 1
                    continue
                    
                if score < min_score:
                    print(f"   ❌ Skipping: Score {score:.1%} below threshold {min_score:.1%}")
                    skipped_count += 1
                    continue

                print(f"   ✅ Proceeding: Score {score:.1%} meets threshold {min_score:.1%}")
                
                status = {
                    'title': title, 
                    'company': company, 
                    'link': link, 
                    'score': score, 
                    'applied': False, 
                    'error': None
                }
                
                try:
                    print(f"   🌐 Navigating to job page...")
                    # Open in a new tab so the original window stays on search/results
                    driver.execute_script("window.open(arguments[0], '_blank');", link)
                    driver.switch_to.window(driver.window_handles[-1])
                    
                    # Wait for page to load
                    WebDriverWait(driver, self.per_job_timeout).until(
                        lambda d: d.execute_script("return document.readyState") == "complete"
                    )
                    time.sleep(2)  # Give page time to render dynamic content
                    
                    print(f"   📄 Page loaded: {driver.title[:50]}...")

                    # Try to click an Apply button
                    clicked = self._click_first_apply(driver)
                    status['applied'] = clicked
                    
                    if clicked:
                        applied_count += 1
                        print(f"   🎉 SUCCESS: Applied to {title} at {company}")
                    else:
                        print(f"   ❌ FAILED: Could not find/click Apply button")
                        
                except TimeoutException:
                    error_msg = f"Page load timeout after {self.per_job_timeout}s"
                    print(f"   ⏰ TIMEOUT: {error_msg}")
                    status['error'] = error_msg
                except WebDriverException as e:
                    error_msg = f"WebDriver error: {str(e)[:100]}"
                    print(f"   🚫 WEBDRIVER ERROR: {error_msg}")
                    status['error'] = error_msg
                except Exception as e:
                    error_msg = f"Unexpected error: {str(e)[:100]}"
                    print(f"   💥 ERROR: {error_msg}")
                    status['error'] = error_msg

                results.append(status)
                
                # Small delay between applications
                if i < len(matches):
                    time.sleep(2)

        except Exception as e:
            print(f"\n💥 CRITICAL ERROR in application loop: {str(e)}")
            
        finally:
            try:
                print(f"\n🔚 Closing browser...")
                driver.quit()
            except Exception as e:
                print(f"   Warning: Error closing browser: {e}")

        # Generate summary
        attempted = len(results)
        applied = sum(1 for r in results if r.get('applied'))
        failed = attempted - applied
        
        print(f"\n📊 APPLICATION SUMMARY:")
        print(f"   Total Jobs Processed: {len(matches)}")
        print(f"   Jobs Attempted: {attempted}")
        print(f"   Successfully Applied: {applied}")
        print(f"   Failed: {failed}")
        print(f"   Skipped (below threshold): {skipped_count}")
        
        if applied > 0:
            print(f"\n🎉 SUCCESS! Applied to {applied} job(s)")
        else:
            print(f"\n😞 No successful applications")

        summary = {
            'attempted': attempted,
            'applied': applied,
            'failed': failed,
            'skipped': skipped_count,
            'details': results
        }
        return summary


