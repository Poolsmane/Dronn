# from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.llms import Ollama
from langchain.chains.question_answering import load_qa_chain
from langchain.docstore.document import Document
from sentence_transformers import SentenceTransformer
from langchain.chains import RetrievalQA
from langchain.text_splitter import RecursiveCharacterTextSplitter
import fitz
import time
import string
import os
import requests
import numpy as np
import pytesseract
from easyocr import Reader
import threading
from langchain_ollama import OllamaLLM
import pdfplumber
# Load better embedding model (local, no key)
embedding_model = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")
reader = Reader(lang_list=['en'])

# Store final extracted content globally
all_text_final = ""

# ✅ Function to extract text and links from PDF using PyMuPDF (fitz)
from unstructured.partition.pdf import partition_pdf

def extract_text_and_links(pdf_path):
    text_content = ""
    links = set()

    try:
        # Extract links using PyMuPDF as before (unchanged)
        doc = fitz.open(pdf_path)
        for i in range(len(doc)):
            page = doc.load_page(i)
            links.update([link.get('uri') for link in page.get_links() if 'uri' in link])

        # Extract text with unstructured.partition.pdf
        elements = partition_pdf(filename=pdf_path)
        for el in elements:
            # el.text contains the textual content of the element
            if el.text:
                text_content += el.text + "\n"

    except Exception as e:
        print(f"❌ Failed to read {pdf_path} with unstructured: {e}")
        return "", []

    return text_content.strip(), list(links)



def generate_filenames(n):
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

# ✅ Downloads files from links
def download_linked_files(links, download_dir):
    os.makedirs(download_dir, exist_ok=True)
    downloaded_files = []
    filenames = generate_filenames(len(links))

    for idx, link in enumerate(links):
        try:
            response = requests.get(link, timeout=15, verify=False)
            if response.status_code == 200:
                filepath = os.path.join(download_dir, filenames[idx])
                with open(filepath, "wb") as f:
                    f.write(response.content)
                downloaded_files.append(filepath)
                print(f"✅ Downloaded: {filepath}")
            else:
                print(f"❌ Status {response.status_code}: {link}")
        except Exception as e:
            print(f"❌ Error downloading {link}: {e}")
    return downloaded_files

# ✅ Summarize extracted text and save to a file
def summarize_and_save(full_text, output_file="summary.txt", chunk_size=3000, overlap=200):
    if not full_text.strip():
        print("⚠️ No text to summarize.")
        return

    try:
        from langchain.text_splitter import RecursiveCharacterTextSplitter

        llm = OllamaLLM(model="deepseek-r1")

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            separators=["\n\n", "\n", ".", " "]
        )
        chunks = splitter.split_text(full_text)
        all_summaries = []

        print(f"🧩 Splitting into {len(chunks)} chunks for summarization...")

        for i, chunk in enumerate(chunks):
            prompt = f"Summarize this part of a document:\n\n{chunk}\n\nSummary:"
            partial_summary = llm.invoke(prompt)
            all_summaries.append(f"--- Chunk {i+1} Summary ---\n{partial_summary}\n")

        # Optional: summarize all summaries
        combined_summary_prompt = "Summarize the following combined summaries into a cohesive document summary:\n\n" + "\n".join(all_summaries)
        final_summary = llm.invoke(combined_summary_prompt)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write("📌 FINAL SUMMARY\n\n")
            f.write(final_summary.strip())
            f.write("\n\n📄 DETAILED SECTION SUMMARIES\n\n")
            f.write("\n".join(all_summaries))

        print(f"✅ Detailed + Final summary saved to {output_file}")

    except Exception as e:
        print(f"❌ Error in smart_summarize_and_save: {e}")



# ✅ Processes main + linked PDFs
def handle_pdf_and_links(current_pdf_path):
    global all_text_final
    try:
        text, links = extract_text_and_links(current_pdf_path)
        all_text = text
        if links:
            downloaded_files = download_linked_files(links, download_dir="linked_pdfs")
            for fpath in downloaded_files:
                if fpath.endswith(".pdf") and os.path.exists(fpath):
                    file_text, _ = extract_text_and_links(fpath)
                    all_text += "\n" + file_text
        if not all_text.strip():
            print("⚠️ No content found.")
            return
        
        all_text_final = all_text
        summarize_and_save(all_text_final)
        print("✅ Extracted content ready.")
    except Exception as e:
        print(f"❌ Error processing PDF: {e}")

# ✅ Finds relevant chunks with FAISS
def find_relevant_chunks(text, query, chunk_size=1300, overlap=140, top_k=5):
    try:
        if not text.strip():
            return "❌ No text found after preprocessing."

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            separators=["\n\n", "\n", ".", " ", "|"]  # add pipe as table column delimiter
        )

        chunks = splitter.split_text(text)
        docs = [Document(page_content=chunk) for chunk in chunks if len(chunk) > 50]

        vector_store = FAISS.from_documents(docs, embedding_model)
        return vector_store.similarity_search(query, top_k=top_k)
    except Exception as e:
        return f"❌ Error while finding relevant chunks: {str(e)}"

# ✅ Answers questions using Ollama (DeepSeek or other)
def process_with_langchain_agent(question):
    print(f"Processing question: {question}")
    try:
        # Initialize Ollama (make sure Ollama + model is running)
        llm = OllamaLLM(model="deepseek-r1")  # or "mistral"
        
        # Get the relevant chunks based on the question
        docs = find_relevant_chunks(all_text_final, question)
        if isinstance(docs, str):  # error message returned
            return docs

        # Create the retriever from FAISS vector store
        retriever = FAISS.from_documents(docs, embedding_model).as_retriever(search_type="similarity", search_kwargs={"k": 5})

        # Initialize the RetrievalQA chain
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            retriever=retriever,
            chain_type="stuff"  # You can choose from "stuff", "map_reduce", "refine"
        )

        # Run the query with the correct input format (using 'query' key)
        response = qa_chain.invoke({"query": question})
        
        # Check if the response contains the actual answer and return it
        if hasattr(response, 'get'):
            # This is where we extract the content from the response object
            return response.get('result', 'No result found')
        else:
            return str(response)  # In case it is a string or a plain object

    except Exception as e:
        return f"❌ Error in process_with_langchain_agent: {str(e)}"


# ✅ PDF folder watcher
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
            print(f"\n🔄 New file: {current_pdf_path}")
            last_pdf_path = current_pdf_path
            threading.Thread(target=handle_pdf_and_links, args=(current_pdf_path,)).start()
        time.sleep(poll_interval)

# ✅ Main run loop
if __name__ == "__main__":
    monitor_and_run_rag()
