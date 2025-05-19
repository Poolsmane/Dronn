import fitz  # PyMuPDF to extract text
import subprocess
import json
import csv
import os

def extract_text_from_pdf(pdf_path):
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text()
    return text

def query_deepseek_r1(text, pdf_name):
    # Craft the prompt to instruct DeepSeek R1 to extract the fields in JSON
    prompt = f"""
You are an AI assistant specialized in reading RFP documents.
Given the following RFP text, extract and return the data as a JSON object with keys:
- bid_no
- start_date
- end_date
- emd_amount
- eligibility_criteria
- documents_required
- contact_person_details
- scope_of_work
- type_of_work
- type_of_manpower_required
- technical_qualification
- pre_qualification_criteria
- hardware_requirements

Please only return valid JSON without any extra commentary.

RFP Text:
\"\"\"{text}\"\"\"
"""

    # Call Ollama CLI to query DeepSeek R1 Complete model
    # Using subprocess; adjust if you have a Python API
    result = subprocess.run(
        ["ollama", "query", "deepseek-r1", "--prompt", prompt, "--json"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Ollama query failed: {result.stderr}")

    # The output should be a JSON string representing the extracted fields
    response_json = result.stdout.strip()
    try:
        data = json.loads(response_json)
    except json.JSONDecodeError:
        raise ValueError("Failed to decode JSON from DeepSeek R1 output")
    return data

def save_to_csv(data_dict, pdf_path, csv_path="rfp_extracted_data.csv"):
    file_exists = os.path.isfile(csv_path)
    with open(csv_path, 'a', newline='', encoding='utf-8') as f:
        fieldnames = ["pdf_file_name"] + list(data_dict.keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({"pdf_file_name": os.path.basename(pdf_path), **data_dict})

def process_pdf(pdf_path):
    print(f"Processing {pdf_path} ...")
    text = extract_text_from_pdf(pdf_path)

    print("Querying DeepSeek R1 model...")
    data = query_deepseek_r1(text, os.path.basename(pdf_path))

    print("Extracted data:", data)
    save_to_csv(data, pdf_path)
    print("Extraction complete and saved to CSV.")

if __name__ == "__main__":
    pdf_path = input("Enter the full path of the PDF: ").strip()
    process_pdf(pdf_path)
