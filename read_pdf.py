import os
import re
import requests
import fitz  # PyMuPDF
import faiss
from pathlib import Path
from urllib.parse import unquote
from sentence_transformers import SentenceTransformer

# Load embedder globally for efficiency
embedder = SentenceTransformer("all-MiniLM-L6-v2")


def extract_text_and_links(pdf_path):
    """Extract full text and all links from a PDF file."""
    doc = fitz.open(pdf_path)
    full_text = ""
    links = set()

    for page in doc:
        full_text += page.get_text()
        for link in page.get_links():
            if link['uri']:
                links.add(link['uri'])

    doc.close()
    return full_text, list(links)


def download_linked_files(links, download_dir):
    """Download all files from extracted PDF links."""
    os.makedirs(download_dir, exist_ok=True)
    downloaded_files = []

    for url in links:
        try:
            filename = os.path.basename(unquote(url.split("?")[0]))
            file_path = os.path.join(download_dir, filename)

            if not os.path.exists(file_path):
                print(f"🌐 Downloading: {url}")
                r = requests.get(url, timeout=10)
                with open(file_path, 'wb') as f:
                    f.write(r.content)

            downloaded_files.append(file_path)

        except Exception as e:
            print(f"❌ Failed to download {url}: {e}")

    return downloaded_files


def smart_chunk_by_section(text):
    """Split document into logical sections based on headings."""
    pattern = r"(?=\n?[A-Z][A-Z\s]+\n)"
    chunks = re.split(pattern, text)
    return [chunk.strip() for chunk in chunks if len(chunk.strip()) > 30]


def enhance_query(query):
    """Enhance query to guide LLM towards detailed answers."""
    return f"{query}. Include all available details such as processor, RAM, SSD/HDD, operating system, brand, model, and other relevant specifications."


def find_semantically_relevant_chunks(text, query, top_k=3):
    """Find top-k relevant chunks from text using embeddings and FAISS."""
    chunks = smart_chunk_by_section(text)
    embeddings = embedder.encode(chunks, convert_to_numpy=True)
    enhanced_query = enhance_query(query)
    query_embedding = embedder.encode([enhanced_query], convert_to_numpy=True)

    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    distances, indices = index.search(query_embedding, top_k)

    return [chunks[i] for i in indices[0]]


def ask_ollama(prompt):
    """Send prompt to local LLaMA API and print response."""
    try:
        response = requests.post("http://localhost:11434/api/generate", json={
            "model": "llama3",
            "prompt": prompt,
            "stream": False
        })

        if response.ok:
            print(f"\n💬 LLaMA Response:\n{response.json()['response']}")
        else:
            print(f"❌ LLaMA API error: {response.status_code}")

    except Exception as e:
        print(f"❌ Could not reach LLaMA API: {e}")


def main():
    pdf_path = input("Enter path to main PDF file: ").strip()
    download_dir = input("Enter directory to save downloaded PDFs: ").strip()

    if not os.path.exists(pdf_path):
        print("❌ Main PDF file does not exist.")
        return

    print("\n📄 Extracting text and links from the main PDF...")
    main_text, links = extract_text_and_links(pdf_path)

    # Save main text for reference
    main_text_file = "main_text.txt"
    Path(main_text_file).write_text(main_text)

    # Download linked files
    downloaded_files = []
    if links:
        downloaded_files = download_linked_files(links, download_dir)
    else:
        print("ℹ️ No links found in the main PDF.")

    # Extract text from all PDFs
    all_text = main_text
    if downloaded_files:
        for fpath in downloaded_files:
            if fpath.endswith(".pdf") and os.path.exists(fpath):
                print(f"\n📥 Extracting text from downloaded file: {fpath}")
                file_text, _ = extract_text_and_links(fpath)
                all_text += "\n\n" + file_text

    if not all_text.strip():
        print("⚠️ No content extracted from PDFs.")
        return

    print("\n✅ All text extracted. Ready to query with LLaMA.")
    while True:
        query = input("\n🔎 Ask your question (or type 'exit'): ").strip()
        if query.lower() in ['exit', 'quit']:
            break

        relevant_chunks = find_semantically_relevant_chunks(all_text, query, top_k=3)
        context = "\n\n".join(relevant_chunks)

        prompt = f"""Based on the following document context, answer the question with technical accuracy and detail:

{context}

Question: {query}
"""
        ask_ollama(prompt)


if __name__ == "__main__":
    main()
