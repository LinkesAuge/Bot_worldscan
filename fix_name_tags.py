#!/usr/bin/env python3

# Script to fix the XML tags in the test file
file_path = 'scout/tests/translations/test_check_translations.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the comment to be more clear
content = content.replace("# Translation file with correct <n> tags",
                         "# Translation file with correct <name> tags")

# Replace the actual tags
content = content.replace("<n>MainWindow</n>", "<name>MainWindow</name>")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Updated file: {file_path}") 