import csv
import os

input_csv = 'bid_results.csv'
output_csv = 'filtered_bid_results.csv'

# Step 1: Read previous filtered data (if any)
existing_rows = []
if os.path.exists(output_csv):
    with open(output_csv, mode='r', newline='', encoding='utf-8') as existing_file:
        reader = csv.DictReader(existing_file)
        existing_rows = [row for row in reader]

# Step 2: Read new bid_results.csv data
with open(input_csv, mode='r', newline='', encoding='utf-8') as infile:
    reader = csv.DictReader(infile)
    new_rows = [row for row in reader]

# Step 3: Combine and filter out rows with 'Not Found' Bid Number
all_rows = existing_rows + new_rows
filtered_rows = [row for row in all_rows if row['Bid Number'] != 'Not Found']

# Optional: Remove duplicates based on 'Bid Number'
seen = set()
unique_rows = []
for row in filtered_rows:
    if row['Bid Number'] not in seen:
        seen.add(row['Bid Number'])
        unique_rows.append(row)

# Step 4: Write to filtered_bid_results.csv
fieldnames = ['Bid Number', 'Items', 'Quantity', 'Department', 'Start Date', 'End Date', 'Downloadable File URL']
with open(output_csv, mode='w', newline='', encoding='utf-8') as outfile:
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(unique_rows)

print(f"Filtered and merged data saved to {output_csv}")
