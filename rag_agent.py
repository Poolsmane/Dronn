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

# Initialize SentenceTransformer model
embedder = SentenceTransformer('all-MiniLM-L6-v2')

# Function to extract text and links from PDF
def extract_text_and_links(pdf_path):
    text_content = ""
    links = set()

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                print(f"Reading page {i + 1}/{len(pdf.pages)}")
                page_text = page.extract_text()
                if page_text:
                    text_content += page_text + "\n"

                if page.annots:
                    for annot in page.annots:
                        uri = annot.get("uri")
                        if uri and uri.startswith("http"):
                            links.add(uri)
    except Exception as e:
        print(f"❌ Failed to read {pdf_path}: {e}")

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
def find_relevant_chunks(text, query, chunk_size=700, overlap=200, top_k=3):
    try:
        chunks = []
        for i in range(0, len(text), chunk_size - overlap):
            chunk = text[i:i + chunk_size]
            if len(chunk.strip()) > 20:
                chunks.append(chunk)

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
        return f"❌ Error calling Ollama subprocess: {str(e)}"
    except Exception as e:
        return f"❌ Error while communicating with Ollama: {str(e)}"

# Function to send a question to the API for an answer
def ask_question_via_api(question, context):
    api_url = "http://192.168.0.85:8080/ask_question"  # Replace with actual API URL
    payload = {
        "question": question,
        "context": context
    }
    try:
        response = requests.post(api_url, json=payload)
        if response.status_code == 200:
            return response.json().get("answer", "❌ No answer found.")
        else:
            return f"❌ Error: Unable to get answer from API. Status code: {response.status_code}"
    except Exception as e:
        return f"❌ Error while making API request: {str(e)}"

# Function to monitor latest_moved_file.txt and restart RAG agent if it changes
def monitor_and_run_rag(poll_interval=3):
    last_pdf_path = None
    last_all_text = None

    while True:
        if not os.path.exists("latest_moved_path.txt"):
            print("⚠️ latest_moved_path.txt not found. Waiting...")
            time.sleep(poll_interval)
            continue

        with open("latest_moved_path.txt", "r") as f:
            current_pdf_path = f.read().strip()

        if current_pdf_path != last_pdf_path:
            print(f"\n🔄 Detected new file: {current_pdf_path}")
            if not os.path.exists(current_pdf_path):
                print(f"❌ File not found: {current_pdf_path}")
                time.sleep(poll_interval)
                continue

            try:
                text, links = extract_text_and_links(current_pdf_path)
                print(f"🔍 Extracted main PDF text length: {len(text)}")
                all_text = text

                if links:
                    downloaded_files = download_linked_files(links, download_dir="linked_pdfs")
                    for fpath in downloaded_files:
                        if fpath.endswith(".pdf") and os.path.exists(fpath):
                            file_text, _ = extract_text_and_links(fpath)
                            print(f"📄 Extracted linked file {fpath} text length: {len(file_text)}")
                            all_text += "\n\n" + file_text
                else:
                    print("ℹ️ No links found in main PDF.")

                if not all_text.strip():
                    print("⚠️ No valid content found in new PDF. Skipping...")
                    time.sleep(poll_interval)
                    continue

                # Only update if everything is successful
                last_pdf_path = current_pdf_path
                last_all_text = all_text
                print("\n✅ Ready to answer questions from the new document.")

            except Exception as e:
                print(f"❌ Error processing PDF: {e}")
                time.sleep(poll_interval)
                continue

        # Start user Q&A
        print("\n🧠 You can now ask questions. Type 'exit' to stop.")
        while True:
        #     user_question = input("\n❓ Ask your question (or type 'exit'): ").strip()
        #     if user_question.lower() in ['exit', 'quit']:
        #         print("👋 Session ended. Waiting for file change...")
        #         break

            # Check if file changed mid-session
            with open("latest_moved_path.txt", "r") as f:
                check_pdf_path = f.read().strip()
            if check_pdf_path != last_pdf_path:
                print("\n⚠️ File changed during conversation. Restarting session...")
                break



# Function for API-based question answering using RAG
def process_with_rag_agent(question):
    try:
        context="The answer from the read rfp pdf is:"
        chunks = find_relevant_chunks(question,context)
        if isinstance(chunks, str) and chunks.startswith("❌"):
            return chunks
        prompt = f"""You are a highly accurate RAG agent helping analyze RFP documents. 
Answer the question strictly based **only** on the given context from the documents (including linked files). 
Do not add any information that is not present in the context. 
If the answer is not present, say "The document does not contain this information."

Respond clearly and concisely, in bullet points if applicable.

---

Context:
{context}

---

Question:
{question}
"""
        return ask_ollama(prompt)  # Or route to API if needed
    except Exception as e:
        return f"❌ Error in process_with_rag_agent: {str(e)}"


# Run the dynamic watcher if script is executed
if __name__ == "__main__":
    monitor_and_run_rag()
