import os
import time
import csv
import tempfile
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ====== SETTINGS ======
GECKODRIVER_PATH = '/usr/local/bin/geckodriver'
import sys

SEARCH_KEYWORD = sys.argv[1] if len(sys.argv) > 1 else ''

if not SEARCH_KEYWORD.strip():
    print("No keyword provided. Exiting silently.")
    with open('bid_results.csv', 'w', newline='', encoding='utf-8') as f:
        f.write('')  # write empty file
    sys.exit(0)
OUTPUT_CSV = 'bid_results.csv'
URL = 'https://bidplus.gem.gov.in/all-bids'

# ====== Create TEMP DIR for downloads ======
temp_dir = tempfile.mkdtemp()
print(f"Temporary download folder: {temp_dir}")

# ====== Setup Firefox profile for auto-download ======
profile = webdriver.FirefoxProfile()
profile.set_preference("browser.download.folderList", 2)
profile.set_preference("browser.download.dir", temp_dir)
profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/pdf,application/zip,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain")
profile.set_preference("pdfjs.disabled", True)

firefox_options = Options()
firefox_options.add_argument("--start-maximized")
firefox_options.profile = profile
# firefox_options.add_argument("--headless") 
service = Service(GECKODRIVER_PATH)
driver = webdriver.Firefox(service=service, options=firefox_options)

def extract_field(text, label, stop_labels):
    try:
        start = text.index(label) + len(label)
        end = min([text.index(stop, start) for stop in stop_labels if stop in text[start:]] + [len(text)])
        return text[start:end].strip()
    except:
        return "Not Found"

def extract_department_from_html(bid):
    try:
        department_div = bid.find_element(By.XPATH, ".//*[contains(text(),'Department Name And Address:')]/following::div[1]")
        department = department_div.text.strip().replace('\n', ' ').replace('\r', '')
        return department if department else "Not Provided"
    except Exception as e:
        print(f"[ERROR] Extracting department: {e}")
        return "Not Provided"

def extract_bid_number(bid, bid_text):
    # 1. Try to extract from known HTML structure
    try:
        bid_p = bid.find_element(By.CLASS_NAME, "bid_no")
        bid_anchor = bid_p.find_element(By.TAG_NAME, "a")
        if bid_anchor:
            bid_no = bid_anchor.text.strip()
            if bid_no.startswith("GEM"):
                return bid_no
    except Exception as e:
        print("[DEBUG] Not found via HTML structure:", e)

    # 2. Try regex from full text
    regex_match = re.search(r'BID\s*NO[:\-]?\s*(GEM/[A-Z0-9/\-]+)', bid_text, re.IGNORECASE)
    if regex_match:
        return regex_match.group(1).strip()

    # 3. Try XPath as fallback
    try:
        bid_no_element = bid.find_element(By.XPATH, ".//*[contains(translate(text(),'abcdefghijklmnopqrstuvwxyz','ABCDEFGHIJKLMNOPQRSTUVWXYZ'),'BID NO')]")
        bid_no_text = bid_no_element.text
        bid_match = re.search(r'GEM/[A-Z0-9/\-]+', bid_no_text)
        if bid_match:
            return bid_match.group(0).strip()
    except Exception as e:
        print("[DEBUG] XPath fallback failed:", e)

    # 4. Final fallback
    fallback_match = re.search(r'GEM/[A-Z0-9/\-]+', bid_text)
    if fallback_match:
        return fallback_match.group(0).strip()

    print("[WARNING] Could not extract bid number.")
    return "Not Found"

try:
    driver.get(URL)
    time.sleep(1)

    # Search keyword
    search_input = driver.find_element(By.ID, "searchBid")
    search_input.clear()
    search_input.send_keys(SEARCH_KEYWORD)

    search_button = driver.find_element(By.ID, "searchBidRA")
    search_button.click()
    WebDriverWait(driver, 10).until(
    EC.invisibility_of_element_located((By.XPATH, "//div[contains(@class, 'card')]"))
)
    WebDriverWait(driver, 10).until(
    EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'card')]"))
)
    # time.sleep(1)
#     WebDriverWait(driver, 10).until(
#     EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'card')]"))
# )


    scraped_data = []

    while True:
        bids = driver.find_elements(By.XPATH, "//div[contains(@class, 'card')]")
        print(f"Found {len(bids)} bid(s) on this page.")

        if len(bids) == 0:
            print("No bids found on this page. Exiting...")
            break

        for index, bid in enumerate(bids):
            try:
                bid_text = bid.text.strip()
                print(f"\n[DEBUG] Bid Content:\n{bid_text}\n")

                bid_number = extract_bid_number(bid, bid_text)
                items = extract_field(bid_text, "Items:", ["Quantity:", "Department", "\n"])
                quantity = extract_field(bid_text, "Quantity:", ["Department", "Start Date:", "\n"])
                department = extract_department_from_html(bid)
                start_date = extract_field(bid_text, "Start Date:", ["End Date:", "\n"])
                end_date = extract_field(bid_text, "End Date:", ["\n"])

                try:
                    link = bid.find_element(By.TAG_NAME, "a").get_attribute("href")
                except:
                    link = "Not Available"

                scraped_data.append({
                    'Bid Number': bid_number,
                    'Items': items,
                    'Quantity': quantity,
                    'Department': department,
                    'Start Date': start_date,
                    'End Date': end_date,
                    'Downloadable File URL': link
                })

            except Exception as e:
                print(f"[ERROR] Parsing bid {index + 1}: {e}")
                continue

        try:
            next_button = driver.find_element(By.CSS_SELECTOR, 'a.page-link.next')
            if "disabled" in next_button.get_attribute("class"):
                print("Reached the last page. Exiting...")
                break
            else:
                next_button.click()
                # time.sleep(1)
                WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'card')]"))
)

        except:
            print("Next button not found. Assuming last page. Exiting...")
            break

    # Save to CSV
    keys = ['Bid Number', 'Items', 'Quantity', 'Department', 'Start Date', 'End Date', 'Downloadable File URL']
    if scraped_data:
        with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(scraped_data)

        print(f"\n✅ Saved {len(scraped_data)} bids to {OUTPUT_CSV}")
    else:
        print("No data to save to CSV.")

    # input("\nPress ENTER to close the browser...")

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    driver.quit()
