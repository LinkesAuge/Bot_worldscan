#!/usr/bin/env python3

def fix_file():
    file_path = 'scout/tests/translations/test_check_translations.py'
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Directly modify line 107 (where the tag is)
    lines[107] = '            <' + 'name' + '>MainWindow</' + 'name' + '>\n'
    
    # Fix the comment line
    for i, line in enumerate(lines):
        if '# Translation file with correct' in line:
            lines[i] = line.replace('<n> tags', '<' + 'name' + '> tags')
    
    # Write the modified lines back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print(f"File updated successfully: {file_path}")

if __name__ == "__main__":
    fix_file() 