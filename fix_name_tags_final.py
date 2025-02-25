#!/usr/bin/env python3

"""
Simple script to copy the correct file over the problematic one.
"""

import shutil

def main():
    source_file = 'correct_test_file_with_name.py'
    target_file = 'scout/tests/translations/test_check_translations.py'
    
    try:
        print(f"Copying {source_file} to {target_file}...")
        shutil.copy2(source_file, target_file)
        print(f"Successfully updated {target_file}")
        return 0
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main()) 