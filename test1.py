# import os
# import requests
# import pdfplumber
# from urllib.parse import urlparse
# from pathlib import Path
# import subprocess
# import string
# from sentence_transformers import SentenceTransformer
# import faiss
# import numpy as np


# embedder = SentenceTransformer('all-MiniLM-L6-v2')  # Load once at the top

# def extract_text_and_links(pdf_path):
#     text_content = ""
#     links = set()

#     try:
#         with pdfplumber.open(pdf_path) as pdf:
#             for i, page in enumerate(pdf.pages):
#                 print(f"Reading page {i + 1}/{len(pdf.pages)}")
#                 page_text = page.extract_text()
#                 if page_text:
#                     text_content += page_text + "\n"

#                 if page.annots:
#                     for annot in page.annots:
#                         uri = annot.get("uri")
#                         if uri and uri.startswith("http"):
#                             links.add(uri)
#     except Exception as e:
#         print(f"❌ Failed to read {pdf_path}: {e}")

#     return text_content.strip(), list(links)


# def download_linked_files(links, download_dir):
#     os.makedirs(download_dir, exist_ok=True)
#     downloaded_files = []

#     print(f"\nFound {len(links)} links. Attempting to download files into: {download_dir}")
#     filenames = generate_filenames(len(links))

#     for idx, link in enumerate(links):
#         try:
#             response = requests.get(link, timeout=15)
#             if response.status_code == 200:
#                 filename = filenames[idx]
#                 filepath = os.path.join(download_dir, filename)
#                 with open(filepath, "wb") as f:
#                     f.write(response.content)
#                 downloaded_files.append(filepath)
#                 print(f"✅ Downloaded: {filepath}")
#             else:
#                 print(f"❌ Failed (status {response.status_code}): {link}")
#         except Exception as e:
#             print(f"❌ Error downloading {link}: {e}")
#     return downloaded_files


# def ask_ollama(prompt, model="llama3"):
#     try:
#         process = subprocess.Popen(
#             ["ollama", "run", model],
#             stdin=subprocess.PIPE,
#             stdout=subprocess.PIPE,
#             stderr=subprocess.PIPE,
#             text=True
#         )
#         stdout, stderr = process.communicate(input=prompt)
#         print("\n💬 LLaMA Response:")
#         print(stdout.strip())
#     except Exception as e:
#         print(f"❌ Failed to query LLaMA: {e}")


# def generate_filenames(n):
#     # Generates names like a.pdf, b.pdf, ..., z.pdf, aa.pdf, ab.pdf, ...
#     alphabet = string.ascii_lowercase
#     result = []
#     i = 0
#     while len(result) < n:
#         name = ''
#         temp = i
#         while True:
#             name = alphabet[temp % 26] + name
#             temp = temp // 26 - 1
#             if temp < 0:
#                 break
#         result.append(f"{name}.pdf")
#         i += 1
#     return result


# def find_relevant_chunks(text, query, chunk_size=1000, overlap=200, top_k=3):
#     chunks = []
#     for i in range(0, len(text), chunk_size - overlap):
#         chunk = text[i:i + chunk_size]
#         if len(chunk.strip()) > 20:
#             chunks.append(chunk)

#     chunk_embeddings = embedder.encode(chunks, convert_to_numpy=True)
#     query_embedding = embedder.encode([query], convert_to_numpy=True)

#     index = faiss.IndexFlatL2(chunk_embeddings.shape[1])
#     index.add(chunk_embeddings)
#     distances, indices = index.search(query_embedding, top_k)

#     return [chunks[i] for i in indices[0]]



# def main():
#     pdf_path = input("Enter path to main PDF file: ").strip()
#     download_dir = input("Enter directory to save downloaded PDFs: ").strip()

#     if not os.path.exists(pdf_path):
#         print("❌ Main PDF file does not exist.")
#         return

#     print("\n📄 Extracting text and links from the main PDF...")
#     main_text, links = extract_text_and_links(pdf_path)

#     # Save main text
#     main_text_file = "main_text.txt"
#     Path(main_text_file).write_text(main_text)

#     # Download linked files
#     downloaded_files = []
#     if links:
#         downloaded_files = download_linked_files(links, download_dir)
#     else:
#         print("ℹ️ No links found in the main PDF.")

#     # Extract text from downloaded PDFs
#     all_text = main_text
#     if downloaded_files:
#         for fpath in downloaded_files:
#             if fpath.endswith(".pdf") and os.path.exists(fpath):
#                 print(f"\n📥 Extracting text from downloaded file: {fpath}")
#                 file_text, _ = extract_text_and_links(fpath)
#                 all_text += "\n\n" + file_text

#     if not all_text.strip():
#         print("⚠️ No content extracted from PDFs.")
#         return

#     print("\n✅ All text extracted. Ready to query with LLaMA.")
#     while True:
#         query = input("\n🔎 Ask your question (or type 'exit'): ").strip()
#         if query.lower() in ['exit', 'quit']:
#             break

#         relevant_chunks = find_relevant_chunks(all_text, query)
#         if not relevant_chunks:
#             print("⚠️ Could not find relevant content.")
#             continue

#         relevant_chunks = find_relevant_chunks(all_text, query)
#         context = "\n\n".join(relevant_chunks)
#         prompt = f"Based on the following document context, answer the question accurately:\n\n{context}\n\nQuestion: {query}"

#         ask_ollama(prompt)



# if __name__ == "__main__":
#     main()
from nltk.tokenize import word_tokenize

text = "This is a sample sentence."
tokens = word_tokenize(text)
print(tokens)