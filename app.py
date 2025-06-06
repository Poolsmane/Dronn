import os
import pdfplumber
import requests
import string
from pathlib import Path
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import subprocess
from flask import Flask, render_template, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
import pandas as pd
import subprocess
import time
import move_file
from move_file import run_task
import threading
app = Flask(__name__)
DOWNLOAD_FOLDER = os.getcwd()
import rag_agent
from rag_agent import monitor_and_run_rag
from rag_agent import process_with_langchain_agent 
import csv
from io import BytesIO
CORS(app)
from io import BytesIO
from urllib.parse import urlparse



file_path1 = 'latest_moved_path.txt'

# Overwrite the file with an empty string to clear its contents
with open(file_path1, mode='w', encoding='utf-8') as outfile:
    outfile.write('')


# print(f"Cleared all data from {file_path1}, header preserved.")

file_path = 'filtered_bid_results.csv'  # Replace with your actual file path

# Step 1: Read the header (column names)
with open(file_path, mode='r', newline='', encoding='utf-8') as infile:
    reader = csv.reader(infile)
    headers = next(reader)  # Get the first row (header)

# Step 2: Write only the header back to the file (clear the rest)
with open(file_path, mode='w', newline='', encoding='utf-8') as outfile:
    writer = csv.writer(outfile)
    writer.writerow(headers)

print(f"Cleared all data from {file_path}, header preserved.")
def clear_csv_file(filepath):
    try:
        with open(filepath, mode='r', newline='', encoding='utf-8') as infile:
            reader = csv.reader(infile)
            headers = next(reader)

        with open(filepath, mode='w', newline='', encoding='utf-8') as outfile:
            writer = csv.writer(outfile)
            writer.writerow(headers)

        print(f"Cleared all data from {filepath}, header preserved.")
    except Exception as e:
        print(f"Failed to clear {filepath}: {e}")

os.environ["TOKENIZERS_PARALLELISM"] = "false"
embedder = SentenceTransformer('all-MiniLM-L6-v2')
ALL_TEXT_CACHE = ""  # cache for all text to avoid re-processing
from rag_agent import (
    extract_text_and_links,
    download_linked_files,
    # find_relevant_chunks,
    handle_pdf_and_links,
    # ask_ollama
)

@app.route('/')
def index():
    return render_template('index.html')

    
@app.route('/favicon.ico')
def favicon():
    return '', 204  # No Content

 # Import the function you created


#download without opening a new tab

@app.route('/download')
def download():
    pdf_url = request.args.get('url')
    if not pdf_url:
        return "Missing URL", 400

    # Directory to save downloaded files
    save_dir = '/home/kartikeyapatel/Videos/gem/extracted_data'
    os.makedirs(save_dir, exist_ok=True)

    # Extract filename or fallback
    filename = os.path.basename(urlparse(pdf_url).path) or 'downloaded_file.pdf'
    filepath = os.path.join(save_dir, filename)

    try:
        print(f"Downloading from: {pdf_url}")
        print(f"Saving to: {filepath}")

        response = requests.get(pdf_url, stream=True, timeout=20)
        response.raise_for_status()

        # Optional: check content-type if you want, but without headers no need to enforce
        # content_type = response.headers.get("Content-Type", "")
        # if "application/pdf" not in content_type:
        #     return f"Expected PDF, but got: {content_type}", 400

        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print("✅ Download complete.")

        return send_file(filepath,
                         as_attachment=True,
                         download_name=filename,
                         mimetype="application/pdf")

    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        return f"Request error: {e}", 500
    except Exception as e:
        print(f"❌ General Exception: {e}")
        return f"Server error: {e}", 500


@app.route('/ask_question', methods=['POST'])
def ask_question():
    bid="GEM/2025/B/6055240"
    data = request.get_json()
    question = data.get("question")
    # context = data.get("context")

    if not question:
        return jsonify({"success": False, "error": "No question provided."}), 400
    # if not context:
    #     return jsonify({"success": False, "error": "No context provided."}), 400

    try:
        # Call the RAG processing function with question and context
        answer = process_with_langchain_agent(question)
        print("success")
        return jsonify({"success": True, "answer": answer})
    except Exception as e:
        print(e)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/status.txt")
def get_status():
    return send_file("status.txt")
    

def download_files(url, save_dir):
    os.makedirs(save_dir, exist_ok=True)
    print(f"📥 Downloading file from URL: {url}")

    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "*/*",
        }
        response = requests.get(url, headers=headers, stream=True, timeout=20, allow_redirects=True)
        print(f"🔁 Status Code: {response.status_code}")
        content_type = response.headers.get("Content-Type", "")
        print(f"🧾 Content-Type: {content_type}")

        if "application/pdf" not in content_type:
            # Not a PDF; save HTML to debug
            debug_path = os.path.join(save_dir, "debug_response.html")
            with open(debug_path, "wb") as f:
                f.write(response.content)
            return None, f"⚠️ Not a PDF. Saved debug HTML to {debug_path}"

        filename = os.path.basename(urlparse(url).path)
        if not filename.endswith(".pdf"):
            filename += ".pdf"
        filepath = os.path.join(save_dir, filename)

        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        print(f"✅ Saved to: {filepath}")
        return filename, None

    except Exception as e:
        return None, f"❌ Exception: {str(e)}"

@app.route('/scrape', methods=['POST'])
def scrape():
    keywords_input = request.form.get('keyword', '')
    clear_csv_file('bid_results.csv')
    clear_csv_file('filtered_bid_results.csv')
    
    if not keywords_input.strip():
        return "No keywords provided", 400

    # Split the keywords by comma and strip whitespace
    keywords = tuple(kw.strip() for kw in keywords_input.split(',') if kw.strip())

    # 1. Run scrap.py for each keyword
    for keyword in keywords:
        try:
            print(f"Scraping for: {keyword}")
            result = subprocess.run(['python3', 'scrap.py', keyword], check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            print(f"Error scraping '{keyword}': {e}")
            return f"Scraper error for '{keyword}': {e.stderr}", 500

    # 2. Run remove_rows.py after all keywords are scraped
    try:
        print("Running row filter...")
        filter_result = subprocess.run(['python3', 'remove_rows.py'], check=True, capture_output=True, text=True)
        clear_csv_file('bid_results.csv')
    except subprocess.CalledProcessError as e:
        print(f"Error filtering rows: {e}")
        return f"Filter error: {e.stderr}", 500

    # 3. Optional delay for write buffer
    time.sleep(0.5)

    # 4. Read filtered_bid_results.csv and download all files from "Downloadable File URL"
    filtered_csv = 'filtered_bid_results.csv'
    save_dir = '/home/kartikeyapatel/Videos/gem/first_extracted_data'

    # Read all rows
    with open(filtered_csv, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    # Add a new column if not present
    if 'Downloaded Filename' not in fieldnames:
        fieldnames.append('Downloaded Filename')

    # Download files and add filename info
    for row in rows:
        url = row.get('Downloadable File URL', '').strip()
        if url:
            print(f"Downloading file from URL: {url}")
            filename, error = download_files(url, save_dir)
            if filename:
                row['Downloaded Filename'] = filename
            else:
                row['Downloaded Filename'] = f"ERROR: {error}"
        else:
            row['Downloaded Filename'] = 'No URL'

    # Write back the CSV with new column
    with open(filtered_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return f"Scraping completed for: {', '.join(keywords)} and files downloaded.", 200



from flask import request, jsonify
import csv
import os





@app.route('/data')
def data():
    try:
        df = pd.read_csv("filtered_bid_results.csv")
        df.fillna("Not Available", inplace=True)
        return jsonify({"data": df.to_dict(orient="records")})
    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    try:
        return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)
    except FileNotFoundError:
        print("Error")
        return "File not found", 404


#added for the context button
@app.route("/context_data")
def get_context_data():
    bid = request.args.get("bid")
    if not bid:
        return jsonify({"status": "error", "message": "Missing 'bid' parameter"}), 400

    if not os.path.exists("static/final_bid_results.csv"):
        return jsonify({"status": "error", "message": "CSV file not found"}), 500

    try:
        with open("static/final_bid_results.csv", newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row["Bid Number"].strip().lower() == bid.strip().lower():
                    return jsonify({"status": "success", "row": row})
    except Exception as e:
        print(f"Error reading CSV or processing bid: {e}")  # 👈 This will show up in your Flask logs
        return jsonify({"status": "error", "message": str(e)}), 500

    return jsonify({"status": "not found"})

ALL_TEXT_CACHE = ""  # optional: to speed things up
 # Track whether a file has been successfully processed


def safe_thread(target_func):
    def wrapper():
        try:
            target_func()
        except Exception as e:
            print(f"Exception in thread {target_func.__name__}: {e}")
    return wrapper

if __name__ == '__main__':
    thread = threading.Thread(target=safe_thread(move_file.run_task))
    # thread.daemon = True
    thread1 = threading.Thread(target=safe_thread(monitor_and_run_rag))
    # thread1.daemon = True
    thread.start()
    thread1.start()
    app.run(host='0.0.0.0', port=8080, debug=True)
    print("Flask App exitec")
    