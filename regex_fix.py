#!/usr/bin/env python3
import re

def fix_file():
    file_path = 'scout/tests/translations/test_check_translations.py'
    output_path = 'scout/tests/translations/test_check_translations_fixed.py'
    
    # Read the file contents
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Use regex for replacements
    # Replace <n>MainWindow</n> with <name>MainWindow</name>
    tag_pattern = re.compile(r'<n>MainWindow</n>')
    content = tag_pattern.sub(r'<name>MainWindow</name>', content)
    
    # Replace the comment
    comment_pattern = re.compile(r'# Translation file with correct <n> tags')
    content = comment_pattern.sub(r'# Translation file with correct <name> tags', content)
    
    # Write to the output file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"New content written to: {output_path}")
    print("Please check this file before replacing the original")

if __name__ == "__main__":
    fix_file() 