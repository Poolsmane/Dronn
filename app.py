import os
import pdfplumber
import requests
import string
from pathlib import Path
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import subprocess
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import pandas as pd
import subprocess
import time
import threading
app = Flask(__name__)
DOWNLOAD_FOLDER = os.getcwd()
import move_file
import rag_agent
from move_file import run_task
from rag_agent import monitor_and_run_rag
from rag_agent import process_with_rag_agent 
import csv
CORS(app)
file_path1 = '/home/kartikeyapatel/Videos/gem/latest_moved_path.txt'  # Replace with your actual text file path

# Step 1: Read the first line (header or title)
with open(file_path1, mode='r', encoding='utf-8') as infile:
    first_line = infile.readline()

# Step 2: Write only the first line back to the file (clear the rest)
with open(file_path1, mode='w', encoding='utf-8') as outfile:
    outfile.write(first_line)

print(f"Cleared all data from {file_path1}, header preserved.")

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

os.environ["TOKENIZERS_PARALLELISM"] = "false"
embedder = SentenceTransformer('all-MiniLM-L6-v2')
ALL_TEXT_CACHE = ""  # cache for all text to avoid re-processing
from rag_agent import (
    extract_text_and_links,
    download_linked_files,
    find_relevant_chunks,
    ask_ollama
)


@app.route('/')
def index():
    return render_template('index.html')

 # Import the function you created

@app.route('/ask_question', methods=['POST'])
def ask_question():
    data = request.get_json()
    question = data.get("question")
    # context = data.get("context")

    if not question:
        return jsonify({"success": False, "error": "No question provided."}), 400
    # if not context:
    #     return jsonify({"success": False, "error": "No context provided."}), 400

    try:
        # Call the RAG processing function with question and context
        answer = process_with_rag_agent(question)
        print("success")
        return jsonify({"success": True, "answer": answer})
    except Exception as e:
        print(e)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/scrape', methods=['POST'])
def scrape():
    keyword = request.form.get('keyword')

    # 1. Run scraper
    try:
        result = subprocess.run(['python3', 'scrap.py', keyword], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(e)
        return f"Scraper error: {e.stderr}", 500

    # 2. Run remove.py immediately after
    try:
        filter_result = subprocess.run(['python3', 'remove_rows.py'], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(e)
        return f"Filter error: {e.stderr}", 500

    # 3. Wait a bit to ensure file write completion (optional but helps on some systems)
    time.sleep(0.5)

    return 'Scraping and filtering completed successfully.', 200



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
    