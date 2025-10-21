# check_categories.py (Updated with auto-discovery)

import argparse
import os
import re
import sys

def find_category_from_content(content: str) -> str | None:
    """
    Parses the content of a Markdown file to find the category.

    Args:
        content: The string content of the Markdown file.

    Returns:
        The category string if found, otherwise None.
    """
    category_pattern = re.compile(r"^\s*-\s*\*\*(?i:Category)\*\*:\s*(.*)$", re.MULTILINE)
    
    match = category_pattern.search(content)
    if match:
        return match.group(1).strip()
        
    return None

def verify_directory_structure(filepath: str):
    """
    Reads a Markdown file, extracts its category, and verifies the
    corresponding dashboard/categories directory exists.
    
    Args:
        filepath: The path to the Markdown file to process.
    """
    print(f"--> Processing file: {filepath}")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        category = find_category_from_content(content)
        
        if not category:
            print(f"    INFO: No category found in {filepath}")
            return

        print(f"    - Found Category: '{category}'")
        
        category_dir_name = category.lower()
        
        base_dir = os.path.dirname(os.path.abspath(filepath))
        
        expected_dir = os.path.join(base_dir, '..', 'dashboard', 'categories', category_dir_name)
        
        normalized_path = os.path.normpath(expected_dir)
        
        if not os.path.isdir(expected_dir):
            print(f"    **WARNING**: Corresponding directory does not exist at: {normalized_path}\n")
        else:
            print(f"    V OK: Directory found at: {normalized_path}\n")
            
    except FileNotFoundError:
        print(f"**ERROR**: File not found at {filepath}\n", file=sys.stderr)
    except Exception as e:
        print(f"**ERROR**: An unexpected error occurred while processing {filepath}: {e}\n", file=sys.stderr)

def main():
    """
    The main function to set up the CLI and process the files.
    If no files are specified, it scans the current directory for .md files.
    """
    parser = argparse.ArgumentParser(
        description="A CLI tool to check that a category directory exists for each Markdown file."
    )
    # --- MODIFIED LINE ---
    # nargs is now '*' which means 'zero or more' arguments are allowed.
    parser.add_argument(
        'files',
        nargs='*',  # Allows the command to be run without any filenames.
        help="A list of Markdown files to process. If empty, all .md files in the current directory are used."
    )
    
    args = parser.parse_args()
    
    # --- NEW LOGIC ---
    files_to_process = args.files
    
    # If the list of files is empty, scan the current directory.
    if not files_to_process:
        print("No filenames provided. Searching for Markdown files in the current directory...\n")
        try:
            # Create a list of all files in the current directory that end with .md
            files_to_process = [
                f for f in os.listdir('.') if os.path.isfile(f) and f.endswith('.md')
            ]
            if not files_to_process:
                print("No Markdown files found.")
                return
        except Exception as e:
            print(f"**ERROR**: Could not read directory contents: {e}", file=sys.stderr)
            return
            
    # Process either the user-provided list or the auto-discovered list.
    for md_file in files_to_process:
        verify_directory_structure(md_file)

if __name__ == "__main__":
    main()
