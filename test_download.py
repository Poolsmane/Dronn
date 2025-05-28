# import requests

# url = "https://bidplus.gem.gov.in/showbidDocument/7865081"
# response = requests.get(url)

# with open("downloads/file.pdf", "wb") as f:
#     f.write(response.content)




# downloader.py
import requests
import os
from urllib.parse import urlparse

def download_file(url, save_dir='/home/kartikeyapatel/Videos/gem/extracted_data'):
    # Ensure save directory exists
    os.makedirs(save_dir, exist_ok=True)

    # Extract filename from URL
    filename = os.path.basename(urlparse(url).path)
    if not filename:
        filename = 'downloaded_file'

    filepath = os.path.join(save_dir, filename)

    print(f"Downloading from: {url}")
    print(f"Saving to: {filepath}")

    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print("✅ Download complete.")
    except requests.exceptions.RequestException as e:
        print(f"❌ Download failed: {e}")

if __name__ == '__main__':
    url = input("Enter the file URL to download: ").strip()
    download_file(url)
