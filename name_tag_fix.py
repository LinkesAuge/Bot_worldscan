#!/usr/bin/env python3

def fix_file():
    file_path = 'scout/tests/translations/test_check_translations.py'
    
    # Read file as text
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"Original content length: {len(content)}")
    
    # Replace <n> tags with <name> tags
    modified_content = content.replace('<n>MainWindow</n>', '<name>MainWindow</name>')
    
    # Replace comment
    modified_content = modified_content.replace(
        '# Translation file with correct <n> tags', 
        '# Translation file with correct <name> tags'
    )
    
    print(f"Content changed: {content != modified_content}")
    
    # Write back to file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(modified_content)
    
    print(f"File updated: {file_path}")
    
    # Verify the changes
    with open(file_path, 'r', encoding='utf-8') as f:
        updated = f.read()
    
    tag_match = '<name>MainWindow</name>' in updated
    comment_match = '# Translation file with correct <name> tags' in updated
    
    print(f"Tag replaced: {tag_match}")
    print(f"Comment replaced: {comment_match}")

if __name__ == "__main__":
    fix_file() 