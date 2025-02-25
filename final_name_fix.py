#!/usr/bin/env python3

def fix_file():
    file_path = 'scout/tests/translations/test_check_translations.py'
    output_path = 'scout/tests/translations/test_check_translations_fixed.py'
    
    # Read the original file
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Process each line
    new_lines = []
    for line in lines:
        # Replace the comment line
        if '# Translation file with correct <n> tags' in line:
            new_lines.append('        # Translation file with correct <name> tags\n')
        # Replace the tag line
        elif '<n>MainWindow</n>' in line:
            new_lines.append(line.replace('<n>MainWindow</n>', '<name>MainWindow</name>'))
        else:
            new_lines.append(line)
    
    # Write to a new file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print(f"New content written to: {output_path}")
    print("Please check this file before replacing the original")

if __name__ == "__main__":
    fix_file() 