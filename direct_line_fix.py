#!/usr/bin/env python3

def fix_file():
    """Fix the test file by directly updating specific lines with character-by-character approach."""
    file_path = 'scout/tests/translations/test_check_translations.py'
    
    # Read all lines from the file
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Character by character construction to avoid editor replacements
    # For line 103 (comment)
    comment_line = '        # Translation file with correct '
    comment_line += '<' + 'n' + 'a' + 'm' + 'e' + '>'
    comment_line += ' tags\n'
    
    # For line 108 (tag)
    tag_line = '            '
    tag_line += '<' + 'n' + 'a' + 'm' + 'e' + '>'
    tag_line += 'MainWindow'
    tag_line += '<' + '/' + 'n' + 'a' + 'm' + 'e' + '>'
    tag_line += '\n'
    
    # Update the lines
    lines[103] = comment_line
    lines[107] = tag_line
    
    # Write the modified lines back to the file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print("File updated successfully")
    
    # Debug output
    print(f"Line 103 now contains: {lines[103].strip()}")
    print(f"Line 108 now contains: {lines[107].strip()}")

if __name__ == "__main__":
    fix_file() 