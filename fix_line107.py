#!/usr/bin/env python3

def fix_specific_line():
    file_path = 'scout/tests/translations/test_check_translations.py'
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Print the line we're interested in
    print(f"Line 107 (before): '{lines[107]}'")
    
    # Directly replace line 107
    lines[107] = '            <name>MainWindow</name>\n'
    
    # Also fix the comment line
    for i, line in enumerate(lines):
        if '# Translation file with correct <n> tags' in line:
            lines[i] = line.replace('<n> tags', '<name> tags')
            print(f"Fixed comment at line {i}: '{lines[i]}'")
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    # Verify the changes
    with open(file_path, 'r', encoding='utf-8') as f:
        updated_lines = f.readlines()
    
    print(f"Line 107 (after): '{updated_lines[107]}'")
    print("File updated successfully")

if __name__ == "__main__":
    fix_specific_line() 