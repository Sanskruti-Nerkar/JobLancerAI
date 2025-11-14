import time
import os
from typing import List, Dict, Tuple, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium import webdriver


class LinkedInJobApplier:
    """
    Automates LinkedIn Easy Apply job applications with resume upload and contact info auto-fill
    """
    
    def __init__(self, session, resume_data: Dict, resume_path: str, max_apply: int = 10, min_score: float = 0.6):
        self.session = session
        self.driver = session.driver
        self.max_apply = max_apply
        self.min_score = min_score
        
        self.resume_data = resume_data
        self.resume_path = os.path.abspath(resume_path)
        
        self.email = resume_data.get('email', '')
        self.phone = resume_data.get('phone', '')
        self.name = resume_data.get('name', '')
        
        if self.phone:
            self.phone = ''.join(filter(str.isdigit, self.phone))
        
        if not self.driver:
            raise RuntimeError("Session driver not initialized")
        
        if not os.path.exists(self.resume_path):
            raise FileNotFoundError(f"Resume not found: {self.resume_path}")
        
        print(f"\n📋 Applier initialized:")
        print(f"   Name: {self.name}")
        print(f"   Email: {self.email}")
        print(f"   Phone: {self.phone}")
        print(f"   Resume: {os.path.basename(self.resume_path)}")
    
    def check_external_application(self) -> bool:
        try:
            page_text = self.driver.page_source.lower()
            external_indicators = [
                'apply on company site',
                'apply on external site',
                'continue to company site',
                'visit company website',
                'external application'
            ]
            return any(indicator in page_text for indicator in external_indicators)
        except Exception:
            return False
    
    def find_apply_button(self) -> Tuple[Optional[object], Optional[str]]:
        print("  🔍 Searching for Apply button...")

        if self.check_external_application():
            print("  ⭐️ Detected external-only application")
            return (None, 'external')

        selectors = [
            (By.XPATH, "//button[contains(., 'Easy Apply')]"),
            (By.XPATH, "//button[contains(@aria-label, 'Easy Apply')]"),
            (By.CSS_SELECTOR, "button.jobs-apply-button--top-card"),
            (By.CSS_SELECTOR, "button[aria-label*='Easy Apply']"),
            (By.CSS_SELECTOR, "button.jobs-apply-button"),
            (By.XPATH, "//button[contains(@class, 'jobs-apply-button')]"),
        ]

        for by, sel in selectors:
            try:
                elements = self.driver.find_elements(by, sel)
                
                for el in elements:
                    if not el.is_displayed():
                        continue
                    
                    text = (el.get_attribute('textContent') or el.text or '').strip().lower()
                    aria = (el.get_attribute('aria-label') or '').lower()

                    if 'easy apply' in text or 'easy' in aria:
                        print(f"  ✅ Found Easy Apply button")
                        return (el, 'easy')

                    if 'apply' in text or 'apply' in aria:
                        if 'save' not in text and 'follow' not in text:
                            return (el, 'external')

            except Exception:
                continue

        print("  ❌ No Apply button found")
        return (None, None)
    
    def safe_click(self, element) -> bool:
        strategies = [
            lambda: element.click(),
            lambda: self.driver.execute_script("arguments[0].click();", element),
            lambda: self.driver.execute_script("arguments[0].scrollIntoView(true); arguments[0].click();", element),
        ]
        
        for strategy in strategies:
            try:
                strategy()
                return True
            except Exception:
                continue
        
        return False
    
    def wait_for_modal(self, timeout: int = 10) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".jobs-easy-apply-modal, [role='dialog']"))
            )
            return True
        except TimeoutException:
            return False
    
    def detect_current_page_type(self) -> str:
        """
        Detect EXACTLY which page we're on
        Returns: 'contact', 'resume', 'questions', 'review', or 'unknown'
        """
        try:
            # Check for visible input fields to determine page type
            
            # 1. CONTACT INFO PAGE - has email or phone fields
            email_fields = self.driver.find_elements(By.XPATH, "//input[@type='email']")
            phone_fields = self.driver.find_elements(By.XPATH, "//input[@type='tel']")
            
            if any(f.is_displayed() for f in email_fields + phone_fields):
                return 'contact'
            
            # 2. RESUME PAGE - has file input or resume list
            file_inputs = self.driver.find_elements(By.XPATH, "//input[@type='file']")
            resume_sections = self.driver.find_elements(By.XPATH, 
                "//*[contains(@class, 'jobs-document-upload')]")
            
            if any(f.is_displayed() for f in file_inputs) or \
               any(r.is_displayed() for r in resume_sections):
                return 'resume'
            
            # 3. ADDITIONAL QUESTIONS PAGE - has other form fields
            # Multiple ways to detect questions section
            
            # Method 1: Check for "Additional Questions" title/heading (most reliable)
            page_text = self.driver.page_source.lower()
            
            # Look for "Additional Questions" heading specifically
            additional_questions_heading = self.driver.find_elements(By.XPATH,
                "//*[contains(text(), 'Additional Questions')] | "
                "//*[contains(text(), 'Additional Question')] | "
                "//h2[contains(text(), 'Additional Questions')] | "
                "//h3[contains(text(), 'Additional Questions')] | "
                "//div[contains(text(), 'Additional Questions')]")
            
            if additional_questions_heading:
                # Check if it's visible
                for heading in additional_questions_heading:
                    try:
                        if heading.is_displayed():
                            return 'questions'
                    except:
                        continue
            
            # Method 1b: Check page text for "Additional Questions" or question indicators
            if any(indicator in page_text for indicator in [
                'additional questions', 'additional question', 
                'please answer', 'please share', 'please confirm',
                'how many years', 'what is your', 'willing to',
                'are you comfortable', 'have you completed', 'do you have'
            ]):
                # Verify it's not contact or resume section
                if 'contact info' not in page_text and 'resume' not in page_text:
                    return 'questions'
            
            # Method 2: Look for radio button groups or dropdowns with question labels
            # This is characteristic of Additional Questions section
            
            # Check for radio button groups (Yes/No questions)
            radio_groups = self.driver.find_elements(By.XPATH,
                "//div[contains(@class, 'jobs-easy-apply-form-element')]//input[@type='radio'] | "
                "//fieldset//input[@type='radio']")
            
            # Check for dropdown selects with "Select an option" text
            selects = self.driver.find_elements(By.XPATH,
                "//div[contains(@class, 'jobs-easy-apply-form-element')]//select | "
                "//select[contains(@class, 'jobs-easy-apply-form-element')]")
            
            # Count visible radio groups and selects
            visible_radio_groups = set()
            for radio in radio_groups:
                try:
                    if radio.is_displayed():
                        # Get the name attribute to group them
                        name = radio.get_attribute('name')
                        if name:
                            visible_radio_groups.add(name)
                except:
                    continue
            
            visible_selects = [s for s in selects if s.is_displayed()]
            
            # If we have multiple radio groups or selects, likely questions section
            if len(visible_radio_groups) >= 2 or len(visible_selects) >= 1:
                # Verify by checking for question labels nearby
                labels = self.driver.find_elements(By.XPATH,
                    "//div[contains(@class, 'jobs-easy-apply-form-section')]//label | "
                    "//label[contains(@class, 'jobs-easy-apply-form-element__label')] | "
                    "//label[contains(text(), '?')] | "
                    "//div[contains(@class, 'jobs-easy-apply-form-element')]//label")
                
                question_labels_found = 0
                for label in labels:
                    try:
                        if label.is_displayed():
                            text = label.text.strip().lower()
                            if text and len(text) > 5:
                                # Skip contact fields
                                if any(skip in text for skip in [
                                    'email', 'phone', 'mobile', 'first name', 'last name',
                                    'resume', 'upload', 'contact'
                                ]):
                                    continue
                                
                                # Check if it looks like a question
                                if '?' in text or any(q_word in text for q_word in [
                                    'what is', 'how many', 'please', 'willing', 'confirm',
                                    'share', 'experience', 'years', 'ctc', 'notice period',
                                    'are you', 'have you', 'do you', 'comfortable', 'completed'
                                ]):
                                    question_labels_found += 1
                    except:
                        continue
                
                # If we found question labels along with radio/select elements, it's questions section
                if question_labels_found >= 1:
                    return 'questions'
            
            # Method 3: Check for form elements that aren't email/phone/file inputs
            form_inputs = self.driver.find_elements(By.XPATH,
                "//div[contains(@class, 'jobs-easy-apply-form-element')]//input | "
                "//div[contains(@class, 'jobs-easy-apply-form-element')]//select | "
                "//div[contains(@class, 'jobs-easy-apply-form-element')]//textarea")
            
            non_contact_inputs = 0
            for inp in form_inputs:
                try:
                    if inp.is_displayed():
                        inp_type = inp.get_attribute('type') or ''
                        inp_id = (inp.get_attribute('id') or '').lower()
                        inp_name = (inp.get_attribute('name') or '').lower()
                        
                        # Skip email, phone, file inputs
                        if inp_type in ['email', 'tel', 'file']:
                            continue
                        if 'email' in inp_id or 'phone' in inp_id or 'tel' in inp_id:
                            continue
                        if 'email' in inp_name or 'phone' in inp_name:
                            continue
                        
                        # If it's a text input, select, or textarea that's not contact info
                        if inp_type in ['text', 'number'] or inp.tag_name in ['select', 'textarea']:
                            non_contact_inputs += 1
                except:
                    continue
            
            # If we have multiple non-contact form inputs, likely questions section
            if non_contact_inputs >= 2:
                return 'questions'
            
            # 4. REVIEW PAGE - check button text
            buttons = self.driver.find_elements(By.CSS_SELECTOR, 
                "button.artdeco-button--primary")
            
            for btn in buttons:
                if btn.is_displayed():
                    text = (btn.text or '').lower()
                    aria = (btn.get_attribute('aria-label') or '').lower()
                    
                    if 'submit' in text or 'submit' in aria:
                        return 'review'
            
            return 'unknown'
            
        except Exception as e:
            print(f"    ⚠️  Detection error: {str(e)[:60]}")
            return 'unknown'
    
    def is_resume_already_selected(self) -> bool:
        try:
            checked_selectors = [
                "//input[@type='radio' and @checked]",
                "//input[@type='radio' and @aria-checked='true']",
            ]
            
            for selector in checked_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements:
                        for elem in elements:
                            parent_html = elem.get_attribute('outerHTML') or ''
                            if 'resume' in parent_html.lower() or 'document' in parent_html.lower():
                                return True
                except:
                    continue
            
            return False
            
        except Exception:
            return False
    
    def handle_resume_section(self) -> bool:
        print("  📄 Resume section")
        
        try:
            if self.is_resume_already_selected():
                print("    ✅ Already selected")
                return True
            
            resume_filename = os.path.basename(self.resume_path)
            
            # Try to select existing
            resume_items = self.driver.find_elements(By.XPATH, 
                "//*[contains(@class, 'jobs-document-upload')]//li")
            
            for item in resume_items:
                try:
                    if resume_filename in item.text or os.path.splitext(resume_filename)[0] in item.text:
                        radio = item.find_element(By.XPATH, ".//input[@type='radio']")
                        if not radio.is_selected():
                            self.safe_click(radio)
                            time.sleep(1)
                            print(f"    ✅ Selected: {resume_filename[:40]}")
                            return True
                except:
                    continue
            
            # Upload
            file_inputs = self.driver.find_elements(By.XPATH, "//input[@type='file']")
            
            for file_input in file_inputs:
                try:
                    file_input.send_keys(self.resume_path)
                    print(f"    ✅ Uploaded: {resume_filename[:40]}")
                    time.sleep(2)
                    return True
                except:
                    continue
            
            print("    ℹ️  No upload needed")
            return True
            
        except Exception as e:
            print(f"    ⚠️  Error: {str(e)[:60]}")
            return True
    
    def fill_contact_info(self) -> bool:
        print("  📞 Contact info section")
        
        try:
            filled_something = False
            
            if self.email:
                try:
                    email_field = self.driver.find_element(By.XPATH, "//input[@type='email']")
                    if email_field.is_displayed():
                        current = email_field.get_attribute('value') or ''
                        if not current:
                            email_field.clear()
                            email_field.send_keys(self.email)
                            print(f"    ✅ Email: {self.email}")
                            filled_something = True
                except:
                    pass
            
            if self.phone:
                try:
                    phone_field = self.driver.find_element(By.XPATH, "//input[@type='tel']")
                    if phone_field.is_displayed():
                        current = phone_field.get_attribute('value') or ''
                        if not current:
                            phone_field.clear()
                            phone_field.send_keys(self.phone)
                            print(f"    ✅ Phone: {self.phone}")
                            filled_something = True
                except:
                    pass
            
            if not filled_something:
                print("    ℹ️  Already filled")
            
            return True
            
        except Exception:
            return True
    
    def handle_additional_questions(self) -> bool:
        print("  ❓ Additional questions section")
        print("\n    " + "="*70)
        print("    ⚠️  MANUAL INPUT REQUIRED")
        print("    Please answer ALL questions in the browser window.")
        print("    " + "="*70)
        
        input("\n    ⏸️  Press ENTER after answering all questions...")
        
        print("    ✅ Questions answered")
        return True
    
    def check_submission_success(self) -> bool:
        success_indicators = [
            (By.XPATH, "//h3[contains(., 'Application sent')]"),
            (By.XPATH, "//h2[contains(., 'Application sent')]"),
            (By.XPATH, "//*[contains(text(), 'Your application was sent')]"),
        ]
        
        for by, selector in success_indicators:
            try:
                element = self.driver.find_element(by, selector)
                if element and element.is_displayed():
                    return True
            except:
                continue
        
        return False
    
    def handle_easy_apply_form(self) -> bool:
        """
        Handle Easy Apply form with LINEAR FLOW - each section ONCE
        Flow: Contact → Resume → Questions → Review → Submit
        """
        print("\n🔍 Starting Easy Apply...")
        
        if not self.wait_for_modal():
            print("❌ Modal did not appear")
            return False
        
        time.sleep(2)
        
        max_steps = 10
        current_step = 0
        consecutive_errors = 0
        
        # Track what we've completed (each section only once!)
        completed_sections = set()
        
        while current_step < max_steps:
            try:
                current_step += 1
                
                # Check if submitted
                if self.check_submission_success():
                    print("\n✅ Application submitted!")
                    return True
                
                time.sleep(1.5)
                
                # Detect current page type
                page_type = self.detect_current_page_type()
                
                print(f"\n📋 Step {current_step} - [{page_type.upper()}]")
                
                # Handle based on page type (only if not done before)
                handled = False
                
                if page_type == 'contact' and 'contact' not in completed_sections:
                    self.fill_contact_info()
                    completed_sections.add('contact')
                    handled = True
                    
                elif page_type == 'resume' and 'resume' not in completed_sections:
                    self.handle_resume_section()
                    completed_sections.add('resume')
                    handled = True
                    
                elif page_type == 'questions' and 'questions' not in completed_sections:
                    self.handle_additional_questions()
                    completed_sections.add('questions')
                    handled = True
                    
                elif page_type == 'review':
                    print("  📝 Review page - ready to submit")
                    handled = True
                    
                elif page_type == 'unknown':
                    print("  ⚠️  Unknown page type")
                    # Fallback: Check what section we're actually on
                    # Priority: Contact Info > Resume > Questions
                    try:
                        page_text = self.driver.page_source.lower()
                        
                        # FIRST: Check if it's CONTACT INFO section
                        # Look for email/phone fields or contact info indicators
                        email_fields = self.driver.find_elements(By.XPATH, 
                            "//input[@type='email'] | //input[contains(@id, 'email')] | //input[contains(@name, 'email')]")
                        phone_fields = self.driver.find_elements(By.XPATH, 
                            "//input[@type='tel'] | //input[contains(@id, 'phone')] | //input[contains(@name, 'phone')]")
                        
                        contact_indicators = [
                            'contact info', 'contact information', 'email address', 
                            'phone number', 'mobile number'
                        ]
                        
                        has_contact_fields = any(f.is_displayed() for f in email_fields + phone_fields)
                        has_contact_text = any(indicator in page_text for indicator in contact_indicators)
                        
                        if has_contact_fields or has_contact_text:
                            # Make sure it's NOT questions section
                            if 'additional questions' not in page_text:
                                print("  🔍 Detected contact info section (fallback detection)")
                                if 'contact' not in completed_sections:
                                    self.fill_contact_info()
                                    completed_sections.add('contact')
                                    handled = True
                        
                        # SECOND: Check if it's RESUME section (if not contact)
                        if not handled:
                            file_inputs = self.driver.find_elements(By.XPATH, "//input[@type='file']")
                            resume_sections = self.driver.find_elements(By.XPATH, 
                                "//*[contains(@class, 'jobs-document-upload')] | "
                                "//*[contains(@class, 'resume')]")
                            
                            has_resume_fields = any(f.is_displayed() for f in file_inputs) or \
                                               any(r.is_displayed() for r in resume_sections)
                            has_resume_text = 'resume' in page_text or 'upload resume' in page_text
                            
                            if has_resume_fields or has_resume_text:
                                # Make sure it's NOT questions section
                                if 'additional questions' not in page_text:
                                    print("  🔍 Detected resume section (fallback detection)")
                                    if 'resume' not in completed_sections:
                                        self.handle_resume_section()
                                        completed_sections.add('resume')
                                        handled = True
                        
                        # THIRD: Check if it's QUESTIONS section (if not contact or resume)
                        if not handled:
                            # Check for "Additional Questions" heading
                            additional_questions_heading = self.driver.find_elements(By.XPATH,
                                "//*[contains(text(), 'Additional Questions')] | "
                                "//*[contains(text(), 'Additional Question')]")
                            
                            if additional_questions_heading:
                                for heading in additional_questions_heading:
                                    try:
                                        if heading.is_displayed():
                                            print("  🔍 Detected 'Additional Questions' heading (fallback detection)")
                                            if 'questions' not in completed_sections:
                                                self.handle_additional_questions()
                                                completed_sections.add('questions')
                                                handled = True
                                            break
                                    except:
                                        continue
                            
                            # If not found by heading, check for radio groups and selects
                            if not handled:
                                question_indicators = [
                                    'additional questions', 'additional question',
                                    'what is your', 'how many years', 'please share',
                                    'please confirm', 'willing to', 'notice period',
                                    'are you comfortable', 'have you completed', 'do you have'
                                ]
                                
                                if any(indicator in page_text for indicator in question_indicators):
                                    # Make sure it's NOT contact or resume section
                                    if 'contact info' not in page_text and 'resume' not in page_text:
                                        # Check for radio button groups or selects
                                        radio_groups = self.driver.find_elements(By.XPATH,
                                            "//div[contains(@class, 'jobs-easy-apply-form-element')]//input[@type='radio']")
                                        selects = self.driver.find_elements(By.XPATH,
                                            "//div[contains(@class, 'jobs-easy-apply-form-element')]//select")
                                        
                                        visible_radios = [r for r in radio_groups if r.is_displayed()]
                                        visible_selects = [s for s in selects if s.is_displayed()]
                                        
                                        # Check for visible question labels
                                        question_labels = self.driver.find_elements(By.XPATH,
                                            "//label[contains(text(), '?')] | "
                                            "//div[contains(@class, 'jobs-easy-apply-form-element')]//label")
                                        
                                        visible_questions = [l for l in question_labels if l.is_displayed()]
                                        
                                        if (len(visible_radios) >= 2 or len(visible_selects) >= 1) and len(visible_questions) >= 1:
                                            print("  🔍 Detected questions section by form structure (fallback detection)")
                                            if 'questions' not in completed_sections:
                                                self.handle_additional_questions()
                                                completed_sections.add('questions')
                                                handled = True
                    except Exception as e:
                        print(f"    ⚠️  Fallback detection error: {str(e)[:60]}")
                        pass
                    
                    # If still not handled, try to fill whatever we haven't done yet (in order)
                    if not handled:
                        if 'contact' not in completed_sections:
                            print("  🔍 Attempting to handle as contact info section")
                            self.fill_contact_info()
                            completed_sections.add('contact')
                            handled = True
                        elif 'resume' not in completed_sections:
                            print("  🔍 Attempting to handle as resume section")
                            self.handle_resume_section()
                            completed_sections.add('resume')
                            handled = True
                        elif 'questions' not in completed_sections:
                            print("  🔍 Attempting to handle as questions section")
                            self.handle_additional_questions()
                            completed_sections.add('questions')
                            handled = True
                
                if not handled:
                    print("  ℹ️  Already processed this section")
                
                # Find and click next/submit button
                button_clicked, is_submit = self.find_and_click_next_button()
                
                if not button_clicked:
                    consecutive_errors += 1
                    if consecutive_errors >= 3:
                        print("\n⚠️  Cannot find next button")
                        user_input = input("Did you submit manually? (y/n): ").strip().lower()
                        return user_input == 'y'
                    continue
                
                consecutive_errors = 0
                
                # If submit button, wait for confirmation
                if is_submit:
                    print("  ⏳ Waiting for confirmation...")
                    
                    for _ in range(5):
                        time.sleep(2)
                        if self.check_submission_success():
                            print("\n✅ Application submitted!")
                            return True
                    
                    # Ask user
                    user_input = input("\nDid you see 'Application sent'? (y/n): ").strip().lower()
                    return user_input == 'y'
                
                time.sleep(1)
                
            except Exception as e:
                print(f"⚠️  Error at step {current_step}: {str(e)[:80]}")
                consecutive_errors += 1
                if consecutive_errors >= 3:
                    return False
        
        print("❌ Max steps reached")
        return False
    
    def find_and_click_next_button(self) -> Tuple[bool, bool]:
        """Find and click next/submit/review button"""
        button_selectors = [
            # Submit (highest priority)
            (By.XPATH, "//button[@aria-label='Submit application']", True),
            (By.XPATH, "//button[contains(@aria-label, 'Submit')]", True),
            (By.XPATH, "//button[contains(., 'Submit application')]", True),
            
            # Review
            (By.XPATH, "//button[@aria-label='Review your application']", False),
            (By.XPATH, "//button[contains(., 'Review')]", False),
            
            # Next/Continue
            (By.XPATH, "//button[@aria-label='Continue to next step']", False),
            (By.XPATH, "//button[contains(., 'Next')]", False),
            
            # Generic primary button
            (By.CSS_SELECTOR, "button.artdeco-button--primary", False),
        ]
        
        for by, selector, is_submit in button_selectors:
            try:
                button = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((by, selector))
                )
                
                if button.is_displayed() and button.is_enabled():
                    button_text = button.text.strip() or button.get_attribute('aria-label') or 'Button'
                    print(f"  → Clicking: {button_text}")
                    
                    if self.safe_click(button):
                        return (True, is_submit)
                    
            except Exception:
                continue
        
        print("  ⚠️  No button found")
        return (False, False)
    
    def close_modal(self):
        close_selectors = [
            (By.XPATH, "//button[@aria-label='Dismiss']"),
            (By.CSS_SELECTOR, ".artdeco-modal__dismiss"),
        ]
        
        for by, selector in close_selectors:
            try:
                close_btn = self.driver.find_element(by, selector)
                if close_btn.is_displayed():
                    self.safe_click(close_btn)
                    time.sleep(1)
                    return True
            except:
                continue
        
        return False
    
    def apply_to_jobs(self, matches: List[Dict]) -> Dict:
        results = {
            'attempted': 0,
            'applied': 0,
            'failed': 0,
            'skipped': 0,
            'details': []
        }
        
        matches.sort(key=lambda x: x['final_score'], reverse=True)
        applied_count = 0
        
        for idx, match in enumerate(matches, 1):
            if applied_count >= self.max_apply:
                print(f"\n✋ Max reached ({self.max_apply})")
                break
            
            job = match['job']
            score = match['final_score']
            
            if score < self.min_score:
                results['skipped'] += 1
                continue
            
            results['attempted'] += 1
            
            print(f"\n{'─'*60}")
            print(f"📋 Job {idx} - {job.get('title')}")
            print(f"Company: {job.get('company')}")
            print(f"Score: {score:.1%}")
            print(f"{'─'*60}")
            
            try:
                success, app_type = self._apply_to_job(job)
                
                if success and app_type == 'easy':
                    applied_count += 1
                    results['applied'] += 1
                    print("✅ APPLIED!")
                elif app_type == 'skipped':
                    results['skipped'] += 1
                    print("⭐️ Skipped")
                else:
                    results['failed'] += 1
                    print("❌ FAILED")
                
            except Exception as e:
                results['failed'] += 1
                print(f"❌ Error: {str(e)[:80]}")
            
            time.sleep(3)
        
        return results
    
    def _apply_to_job(self, job: Dict) -> Tuple[bool, Optional[str]]:
        if not job.get('link'):
            return (False, None)
        
        try:
            print("🌐 Loading...")
            self.driver.get(job['link'])
            
            WebDriverWait(self.driver, 15).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            time.sleep(3)
            
            apply_button, button_type = self.find_apply_button()

            if not apply_button:
                return (False, 'skipped' if button_type == 'external' else None)
            
            if button_type != 'easy':
                return (False, 'skipped')
            
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", apply_button)
            time.sleep(1)
            
            if not self.safe_click(apply_button):
                return (False, None)
            
            print("  ✅ Clicked Easy Apply")
            time.sleep(3)
            
            success = self.handle_easy_apply_form()
            
            if not success:
                self.close_modal()
            
            return (success, 'easy')
                
        except Exception as e:
            try:
                self.close_modal()
            except:
                pass
            return (False, None)


class JobApplier(LinkedInJobApplier):
    """Alias for backward compatibility"""
    pass