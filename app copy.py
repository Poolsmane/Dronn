import os
import requests
import tempfile
from flask import Flask, render_template, jsonify, send_file
import pandas as pd
from flask import Flask, send_from_directory
app = Flask(__name__)

# Specify the directory you want the files to be saved in
# If you want the current working directory, you can use os.getcwd()
DOWNLOAD_FOLDER = os.getcwd()  # Current working directory (you can change this to any other directory)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data')
def data():
    df = pd.read_csv("filtered_bid_results.csv")
    df.fillna("Not Available", inplace=True)
    return jsonify({"data": df.to_dict(orient="records")})

@app.route('/download/<filename>')
def download_file(filename):
    # Return the file from the directory
    try:
        return send_from_directory(app.config['/home/kartikeyapatel/Videos/gem/extracted_data'], filename, as_attachment=True)
    except FileNotFoundError:
        return "File not found", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
