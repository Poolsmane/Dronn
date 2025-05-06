import os
import subprocess
from flask import Flask, render_template, request, jsonify, send_from_directory
import pandas as pd
import subprocess
import time
import threading
app = Flask(__name__)
DOWNLOAD_FOLDER = os.getcwd()
import move_file
from move_file import run_task

# import download_file

@app.route('/')
def index():
    return render_template('index.html')


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

if __name__ == '__main__':
    thread=threading.Thread(target=move_file.run_task)
    thread.daemon=True
    thread.start()
    app.run(host='0.0.0.0', port=8080, debug=True)
    