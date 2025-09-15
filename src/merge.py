
"""
Merge Script for JSON Files

Combine several .json files that hold AlumniProfile instances as plain dictionaries,
where each entry is keyed by uid. All files in the provided directory are merged into
a single .json file at the specified output location.
"""

import json
import os

from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

data_dir = os.getenv("DATA_DIR")

combined_data = {}

# grab all JSON files in the directory
source_dir = input("Source directory (path): ")
json_files = list(Path(source_dir).glob("*json"))

if not json_files:
    print("No files to merge.")
    exit()

print(f"Found {len(json_files)} .json files to merge.")

for json_file in json_files:
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # merge, if there are duplicates later files will overwrite earlier ones
        combined_data.update(data)
        
        print(f"Processed: {json_file.name} ({len(data)} records)")
        
    except json.JSONDecodeError as e:
        print(f"Error reading {json_file.name}: Invalid JSON - {e}")
    except Exception as e:
        print(f"Error processing {json_file.name}: {e}")

output_file_name = input("Output file name: ")
output_file = data_dir + output_file_name

try:
    # write the combined data to the output file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(combined_data, f, indent=2, ensure_ascii=False)
    
    print(f"Successfully combined {len(combined_data)} total records")
    print(f"Output saved to: {output_file}")
    
except Exception as e:
    print(f"Error writing output file: {e}")