#!/usr/bin/env python3

def fix_file():
    """Fix the test file using raw byte manipulation to avoid editor issues."""
    file_path = 'scout/tests/translations/test_check_translations.py'
    
    # Read the file content as binary
    with open(file_path, 'rb') as f:
        content = f.read()
    
    # Define the bytes to replace
    old_tag = b'<n>MainWindow</n>'
    new_tag = b'<name>MainWindow</name>'
    
    old_comment = b'# Translation file with correct <n> tags'
    new_comment = b'# Translation file with correct <name> tags'
    
    # Replace the content
    content = content.replace(old_tag, new_tag)
    content = content.replace(old_comment, new_comment)
    
    # Write back to the file
    with open(file_path, 'wb') as f:
        f.write(content)
    
    print(f"File updated: {file_path}")

if __name__ == "__main__":
    fix_file() 