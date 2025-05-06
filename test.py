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

service = Service(GECKODRIVER_PATH)
driver = webdriver.Firefox(service=service, options=firefox_options)

try:
    driver.get(URL)

    # Search keyword
    time.sleep(2)
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
            print("No bids found on this page. Exiting...")
            break

        for index, bid in enumerate(bids):
            try:
                bid_number_elem = WebDriverWait(bid, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "bid_no_hover"))
                )
                bid_number = bid_number_elem.text.strip()
                print(f"\n[INFO] Clicking on Bid Number: {bid_number}")
                bid_number_elem.click()
                time.sleep(3)

                # Close modal popup if present
                try:
                    modal_close = driver.find_element(By.XPATH, "//div[contains(@class, 'modal')]//button[contains(text(),'Close')]")
                    modal_close.click()
                    print("[INFO] Closed modal popup.")
                    time.sleep(1)
                except:
                    pass

                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "BidDetailForm"))
                )

                content = driver.find_element(By.ID, "BidDetailForm").text

                # Extract basic fields using string parsing
                def extract_field(text, label, stop_labels):
                    try:
                        start = text.index(label) + len(label)
                        end = min([text.index(stop, start) for stop in stop_labels if stop in text[start:]] + [len(text)])
                        return text[start:end].strip()
                    except:
                        return "Not Found"

                items = extract_field(content, "Items:", ["Quantity:", "Department"])
                quantity = extract_field(content, "Quantity:", ["Department", "Start Date:", "StartDate:"])
                department = extract_field(content, "Department Name And Address:", ["Start Date:", "StartDate:"])
                start_date = extract_field(content, "Start Date:", ["End Date:"])
                end_date = extract_field(content, "End Date:", ["Corrigendum", "Representation", "\n"])

                # Try to find downloadable links
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
                print(f"[ERROR] Parsing bid {index + 1}: {e}")
                print(f"[DEBUG] Bid Content:\n{bid.text}\n")
                try:
                    driver.back()
                    time.sleep(2)
                except:
                    pass

        try:
            next_button = driver.find_element(By.CSS_SELECTOR, 'a.page-link.next')
            if "disabled" in next_button.get_attribute("class"):
                print("Reached the last page. Exiting...")
                break
            else:
                next_button.click()
                time.sleep(5)
        except:
            print("Next button not found. Assuming last page. Exiting...")
            break

    # Save CSV
    keys = ['Bid Number', 'Items', 'Quantity', 'Department', 'Start Date', 'End Date', 'Downloadable File URL']
    with open(OUTPUT_CSV, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(scraped_data)

    print(f"\n✅ Saved {len(scraped_data)} bids to {OUTPUT_CSV}")
    input("\nPress ENTER to close the browser...")

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    driver.quit()
