#!/usr/bin/env python3

def fix_file():
    """Fix the test file using escape characters to avoid editor issues."""
    file_path = 'scout/tests/translations/test_check_translations.py'
    
    # Read the file content
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace using escaped characters
    # Replace <n>MainWindow</n> with <name>MainWindow</name>
    content = content.replace('&lt;n&gt;MainWindow&lt;/n&gt;', '&lt;name&gt;MainWindow&lt;/name&gt;')
    content = content.replace('<n>MainWindow</n>', '<name>MainWindow</name>')
    
    # Replace the comment
    content = content.replace('# Translation file with correct <n> tags', 
                             '# Translation file with correct <name> tags')
    
    # Write back to the file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"File updated: {file_path}")

if __name__ == "__main__":
    fix_file() 