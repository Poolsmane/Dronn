import os
import pdfplumber
import requests
import string
from pathlib import Path
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import subprocess
from flask import Flask, render_template, request, jsonify, send_from_directory,session
import pandas as pd
import subprocess
import time
import threading
app = Flask(__name__)
DOWNLOAD_FOLDER = os.getcwd()
import move_file
from move_file import run_task
from rag_agent import process_with_rag_agent 

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
        return jsonify({"success": True, "answer": answer})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500



@app.route('/query', methods=['POST'])
def query_document():
    question = request.form.get('question')
    file_text = session.get('file_text')

    if not file_text:
        return jsonify({"error": "No file processed yet."}), 400

    # Process the question (replace this with your AI logic)
    answer = process_question(file_text, question)

    return jsonify({"answer": answer})

@app.route('/scrape', methods=['POST'])
def scrape():
    keyword = request.form.get('keyword')

    # 1. Run scraper
    try:
        result = subprocess.run(['python3', 'scrap.py', keyword], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        return f"Scraper error: {e.stderr}", 500

    # 2. Run remove.py immediately after
    try:
        filter_result = subprocess.run(['python3', 'remove_rows.py'], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
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
        return jsonify({"error": str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    try:
        return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)
    except FileNotFoundError:
        return "File not found", 404

ALL_TEXT_CACHE = ""  # optional: to speed things up
 # Track whether a file has been successfully processed




if __name__ == '__main__':
    thread=threading.Thread(target=move_file.run_task)
    thread.daemon=True
    thread.start()
    app.run(host='0.0.0.0', port=8080, debug=True)
    