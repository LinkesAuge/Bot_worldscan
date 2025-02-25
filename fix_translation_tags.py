#!/usr/bin/env python3

"""
Script to directly replace the problematic XML section in the test file.
"""

def main():
    # File path
    file_path = 'scout/tests/translations/test_check_translations.py'
    
    # Correct content with <name> tags
    correct_ts_content = '''
        # Translation file with correct <name> tags
        ts_content = """
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
        """'''
    
    # Read the entire file
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Find the start position of the TS content section
    start_marker = '        # Translation file with correct'
    start_pos = content.find(start_marker)
    
    if start_pos == -1:
        print(f"Error: Could not find the TS content section in {file_path}")
        return 1
    
    # Find the end position of the TS content section
    end_marker = '        """'
    end_pos = content.find(end_marker, start_pos) + len(end_marker)
    
    if end_pos <= len(end_marker):
        print(f"Error: Could not find the end of TS content section in {file_path}")
        return 1
    
    # Replace the section
    new_content = content[:start_pos] + correct_ts_content + content[end_pos:]
    
    # Debug output
    print(f"Original section ({start_pos} to {end_pos}):")
    print(content[start_pos:end_pos])
    print("\nReplacing with:")
    print(correct_ts_content)
    
    # Check for the tags
    print(f"\nBefore replacement:")
    print(f"  Has <n> tags: {'<n>' in content}")
    print(f"  Has <name> tags: {'<name>' in content}")
    
    print(f"\nAfter replacement:")
    print(f"  Has <n> tags: {'<n>' in new_content}")
    print(f"  Has <name> tags: {'<name>' in new_content}")
    
    # Write the modified content back to the file
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(new_content)
    
    print(f"\nSuccessfully updated file: {file_path}")
    return 0

if __name__ == "__main__":
    exit(main()) 