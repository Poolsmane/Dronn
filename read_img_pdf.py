import pytesseract
from pdf2image import convert_from_path
import os
import cv2
import numpy as np
from pytesseract import Output
from collections import defaultdict
import re

def preprocess_image(img):
    """Enhance image contrast, reduce noise for better OCR"""
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    sharpen = cv2.addWeighted(gray, 1.5, blur, -0.5, 0)
    return cv2.cvtColor(sharpen, cv2.COLOR_GRAY2RGB)

def group_words_by_line(data, y_threshold=12):
    lines = defaultdict(list)
    for i, word in enumerate(data["text"]):
        if word.strip():
            y = data["top"][i]
            x = data["left"][i]
            line_key = y // y_threshold
            lines[line_key].append((x, word.strip()))
    sorted_lines = []
    for line in sorted(lines.keys()):
        words = sorted(lines[line], key=lambda w: w[0])
        text_line = " ".join(w[1] for w in words)
        sorted_lines.append(text_line)
    return sorted_lines

def clean_line(line):
    """Clean garbage characters"""
    line = re.sub(r'[^a-zA-Z0-9@:/\.\-,() ]', '', line)
    line = re.sub(r'\s+', ' ', line).strip()
    return line

def detect_table_rows(image):
    """Detect rows in table using horizontal lines and contours"""
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    _, binary = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (image.shape[1]//5, 1))  # horizontal line detection
    horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(horizontal_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    row_boxes = [cv2.boundingRect(c) for c in contours]

    # sort by Y to keep top-to-bottom reading order
    row_boxes = sorted(row_boxes, key=lambda b: b[1])
    return row_boxes

def extract_table_lines(image):
    """Extract each table row as a line using bounding boxes"""
    rows = detect_table_rows(image)
    extracted_lines = []

    for x, y, w, h in rows:
        roi = image[y:y+h+10, x:x+w]  # +10 to avoid cropping descenders
        text = pytesseract.image_to_string(roi, config="--psm 6")
        clean = clean_line(text)
        if clean:
            extracted_lines.append(clean)

    return extracted_lines

def ocr_pdf_clean_lines(pdf_path, output_txt_path, dpi=300):
    if not os.path.exists(pdf_path):
        print("❌ PDF not found.")
        return

    print("🔄 Converting PDF pages to images...")
    images = convert_from_path(pdf_path, dpi=dpi)

    with open(output_txt_path, "w", encoding="utf-8") as out:
        for idx, pil_img in enumerate(images):
            print(f"📝 Processing Page {idx+1}")
            out.write(f"\n--- Page {idx+1} ---\n")

            img = np.array(pil_img)
            img = preprocess_image(img)

            # If it's a table-heavy image, segment into rows
            rows = detect_table_rows(img)
            if len(rows) > 3:  # Consider as table if 3+ rows detected
                print("📋 Table detected. Extracting row-wise...")
                lines = extract_table_lines(img)
            else:
                print("🔎 Normal text layout. Using grouped lines...")
                data = pytesseract.image_to_data(img, output_type=Output.DICT, config="--psm 6")
                lines = group_words_by_line(data)

            for line in lines:
                clean = clean_line(line)
                if clean:
                    out.write(clean + "\n")

    print(f"✅ Output written to: {output_txt_path}")

if __name__ == "__main__":
    pdf = "/home/kartikeyapatel/Videos/gem/tender_test.pdf"
    output = "/home/kartikeyapatel/Videos/gem/output_ocr.txt"
    ocr_pdf_clean_lines(pdf, output)
