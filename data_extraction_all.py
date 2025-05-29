import os
import csv
import re
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaLLM
from langchain.chains import RetrievalQA
from unstructured.partition.pdf import partition_pdf

INPUT_CSV = "filtered_bid_results.csv"
OUTPUT_CSV = "final_extracted_data.csv"
PDF_DIR = "/home/kartikeyapatel/Videos/gem/first_extracted_data"

# Embedding model
embedding_model = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-en-v1.5",
    model_kwargs={"device": "cpu"}
)

# Text splitting
def split_text(text, chunk_size=900, overlap=85):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", ".", " "]
    )
    return splitter.split_text(text)

# Extract text from PDF
def extract_text_from_pdf(pdf_path):
    try:
        elements = partition_pdf(filename=pdf_path)
        return "\n".join(el.text for el in elements if el.text)
    except Exception as e:
        print(f"❌ Failed to extract text from {pdf_path}: {e}")
        return ""

# Clean numeric or currency-style answers
def clean_numeric_answer(text):
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    for prefix in ["**Answer:**", "Answer:", "- ", "* "]:
        if prefix in text:
            text = text.split(prefix)[-1]
    text = re.sub(r"[^\x00-\x7F]+", " ", text).strip().replace("\n", " ").strip()
    if not text or text == ".":
        return "None"

    match = re.search(
        r"(?i)\b(?:Rs\.?|INR|USD|EUR|₹|\$)?\s*[\d,]+(?:\.\d+)?\s*(lakh|crore|million|billion|rupees)?\b",
        text
    )
    if match:
        return match.group(0).strip()

    paren_match = re.search(
        r"\b[\d,]+(?:\.\d+)?\s*(lakh|crore|million|billion|rupees)?\b\s*\([^)]*\)", text, re.IGNORECASE)
    if paren_match:
        return paren_match.group(0).split("(")[0].strip()

    if len(text.split()) <= 15:
        return text.strip()

    return "None"

# Clean short textual answers (like "Two Packet Bid")
def clean_textual_answer(text):
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    for prefix in ["**Answer:**", "Answer:", "- ", "* "]:
        if prefix in text:
            text = text.split(prefix)[-1]
    text = re.sub(r"[^\x00-\x7F]+", " ", text).strip().replace("\n", " ").strip()
    if not text or text == ".":
        return "None"

    cleaned = text.strip('"').strip()
    if 2 <= len(cleaned.split()) <= 8:
        return cleaned

    return "None"

# Generate structured field answers via LangChain + FAISS
def extract_fields(text):
    try:
        chunks = split_text(text)
        docs = [Document(page_content=chunk) for chunk in chunks if chunk.strip()]
        vector_store = FAISS.from_documents(docs, embedding_model)
        retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 4})
        llm = OllamaLLM(model="deepseek-r1")

        qa = RetrievalQA.from_chain_type(
            llm=llm,
            retriever=retriever,
            chain_type="stuff"
        )

        questions = {
            "EMD Amount": "What is the EMD Amount/ईएमड ?",
            "Type of Bid": "Give me the Type of Bid, one packet ,two packet,etc?",
            "Estimated Bid Value": "What is the Estimated Bid Value?",
            "Minimum Average Annual Turnover": "What is the Minimum Average Annual Turnover of the bidder (For 3 Years)?"
        }

        answers = {}
        for key, question in questions.items():
            response = qa.invoke({"query": question})
            raw_text = response.get("result", "").strip() if isinstance(response, dict) else str(response).strip()
            print(f"\n🧠 {key} Raw LLM response: {raw_text}\n")

            if key == "Type of Bid":
                answer = clean_textual_answer(raw_text)
            else:
                answer = clean_numeric_answer(raw_text)

            if answer == "None" and key in ["EMD Amount", "Estimated Bid Value", "Minimum Average Annual Turnover"]:
                answer = "0"

            answers[key] = answer

        return answers
    except Exception as e:
        print(f"❌ Error during field extraction: {e}")
        return {}

# Append row to CSV
def append_to_csv(row, header):
    file_exists = os.path.isfile(OUTPUT_CSV)
    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

# Main pipeline
def main():
    # Load existing entries from output CSV to skip duplicates
    processed_keys = set()
    if os.path.exists(OUTPUT_CSV):
        with open(OUTPUT_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = (row.get("Bid Number", "").strip(), row.get("Ministry Name", "").strip())
                processed_keys.add(key)

    # Read input and process unprocessed PDFs
    with open(INPUT_CSV, "r", encoding="utf-8") as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            bid_number = row.get("Bid Number", "").strip()
            ministry_name = row.get("Department", "").strip()
            key = (bid_number, ministry_name)

            # Check for duplicates
            if key in processed_keys:
                raw_name = row.get("Downloaded Filename", "").strip()
                filename = raw_name if raw_name.endswith(".pdf") else f"{raw_name}.pdf"
                pdf_path = os.path.join(PDF_DIR, filename)
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)
                    print(f"⏩ Skipped & deleted duplicate file: {filename}")
                else:
                    print(f"⏩ Skipped duplicate (file already missing): {filename}")
                continue

            raw_name = row.get("Downloaded Filename", "").strip()
            if not raw_name or raw_name.startswith("ERROR"):
                print(f"⏩ Skipping invalid filename: {raw_name}")
                continue

            filename = raw_name if raw_name.endswith(".pdf") else f"{raw_name}.pdf"
            pdf_path = os.path.join(PDF_DIR, filename)
            if not os.path.isfile(pdf_path):
                print(f"⚠️ File missing: {pdf_path}")
                continue

            print(f"🔍 Processing {filename}")
            text = extract_text_from_pdf(pdf_path)
            if not text.strip():
                print(f"⚠️ Empty content in {filename}")
                continue

            extracted = extract_fields(text)
            output_row = {
                "Bid Number": bid_number,
                "Ministry Name": ministry_name,
                "Downloaded Filename": filename,
                "EMD Amount": extracted.get("EMD Amount", ""),
                "Type of Bid": extracted.get("Type of Bid", ""),
                "Estimated Bid Value": extracted.get("Estimated Bid Value", ""),
                "Minimum Average Annual Turnover": extracted.get("Minimum Average Annual Turnover", "")
            }

            append_to_csv(output_row, header=list(output_row.keys()))
            os.remove(pdf_path)
            print(f"✅ Extracted & deleted: {filename}")



if __name__ == "__main__":
    main()
