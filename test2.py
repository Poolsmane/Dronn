import os
import requests
import pdfplumber
import subprocess
import string
from urllib.parse import urlparse
from pathlib import Path

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer


class RAGAgent:
    def __init__(self, model="deepseek-r1"):
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        self.model = model

    def extract_text_and_links(self, pdf_path):
        text_content = ""
        links = set()
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    print(f"📖 Reading page {i + 1}/{len(pdf.pages)}")
                    if (page_text := page.extract_text()):
                        text_content += page_text + "\n"
                    if page.annots:
                        for annot in page.annots:
                            uri = annot.get("uri")
                            if uri and uri.startswith("http"):
                                links.add(uri)
        except Exception as e:
            print(f"❌ Error reading {pdf_path}: {e}")
        return text_content.strip(), list(links)

    def generate_filenames(self, n):
        alphabet = string.ascii_lowercase
        result, i = [], 0
        while len(result) < n:
            name, temp = '', i
            while True:
                name = alphabet[temp % 26] + name
                temp = temp // 26 - 1
                if temp < 0:
                    break
            result.append(f"{name}.pdf")
            i += 1
        return result

    def download_linked_files(self, links, download_dir):
        os.makedirs(download_dir, exist_ok=True)
        filenames = self.generate_filenames(len(links))
        downloaded = []
        for idx, link in enumerate(links):
            try:
                response = requests.get(link, timeout=15, verify=False)
                if response.status_code == 200:
                    filename = os.path.join(download_dir, filenames[idx])
                    with open(filename, "wb") as f:
                        f.write(response.content)
                    downloaded.append(filename)
                    print(f"✅ Downloaded: {filename}")
                else:
                    print(f"⚠️ Status {response.status_code} for {link}")
            except Exception as e:
                print(f"❌ Download error for {link}: {e}")
        return downloaded

    def chunk_text(self, text, chunk_size=700, overlap=200):
        return [
            text[i:i + chunk_size]
            for i in range(0, len(text), chunk_size - overlap)
            if len(text[i:i + chunk_size].strip()) > 20
        ]

    def retrieve_chunks(self, query, chunks, top_k=3):
        chunk_embeddings = self.embedder.encode(chunks, convert_to_numpy=True)
        query_embedding = self.embedder.encode([query], convert_to_numpy=True)

        index = faiss.IndexFlatL2(chunk_embeddings.shape[1])
        index.add(chunk_embeddings)
        _, indices = index.search(query_embedding, top_k)
        return [chunks[i] for i in indices[0]]

    def ask(self, context, query):
        prompt = (
            f"Use the following context to answer the question accurately and concisely:\n\n"
            f"{context}\n\n"
            f"Question: {query}\n"
            f"Answer in bullet points or structured format if applicable:"
        )
        try:
            process = subprocess.Popen(
                ["ollama", "run", self.model],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate(input=prompt)
            print("\n🧠 DeepSeek Response:")
            print(stdout.strip())
        except Exception as e:
            print(f"❌ Model error: {e}")

    def run(self, pdf_path, download_dir):
        if not os.path.exists(pdf_path):
            print("❌ PDF not found.")
            return

        print("🔍 Extracting main PDF...")
        main_text, links = self.extract_text_and_links(pdf_path)

        all_text = main_text
        if links:
            downloaded = self.download_linked_files(links, download_dir)
            for pdf in downloaded:
                if pdf.endswith(".pdf"):
                    extra_text, _ = self.extract_text_and_links(pdf)
                    all_text += "\n\n" + extra_text

        if not all_text.strip():
            print("⚠️ No text found.")
            return

        chunks = self.chunk_text(all_text)

        while True:
            query = input("\n🔎 Ask something (or type 'exit'): ").strip()
            if query.lower() in ['exit', 'quit']:
                break
            relevant = self.retrieve_chunks(query, chunks)
            self.ask("\n\n".join(relevant), query)
# from rag_agent import RAGAgent

if __name__ == "__main__":
    agent = RAGAgent()
    pdf_path = input("📁 Enter main PDF path: ").strip()
    download_dir = input("📥 Download directory: ").strip()
    agent.run(pdf_path, download_dir)
