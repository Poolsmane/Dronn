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
SEARCH_KEYWORD = 'lms'
OUTPUT_CSV = 'bid_results.csv'
URL = 'https://bidplus.gem.gov.in/all-bids'

# ====== Create TEMP DIR for downloads ======
temp_dir = tempfile.mkdtemp()
print(f"Temporary download folder: {temp_dir}")

# ====== Setup Firefox profile for auto-download ======
profile = webdriver.FirefoxProfile()
profile.set_preference("browser.download.folderList", 2)
profile.set_preference("browser.download.dir", temp_dir)
profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/pdf")
profile.set_preference("pdfjs.disabled", True)

firefox_options = Options()
firefox_options.add_argument("--start-maximized")
firefox_options.profile = profile

service = Service(GECKODRIVER_PATH)
driver = webdriver.Firefox(service=service, options=firefox_options)

try:
    # 1. Open GeM bid page
    driver.get(URL)

    # 2. Wait and search for the keyword
    time.sleep(2)
    search_input = driver.find_element(By.ID, "searchBid")
    search_input.clear()
    search_input.send_keys(SEARCH_KEYWORD)

    search_button = driver.find_element(By.ID, "searchBidRA")
    search_button.click()

    # 3. Wait for search results
    time.sleep(3)

    scraped_data = []
    while True:  # Loop through all pages
        bids = driver.find_elements(By.XPATH, "//div[contains(@class, 'card')]")
        print(f"Found {len(bids)} bid(s) on this page.")

        if len(bids) == 0:
            print("No bids found on this page. Exiting...")
            break

        for index, bid in enumerate(bids):
            try:
                # Find the bid number link (bid_no_hover)
                bid_number_element = WebDriverWait(bid, 10).until(
                    EC.visibility_of_element_located((By.CLASS_NAME, "bid_no_hover"))
                )
                bid_number = bid_number_element.text.strip()

                print(f"Bid Number: {bid_number}")
                bid_number_element.click()
                time.sleep(3)

                # Wait for bid details page to load, explicitly wait for the "Bid Details" section
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "otherDetails"))
                )

                # Explicitly find the "Download" link in the bid details
                download_link = driver.find_element(By.XPATH, "//div[@class='otherDetails']//a")
                download_href = download_link.get_attribute("href")
                
                # Click on the download link to download the PDF
                download_link.click()
                time.sleep(2)

                scraped_data.append({
                    'Bid Number': bid_number,
                    'Downloaded PDF URL': download_href,
                    'Downloaded PDF Path': temp_dir
                })

                # Go back to the previous page to continue scraping
                driver.back()
                time.sleep(2)

            except Exception as e:
                print(f"Error parsing bid {index + 1}: {e}")
                driver.back()
                time.sleep(2)

        # 4. Check if 'Next' button is available and not disabled
        try:
            next_button = driver.find_element(By.CSS_SELECTOR, 'a.page-link.next')
            if "disabled" in next_button.get_attribute("class"):
                print("Reached the last page. Exiting...")
                break
            else:
                next_button.click()
                time.sleep(5)
        except Exception as e:
            print("Next button not found. Assuming last page. Exiting...")
            break

    # 5. Save results to CSV
    if scraped_data:
        keys = scraped_data[0].keys()
        with open(OUTPUT_CSV, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(scraped_data)
        print(f"Saved {len(scraped_data)} bids to {OUTPUT_CSV}")
    else:
        print("No bids found.")

    input("\nPress ENTER to close the browser...")

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    driver.quit()



# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC

# # Initialize the driver
# driver = webdriver.Firefox()

# # Navigate to the page
# driver.get("https://bidplus.gem.gov.in/all-bids")

# # Wait until the element with class 'bid_no' is present in the DOM
# try:
#     # Use WebDriverWait to wait for the element to be visible
#     bid_no_element = WebDriverWait(driver, 10).until(
#         EC.visibility_of_element_located((By.CSS_SELECTOR, ".bid_no"))
#     )
#     # Now interact with the element (e.g., print its text or click it)
#     print(bid_no_element.text)
# except Exception as e:
#     print("Element not found or an error occurred:", e)

# # Close the driver after interaction
# driver.quit()
