import os
import time
import csv
import tempfile
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ====== SETTINGS ======
GECKODRIVER_PATH = '/usr/local/bin/geckodriver'
SEARCH_KEYWORD = 'blockchain'
OUTPUT_CSV = os.path.join(os.getcwd(), 'bid_results.csv')
URL = 'https://bidplus.gem.gov.in/all-bids'

# ====== Create TEMP DIR for downloads ======
temp_dir = tempfile.mkdtemp()
print(f"Temporary download folder: {temp_dir}")

# ====== Setup Firefox profile for auto-download ======
profile = webdriver.FirefoxProfile()
profile.set_preference("browser.download.folderList", 2)
profile.set_preference("browser.download.dir", temp_dir)
profile.set_preference("browser.helperApps.neverAsk.saveToDisk", 
    "application/pdf,application/zip,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain")
profile.set_preference("pdfjs.disabled", True)

firefox_options = Options()
firefox_options.add_argument("--start-maximized")
firefox_options.profile = profile

service = Service(GECKODRIVER_PATH)
driver = webdriver.Firefox(service=service, options=firefox_options)

def extract_field(text, label, stop_labels):
    try:
        start = text.index(label) + len(label)
        end = min([text.index(stop, start) for stop in stop_labels if stop in text[start:]] + [len(text)])
        return text[start:end].strip()
    except:
        return "Not Found"

try:
    driver.get(URL)
    time.sleep(2)

    # Search for the keyword
    search_input = driver.find_element(By.ID, "searchBid")
    search_input.clear()
    search_input.send_keys(SEARCH_KEYWORD)

    search_button = driver.find_element(By.ID, "searchBidRA")
    search_button.click()
    time.sleep(3)

    scraped_data = []

    while True:
        bids = driver.find_elements(By.XPATH, "//div[contains(@class, 'card')]")
        print(f"Found {len(bids)} bid(s) on this page.")

        if len(bids) == 0:
            print("No bids found. Exiting...")
            break

        for index, bid in enumerate(bids):
            try:
                bid_number_elem = WebDriverWait(bid, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "bid_no_hover"))
                )
                bid_number = bid_number_elem.text.strip()
                print(f"\n[INFO] Opening bid: {bid_number}")
                bid_number_elem.click()
                time.sleep(3)

                # Close modal if it pops up
                try:
                    modal_close = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'modal')]//button[contains(text(),'Close')]"))
                    )
                    modal_close.click()
                    print("[INFO] Closed modal popup.")
                    time.sleep(1)
                except:
                    pass

                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "BidDetailForm"))
                )

                content = driver.find_element(By.ID, "BidDetailForm").text

                try:
                    links = driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf') or contains(@href, '.zip') or contains(@href, '.doc') or contains(@href, '.txt') or contains(@href, '.xls') or contains(@href, '.xlsx')]")
                    link_url = links[0].get_attribute("href") if links else "Not Available"
                except:
                    link_url = "Not Available"

                scraped_data.append({
                    'Bid Number': bid_number,
                    'Items': items,
                    'Quantity': quantity,
                    'Department': department,
                    'Start Date': start_date,
                    'End Date': end_date,
                    'Downloadable File URL': link_url
                })

                driver.back()
                time.sleep(2)

            except Exception as e:
                print(f"[ERROR] Failed parsing bid {index + 1}: {e}")
                try:
                    driver.back()
                    time.sleep(2)
                except:
                    pass
                continue

        try:
            next_button = driver.find_element(By.CSS_SELECTOR, 'a.page-link.next')
            if "disabled" in next_button.get_attribute("class"):
                print("Reached the last page.")
                break
            else:
                next_button.click()
                time.sleep(5)
        except:
            print("Next button not found. Assuming last page.")
            break



except Exception as e:
    print(f"[FATAL ERROR] {e}")

finally:
    driver.quit()
