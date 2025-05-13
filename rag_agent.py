import os
import time
import string
import requests
import subprocess
import pdfplumber
from pathlib import Path
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from pdfminer.pdfparser import PDFSyntaxError
import pytesseract
from pdf2image import convert_from_path
from fpdf import FPDF
import re

# Initialize SentenceTransformer model
embedder = SentenceTransformer('all-MiniLM-L6-v2')
all_text_final=""
# Function to extract text and links from PDF
def extract_text_and_links(pdf_path):
    text_content = ""
    links = set()

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                print(f"📄 Reading page {i + 1}/{len(pdf.pages)}")
                
                # Step 1: Extract regular text
                page_text = page.extract_text()
                if page_text:
                    text_content += page_text + "\n"
                else:
                    print(f"⚠️ No text found on page {i + 1}, using OCR fallback...")
                    image = convert_from_path(pdf_path, first_page=i+1, last_page=i+1)[0]
                    custom_oem_psm_config = r'--oem 3 --psm 6'
                    ocr_text = pytesseract.image_to_string(image, config=custom_oem_psm_config)
                    text_content += ocr_text + "\n"
                
                # Step 2: Extract structured tables
                tables = page.extract_tables()
                for table in tables:
                    text_content += "\n[Table]\n"
                    for row in table:
                        row_text = ' | '.join([cell.strip() if cell else '' for cell in row])
                        text_content += row_text + "\n"

                # Step 3: Extract hyperlinks
                try:
                    if page.annots:
                        for annot in page.annots:
                            uri = annot.get("uri")
                            if uri and uri.startswith("http"):
                                links.add(uri)
                except Exception:
                    pass

    except Exception as e:
        print(f"❌ Failed to read {pdf_path}: {e}")
        return "", []

    return text_content.strip(), list(links)




# Function to generate filenames for linked files
def generate_filenames(n):
    alphabet = string.ascii_lowercase
    result = []
    i = 0
    while len(result) < n:
        name = ''
        temp = i
        while True:
            name = alphabet[temp % 26] + name
            temp = temp // 26 - 1
            if temp < 0:
                break
        result.append(f"{name}.pdf")
        i += 1
    return result

# Function to download files linked in the PDF
def download_linked_files(links, download_dir):
    os.makedirs(download_dir, exist_ok=True)
    downloaded_files = []

    print(f"\nFound {len(links)} links. Attempting to download files into: {download_dir}")
    filenames = generate_filenames(len(links))

    for idx, link in enumerate(links):
        try:
            response = requests.get(link, timeout=15, verify=False)
            if response.status_code == 200:
                filename = filenames[idx]
                filepath = os.path.join(download_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(response.content)
                downloaded_files.append(filepath)
                print(f"✅ Downloaded: {filepath}")
            else:
                print(f"❌ Failed (status {response.status_code}): {link}")
        except Exception as e:
            print(f"❌ Error downloading {link}: {e}")
    return downloaded_files

# Function to find relevant chunks based on the query
def find_relevant_chunks(text, query, chunk_size=800, overlap=350, top_k=5):
    try:
        # Preprocess: Remove excessive whitespace
        text = ' '.join(text.split())

        if not text.strip():
            return "❌ No text found after preprocessing."

        # Split into overlapping chunks
        chunks = []
        for i in range(0, len(text), chunk_size - overlap):
            chunk = text[i:i + chunk_size].strip()
            if len(chunk) >= 50:  # Lowered from 20 to 50 to ensure richer chunks
                chunks.append(chunk)

        if not chunks:
            return "❌ No valid text chunks found for embedding."

        chunk_embeddings = embedder.encode(chunks, convert_to_numpy=True)
        query_embedding = embedder.encode([query], convert_to_numpy=True)

        index = faiss.IndexFlatL2(chunk_embeddings.shape[1])
        index.add(chunk_embeddings)
        distances, indices = index.search(query_embedding, top_k)

        return [chunks[i] for i in indices[0]]
    except Exception as e:
        return f"❌ Error while finding relevant chunks: {str(e)}"

# Function to interact with Ollama for prompt-based responses
def ask_ollama(prompt, model="deepseek-r1"):
    try:
        process = subprocess.Popen(
            ["ollama", "run", model],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, _ = process.communicate(input=prompt)
        return stdout.strip()
    except subprocess.CalledProcessError as e:
        print(e)
        return f"❌ Error calling Ollama subprocess: {str(e)}"
    except Exception as e:
        print(e)
        return f"❌ Error while communicating with Ollama: {str(e)}"


# Function to monitor latest_moved_file.txt and restart RAG agent if it changes

import threading

# Function to monitor file path changes and return a flag indicating the change
def monitor_and_run_rag(poll_interval=3):
    last_pdf_path = None
    while True:
        if not os.path.exists("latest_moved_path.txt"):
            print("⚠️ latest_moved_path.txt not found. Waiting...")
            time.sleep(poll_interval)
            continue

        with open("latest_moved_path.txt", "r") as f:
            current_pdf_path = f.read().strip()

        if current_pdf_path != last_pdf_path:
            print(f"\n🔄 Detected new file: {current_pdf_path}")
            last_pdf_path = current_pdf_path
            # Trigger the file processing and link downloading
            threading.Thread(target=handle_pdf_and_links, args=(current_pdf_path,)).start()

        time.sleep(poll_interval)

# New function to handle PDF processing, link downloading, and text aggregation
def handle_pdf_and_links(current_pdf_path):
    global all_text_final
    try:
        # Extract text from main PDF and links
        text, links = extract_text_and_links(current_pdf_path)
        print(f"🔍 Extracted main PDF text length: {len(text)}")
        print(f"✅ Raw extracted text (first 500 chars): {text[:500]}")
        all_text = text

        # If there are links in the PDF, download the files linked in the PDF
        if links:
            print(f"ℹ️ Found {len(links)} links in the PDF.")
            downloaded_files = download_linked_files(links, download_dir="linked_pdfs")
            for fpath in downloaded_files:
                if fpath.endswith(".pdf") and os.path.exists(fpath):
                    file_text, _ = extract_text_and_links(fpath)
                    print(f"📄 Extracted linked file {fpath} text length: {len(file_text)}")
                    all_text += "\n" + file_text
        else:
            print("ℹ️ No links found in main PDF.")

        # If no valid content found in the PDF, return None
        if not all_text.strip():
            print("⚠️ No valid content found in new PDF. Skipping...")
            return None

        print("\n✅ Ready to answer questions from the new document.")
        all_text_final = all_text

    except Exception as e:
        print(f"❌ Error processing PDF: {e}")


# Modify process_with_rag_agent to use the new function
def process_with_rag_agent(question):
    global all_text_final

    print(f"all text is:{all_text_final}")
    try:
        chunks = find_relevant_chunks(all_text_final, question)
        if isinstance(chunks, str) and chunks.startswith("❌"):
            return chunks

        context = "\n\n".join(chunks)
        prompt = (
    f"Give me a precise nswer with values from the documents."
    f"If the answer is not clearly in the context, respond with 'Not found in the document.'\n\n"
    f"Context:\n{context}\n\n"
    f"Question: {question}"
)
        return ask_ollama(prompt)
    except Exception as e:
        print(e)
        return f"❌ Error in process_with_rag_agent: {str(e)}"


# Run the dynamic watcher if script is executed
if __name__ == "__main__":
    monitor_and_run_rag()