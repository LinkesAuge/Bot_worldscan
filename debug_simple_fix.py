#!/usr/bin/env python3

def fix_file():
    file_path = 'scout/tests/translations/test_check_translations.py'
    output_path = 'scout/tests/translations/test_check_translations_fixed.py'
    
    # Read the original file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"File content length: {len(content)}")
    
    # Create the tags
    n_tag = '<n>MainWindow</n>'
    name_tag = '<name>MainWindow</name>'
    
    n_comment = '# Translation file with correct <n> tags'
    name_comment = '# Translation file with correct <name> tags'
    
    # Check if patterns exist in the file
    print(f"n_tag exists in file: {n_tag in content}")
    print(f"name_tag already exists in file: {name_tag in content}")
    print(f"n_comment exists in file: {n_comment in content}")
    print(f"name_comment already exists in file: {name_comment in content}")
    
    # Print the exact string we're searching for
    print(f"N tag to search for: {repr(n_tag)}")
    
    # Try to find the context more precisely
    import re
    context_pattern = re.compile(r'<context>\s*<n>MainWindow</n>', re.DOTALL)
    matches = context_pattern.findall(content)
    print(f"Context pattern matches: {len(matches)}")
    for i, m in enumerate(matches):
        print(f"Match {i}: {repr(m)}")
    
    # Try a simpler regex pattern
    n_tag_pattern = re.compile(r'<n>MainWindow</n>')
    n_matches = n_tag_pattern.findall(content)
    print(f"n_tag pattern matches: {len(n_matches)}")
    
    # Modified approach - create a fixed output by modifying TS content directly
    new_content = content
    if '<context>\n            <n>MainWindow</n>' in content:
        new_content = content.replace(
            '<context>\n            <n>MainWindow</n>', 
            '<context>\n            <name>MainWindow</name>'
        )
        print("Fixed context with newlines")
    
    ts_content_old = '        # Translation file with correct <n> tags\n        ts_content = """'
    ts_content_new = '        # Translation file with correct <name> tags\n        ts_content = """'
    
    if ts_content_old in new_content:
        new_content = new_content.replace(ts_content_old, ts_content_new)
        print("Fixed comment")
    
    # Hacky but effective approach - manually fix the line we know contains the tag
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines):
        if '<n>MainWindow</n>' in line:
            print(f"Found tag in line {i+1}: {repr(line)}")
            lines[i] = line.replace('<n>MainWindow</n>', '<name>MainWindow</name>')
            print(f"Fixed line {i+1}")
        if '# Translation file with correct <n> tags' in line:
            print(f"Found comment in line {i+1}: {repr(line)}")
            lines[i] = line.replace('<n> tags', '<name> tags')
            print(f"Fixed comment in line {i+1}")
    
    # Write to a new file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print(f"New content written to: {output_path}")
    print("Please check this file before replacing the original")

if __name__ == "__main__":
    fix_file() 