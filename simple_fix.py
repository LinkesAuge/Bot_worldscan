#!/usr/bin/env python3

def fix_file():
    file_path = 'scout/tests/translations/test_check_translations.py'
    output_path = 'scout/tests/translations/test_check_translations_fixed.py'
    
    # Read the original file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Build the replacements character by character to avoid editor issues
    n_tag = '<n>MainWindow</n>'
    name_tag = '<' + 'name' + '>MainWindow</' + 'name' + '>'
    
    n_comment = '# Translation file with correct <n> tags'
    name_comment = '# Translation file with correct <' + 'name' + '> tags'
    
    # Replace <n> with <name>
    content = content.replace(n_tag, name_tag)
    
    # Replace comment
    content = content.replace(n_comment, name_comment)
    
    # Write to a new file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"New content written to: {output_path}")
    print("Please check this file before replacing the original")

if __name__ == "__main__":
    fix_file() 