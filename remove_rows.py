import csv
import os

input_csv = 'bid_results.csv'
intermediate_csv = 'filtered_bid_results.csv'
output_csv = 'filtered_bid_results.csv'

# Keywords for selective matching in 'Items'
keywords = ['software', 'consultancy', 'custom', 'development', 'learning']

# Step 1: Read previous filtered data (if any)
existing_rows = []
if os.path.exists(intermediate_csv):
    with open(intermediate_csv, mode='r', newline='', encoding='utf-8') as existing_file:
        reader = csv.DictReader(existing_file)
        existing_rows = [row for row in reader]

# Step 2: Read new bid_results.csv data
with open(input_csv, mode='r', newline='', encoding='utf-8') as infile:
    reader = csv.DictReader(infile)
    new_rows = [row for row in reader]

# Step 3: Combine and filter out rows with 'Not Found' Bid Number
all_rows = existing_rows + new_rows
filtered_rows = [row for row in all_rows if row['Bid Number'].strip().lower() != 'not found']

# Step 4: Remove duplicates based on 'Bid Number'
seen = set()
unique_rows = []
for row in filtered_rows:
    bid = row['Bid Number']
    if bid not in seen:
        seen.add(bid)
        unique_rows.append(row)

# Step 5: Selective match on 'Items' column using keywords
matched_rows = []
for row in unique_rows:
    item_value = row.get('Items', '').lower()
    if any(keyword in item_value for keyword in keywords):
        matched_rows.append(row)

# Step 6: Write to final_bid_results.csv
fieldnames = ['Bid Number', 'Items', 'Quantity', 'Department', 'Start Date', 'End Date', 'Downloadable File URL']
with open(output_csv, mode='w', newline='', encoding='utf-8') as outfile:
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(matched_rows)

print(f"Filtered, merged, and keyword-matched data saved to {output_csv}")
