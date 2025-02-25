#!/usr/bin/env python3

def fix_file():
    """Fix the test_check_translations.py file by replacing it with the correct version."""
    file_path = 'scout/tests/translations/test_check_translations.py'
    source_path = 'test_check_translations_name.py'
    
    # Create fixed content with explicit name tags
    with open(source_path, 'r', encoding='utf-8') as f:
        correct_content = f.read()
    
    # Write the correct content directly
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(correct_content)
    
    print(f"File replaced with correct content: {file_path}")
    
    # Verify the file now has <name> tags
    with open(file_path, 'r', encoding='utf-8') as f:
        updated_content = f.read()
        print(f"File contains correct tags: {'<name>MainWindow</name>' in updated_content}")

if __name__ == "__main__":
    fix_file() 