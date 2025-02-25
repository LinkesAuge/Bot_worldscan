#!/usr/bin/env python3

import sys

def fix_file():
    file_path = 'scout/tests/translations/test_check_translations.py'
    
    try:
        print("Reading the file...")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check current content
        print(f"Current file has <n> tags: {'<n>MainWindow</n>' in content}")
        print(f"Current file has <name> tags: {'<name>MainWindow</name>' in content}")
        
        # Create the fixed content as a string literal
        fixed_content = """
        # Translation file with correct <name> tags
        ts_content = \"\"\"
        <!DOCTYPE TS>
        <TS version="2.1" language="en_US">
        <context>
            <name>MainWindow</name>
            <message>
                <source>Translated String</source>
                <translation>Translated String</translation>
            </message>
        </context>
        </TS>
        \"\"\"
        """
        
        # Replace the problematic section
        import re
        pattern = r'# Translation file with correct.*?</TS>\s+"""'
        replacement = fixed_content.strip()
        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        # Verify the replacement worked
        print(f"New content has <n> tags: {'<n>MainWindow</n>' in new_content}")
        print(f"New content has <name> tags: {'<name>MainWindow</name>' in new_content}")
        
        # Write the modified content back to the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"Successfully updated file: {file_path}")
        return 0
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(fix_file()) 