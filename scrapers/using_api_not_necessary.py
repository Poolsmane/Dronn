import os
import fitz
import pytesseract
from pdf2image import convert_from_path
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import openai  # Replace with llama if needed

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
EMBED_MODEL = 'all-MiniLM-L6-v2'
OPENAI_MODEL = "gpt-4"
EMBEDDING_DIM = 384

model = SentenceTransformer(EMBED_MODEL)
index = faiss.IndexFlatL2(EMBEDDING_DIM)
chunk_map = []  # (doc_name, chunk)


def extract_text(pdf_path):
    try:
        print(f"📥 Extracting from: {pdf_path}")
        doc = fitz.open(pdf_path)
        text = "".join([page.get_text() for page in doc])
        return text.strip()
    except Exception as e:
        print(f"⚠️ PyMuPDF failed: {e}")
        return ocr_pdf(pdf_path)


def ocr_pdf(pdf_path):
    print("🔍 Running OCR fallback...")
    try:
        pages = convert_from_path(pdf_path)
        return "".join(pytesseract.image_to_string(p) for p in pages)
    except Exception as e:
        print(f"❌ OCR failed: {e}")
        return ""


def chunk_text(text):
    words = text.split()
    return [
        " ".join(words[i:i + CHUNK_SIZE])
        for i in range(0, len(words), CHUNK_SIZE - CHUNK_OVERLAP)
    ]


def embed_and_store(doc_name, chunks):
    embeddings = model.encode(chunks)
    index.add(np.array(embeddings))
    chunk_map.extend([(doc_name, chunk) for chunk in chunks])


def query_pdf(question, top_k=5):
    q_embed = model.encode([question])[0]
    D, I = index.search(np.array([q_embed]), top_k)
    retrieved_chunks = [chunk_map[i][1] for i in I[0]]
    context = "\n---\n".join(retrieved_chunks)
    return synthesize_answer(question, context)


def synthesize_answer(question, context):
    openai.api_key = os.getenv("OPENAI_API_KEY")
    try:
        messages = [
            {"role": "system", "content": "Answer only using the content provided."},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
        ]
        response = openai.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.2,
            max_tokens=600
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"❌ Error: {e}"


def process_pdf(path):
    if not os.path.exists(path):
        print("❌ File not found.")
        return
    text = extract_text(path)
    if not text.strip():
        print("⚠️ No content extracted.")
        return
    chunks = chunk_text(text)
    embed_and_store(os.path.basename(path), chunks)
    print(f"✅ {len(chunks)} chunks embedded from {os.path.basename(path)}.")


def interactive_session():
    while True:
        pdf_path = input("\n📄 Enter PDF file path (or press Enter to skip): ").strip()
        if pdf_path:
            process_pdf(pdf_path)

        while True:
            question = input("❓ Ask your question (or type 'new' to add PDF, or 'exit'): ").strip()
            if question.lower() == "exit":
                return
            elif question.lower() == "new":
                break
            elif not chunk_map:
                print("⚠️ No PDFs loaded yet. Please load one.")
                break
            else:
                answer = query_pdf(question)
                print(f"\n🧠 Answer: {answer}\n")


if __name__ == "__main__":
    print("🤖 PDF Question Answering Assistant Ready")
    interactive_session()
