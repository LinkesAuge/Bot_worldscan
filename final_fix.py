#!/usr/bin/env python3

def fix_file():
    """Fix the test file using string concatenation to avoid editor issues."""
    file_path = 'scout/tests/translations/test_check_translations.py'
    
    # We have to use string concatenation to avoid editor replacement
    name_open = '<' + 'name' + '>'
    name_close = '</' + 'name' + '>'
    n_open = '<' + 'n' + '>'
    n_close = '</' + 'n' + '>'
    
    # Read file and replace
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace tags
    content = content.replace(n_open + 'MainWindow' + n_close, 
                              name_open + 'MainWindow' + name_close)
    
    # Replace comment - building it character by character
    n_tag = '<' + 'n' + '>'
    name_tag = '<' + 'name' + '>'
    
    old_comment = '# Translation file with correct ' + n_tag + ' tags'
    new_comment = '# Translation file with correct ' + name_tag + ' tags'
    content = content.replace(old_comment, new_comment)
    
    # Write back to file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("File updated successfully")

if __name__ == "__main__":
    fix_file() 