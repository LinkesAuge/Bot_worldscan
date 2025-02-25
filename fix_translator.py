#!/usr/bin/env python3

"""
This script fixes the XML tags in the test_check_translations.py file,
changing <n> tags to <name> tags.
"""

import sys

def fix_file():
    file_path = 'scout/tests/translations/test_check_translations.py'
    
    try:
        # Read the file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace the comment
        content = content.replace('# Translation file with correct <n> tags', 
                                 '# Translation file with correct <name> tags')
        
        # Replace the XML tags
        content = content.replace('<n>MainWindow</n>', '<name>MainWindow</name>')
        
        # Write the modified content back to the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Successfully updated file: {file_path}")
        return 0
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(fix_file()) 