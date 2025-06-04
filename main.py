from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, NoAlertPresentException, UnexpectedAlertPresentException
)
import pandas as pd
import time
import re
import os
import shutil

def setup_chrome_profile():
    """Setup a dedicated Chrome profile directory for Selenium, ensuring a clean state."""
    selenium_profile_path = r"C:\SeleniumChromeProfile"  # Ensure this path is writable
    profile_default_subdir = os.path.join(selenium_profile_path, "Default")

    try:
        if os.path.exists(profile_default_subdir):
            print(f"Attempting to remove existing 'Default' subdirectory: {profile_default_subdir}")
            try:
                shutil.rmtree(profile_default_subdir)
                print(f"✅ Successfully removed {profile_default_subdir} for a clean session.")
            except Exception as e:
                print(f"⚠️ Warning: Could not remove {profile_default_subdir}: {e}. Decryption errors might persist if old data is reused by Chrome.")
        elif os.path.exists(selenium_profile_path):
             print(f"ℹ️ Profile directory {selenium_profile_path} exists, but 'Default' subdir not found or already handled.")
        
        if not os.path.exists(selenium_profile_path):
            print(f"Creating dedicated Selenium Chrome profile directory at: {selenium_profile_path}")
            os.makedirs(selenium_profile_path, exist_ok=True)
        
        print(f"ℹ️ Chrome will use profile directory: {selenium_profile_path}. A clean profile will be initialized by Chrome.")
        return selenium_profile_path
        
    except Exception as e:
        print(f"❌ Error managing Selenium profile directory {selenium_profile_path}: {e}")
        print("Will attempt to let Selenium use its default ephemeral profile if this fails.")
        return None

def setup_driver():
    """Setup Chrome driver with profile options."""
    selenium_profile_path = setup_chrome_profile()
    
    chrome_options = Options()
    
    if selenium_profile_path:
        chrome_options.add_argument(f"--user-data-dir={selenium_profile_path}")
    else:
        print("⚠️ Could not set up a persistent user data directory; Selenium will use a temporary profile.")

    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins-discovery")
    chrome_options.add_argument("--disable-images")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("--remote-allow-origins=*")
    # chrome_options.add_argument("--headless")

    driver_instance = None
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())
        driver_instance = webdriver.Chrome(service=service, options=chrome_options)
        driver_instance.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        print("✅ Successfully setup Chrome driver using webdriver-manager.")
        return driver_instance
    except ImportError:
        print("⚠️ webdriver-manager not installed. Install it with: pip install webdriver-manager")
    except Exception as e:
        print(f"❌ Error with webdriver-manager: {e}")
    
    try:
        print("🔄 Trying system Chrome driver as fallback...")
        driver_instance = webdriver.Chrome(options=chrome_options)
        driver_instance.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        print("✅ Successfully setup Chrome driver using system ChromeDriver.")
        return driver_instance
    except Exception as e:
        print(f"❌ Error setting up system Chrome driver: {e}")
    
    print("❌❌ All Chrome driver setup attempts failed.")
    return None

def clean_text(text):
    """Clean and normalize text data."""
    if not text: return "N/A"
    cleaned = re.sub(r'\s+', ' ', str(text).strip())
    cleaned = re.sub(r'<[^>]+>', '', cleaned)
    return cleaned if cleaned else "N/A"

def extract_currency_amount(text):
    """Extract currency amount and clean it."""
    if not text or str(text).strip() == "": return "N/A"
    cleaned = str(text).replace("₹", "").replace("Rs.", "").replace(",", "").strip()
    amount_match = re.search(r'[\d\.]+\d*', cleaned) 
    if amount_match:
        return amount_match.group() 
    return cleaned if cleaned else "N/A"

def scrape_cpwd_tenders():
    driver = setup_driver()
    if not driver:
        return
    
    all_tenders_data = []
    base_wait = WebDriverWait(driver, 10)

    try:
        print("🌐 Opening CPWD website...")
        driver.set_page_load_timeout(60)
        driver.get("https://etender.cpwd.gov.in/")
        print(f"  Landed on initial URL: {driver.current_url}")

        navigated_to_tender_list_page = False
        
        try:
            print("🔍 Attempting to locate and click 'All' link for New Tenders on the initial page...")
            try:
                alert = WebDriverWait(driver, 2).until(EC.alert_is_present())
                print(f"🚨 Immediate alert detected on page load: {alert.text}")
                alert.accept()
                print("✅ Immediate alert accepted. Pausing briefly...")
                time.sleep(1) 
                print(f"  URL after handling immediate alert: {driver.current_url}")
            except TimeoutException:
                print("ℹ️ No super-fast initial alert detected before trying to click 'All' link.")

            all_tenders_link_id = "a_TenderswithinOneday3"
            all_link_element = base_wait.until(
                EC.element_to_be_clickable((By.ID, all_tenders_link_id))
            )
            print(f"✅ Found 'All' link (id='{all_tenders_link_id}'). Clicking...")
            driver.execute_script("arguments[0].click();", all_link_element)
            
            print("⏳ Paused for 5s after clicking 'All' link to observe navigation and potential new alerts...")
            time.sleep(5)

            try:
                alert = WebDriverWait(driver, 5).until(EC.alert_is_present())
                print(f"🚨 Alert detected after clicking 'All' link: {alert.text}")
                alert.accept()
                print("✅ Alert (after 'All' click) accepted.")
                time.sleep(2)
            except TimeoutException:
                print("ℹ️ No alert found after clicking 'All' link and brief wait.")
            
            current_url_after_click = driver.current_url
            print(f"  URL after clicking 'All' link and handling potential alert: {current_url_after_click}")

            # Check if navigation was successful
            # The XPath for table check still includes 'Tender ID' as it might still be a good structural identifier
            # even if we don't extract its data.
            if ("TenderswithinOneday.html" in current_url_after_click or \
                WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "//table[.//th[contains(text(), 'Tender ID')]]")))): # Table structure might still have Tender ID column
                print("✅ Successfully navigated to a tender list page via the 'All' link.")
                navigated_to_tender_list_page = True
            else:
                print(f"⚠️ Clicking 'All' link did not conclusively lead to an expected tender page or table. Current URL: {current_url_after_click}")

        except TimeoutException:
            print(f"❌ Timeout: Could not find or click the 'All' link (id='{all_tenders_link_id}') on the initial page.")
            print(f"  Current URL when failed: {driver.current_url}")
            if "login.html" in driver.current_url:
                print("  It's likely the CPWD Signer alert redirected to login.html too quickly.")
        except UnexpectedAlertPresentException as e_alert_during_click:
            alert_text = e_alert_during_click.alert_text if hasattr(e_alert_during_click, 'alert_text') and e_alert_during_click.alert_text else "N/A"
            print(f"🚨 UnexpectedAlertPresentException occurred while trying to click 'All' link. Alert: '{alert_text}'")
            try:
                current_alert_obj = driver.switch_to.alert
                print(f"  Handling alert: {current_alert_obj.text}")
                current_alert_obj.accept()
            except NoAlertPresentException:
                print("  No alert found when trying to clear UnexpectedAlert.")
        except Exception as e_click_all_link:
            print(f"❌ An error occurred attempting to click the 'All' link: {e_click_all_link}")

        if not navigated_to_tender_list_page:
            print(" FAILED TO NAVIGATE TO TENDER LIST VIA 'ALL' LINK.")
            print(" The CPWD Signer requirement is likely preventing access or the 'All' link is not reachable.")
            return

        print("🔍 Looking for tender table on the current page...")
        try:
            # The table might still have 'Tender ID' as a column, so using it in XPath is fine for locating the table
            tender_table_element = WebDriverWait(driver, 15).until(EC.presence_of_element_located((
                By.XPATH, "//table[.//th[contains(text(), 'Tender ID')] and .//th[contains(text(), 'NIT/RFP NO')]]"
            )))
            print("✅ Tender table found.")
            
            headers_text = [clean_text(th.text) for th in tender_table_element.find_elements(By.TAG_NAME, "th")]
            print(f"📋 Table headers: {headers_text}")

            # If 'Tender ID' was column 0, and we skip it, we now need data from original columns 1-8.
            # This means we expect at least 8 columns in the `cells` list to get data up to 'Bid Opening Date'.
            # The original indices for desired data were: NIT/RFP NO (1) to Bid Opening Date (7).
            # If we skip cells[0] (Tender ID), then NIT/RFP NO is cells[1], Name of Work is cells[2], etc.
            # No, if we are skipping the *data* from the first column (Tender ID), our new indices start from what was originally the second column.
            # So, ref_no (orig cells[1]) -> becomes cells[0] for our extraction logic if we ignore the content of the true cells[0].
            # Let's be clear: we are IGNORING the content of the actual first `<td>` if it's Tender ID.
            # We will extract from the second `<td>` onwards.

            # Original headers: ['Tender ID', 'NIT/RFP NO', 'Name of Work', 'Pub Office', 'Est Cost', 'EMD', 'Closing', 'Opening', 'Action']
            # We want:                'NIT/RFP NO', 'Name of Work', 'Pub Office', 'Est Cost', 'EMD', 'Closing', 'Opening'
            # These correspond to actual cell indices: 1, 2, 3, 4, 5, 6, 7
            # So, if a row has `cells`, we will access `cells[1]` through `cells[7]`.
            # This means we need `len(cells)` to be at least 8 (to cover index 7).
            expected_min_cells_in_row = 8 # To access up to index 7 (original 'Bid Opening Date')

            table_rows = tender_table_element.find_elements(By.TAG_NAME, "tr")
            data_rows_in_table = [row for row in table_rows if row.find_elements(By.TAG_NAME, "td")]
            print(f"📊 Found {len(data_rows_in_table)} potential data rows.")

            for i, row in enumerate(data_rows_in_table[:20]):
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) < expected_min_cells_in_row: 
                    print(f"ℹ️ Row {i+1} has {len(cells)} cells, expected at least {expected_min_cells_in_row} to extract all desired fields. Skipping.")
                    continue
                
                # Indices shift: what was cells[1] is now our first piece of data (ref_no)
                tender_item = {
                    # "tender_id" is removed
                    "ref_no": clean_text(cells[1].text),            # Original cells[1] is NIT/RFP NO
                    "title": clean_text(cells[2].text),             # Original cells[2] is Name of Work
                    "publishing_office": clean_text(cells[3].text), # Original cells[3] is Tender Publishing Office
                    "tender_value": extract_currency_amount(cells[4].text), # Original cells[4] is Estimated Cost
                    "emd": extract_currency_amount(cells[5].text),          # Original cells[5] is EMD Amount
                    "bid_submission_end_date": clean_text(cells[6].text),   # Original cells[6]
                    "bid_open_date": clean_text(cells[7].text)              # Original cells[7]
                }
                
                if any(val not in ["N/A", ""] for name, val in tender_item.items() if name in ["ref_no", "title"]):
                    all_tenders_data.append(tender_item)
                    print(f"✅ Extracted: Ref '{tender_item['ref_no']}', Title '{tender_item['title'][:25]}...'")
            
            if not all_tenders_data: 
                print("❌ No data extracted from table. Content might be blocked or table was empty/unparsable.")
            else: 
                df = pd.DataFrame(all_tenders_data)
                output_columns = ["ref_no", "title", "publishing_office", "tender_value", "bid_submission_end_date", "emd", "bid_open_date"] # "tender_id" removed
                df = df.reindex(columns=output_columns, fill_value="N/A")
                
                csv_filename = "cpwd_tenders_final_output.csv"
                df.to_csv(csv_filename, index=False, encoding='utf-8')
                print(f"\n✅ SUCCESS! Data saved to {csv_filename}. Extracted {len(df)} tenders.")
                if not df.empty: 
                    print("\n📋 First few rows of extracted data:")
                    print(df.head().to_string())

        except TimeoutException:
            print(f"❌ Timeout: Tender table not found on page {driver.current_url} even after presumed navigation.")
            print("   This strongly suggests content is blocked by 'CPWD Signer' or page structure is unexpected.")
            
    except Exception as e_main:
        print(f"❌ An critical unexpected error occurred in the main script: {e_main}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            current_url_at_exit = "N/A"
            try:
                current_url_at_exit = driver.current_url
            except Exception: 
                pass 

            print(f"💾 Saving final page source from: {current_url_at_exit}")
            try:
                with open("debug_final_page_state.html", "w", encoding="utf-8") as f:
                     f.write(driver.page_source)
            except Exception as e_save:
                print(f"  Could not save debug page: {e_save}")
            
            print("🔚 Closing browser...")
            driver.quit()
            print("✅ Browser closed.")

if __name__ == "__main__":
    print("🚀 CPWD Tender Scraper Initializing...")
    print("Make sure Chrome and ChromeDriver are installed and accessible!")
    print("-" * 70)
    scrape_cpwd_tenders()
    print("-" * 70)
    print("🏁 Scraping process completed!")