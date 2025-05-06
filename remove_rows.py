import csv

input_csv = 'bid_results.csv'
output_csv = 'filtered_bid_results.csv'

with open(input_csv, mode='r', newline='', encoding='utf-8') as infile:
    reader = csv.DictReader(infile)
    rows = [row for row in reader if row['Bid Number'] != 'Not Found']

# Adjusted fieldnames to match scrap.py output
fieldnames = ['Bid Number', 'Items', 'Quantity', 'Department', 'Start Date', 'End Date', 'Downloadable File URL']

with open(output_csv, mode='w', newline='', encoding='utf-8') as outfile:
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"Filtered data saved to {output_csv}")
