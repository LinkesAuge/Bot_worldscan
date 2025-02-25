#!/usr/bin/env python3

# Debug script to fix the XML tags in the test file
file_path = 'scout/tests/translations/test_check_translations.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

print(f"Original content contains '<n>MainWindow</n>': {'<n>MainWindow</n>' in content}")

# Fix the comment
comment_replaced = content.replace("# Translation file with correct <n> tags", 
                                  "# Translation file with correct <name> tags")
print(f"Comment replaced: {comment_replaced != content}")

# Replace the actual tags
new_content = comment_replaced.replace("<n>MainWindow</n>", "<name>MainWindow</name>")
print(f"Tags replaced: {new_content != comment_replaced}")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

# Verify the changes
with open(file_path, 'r', encoding='utf-8') as f:
    updated_content = f.read()

print(f"Updated content contains '<name>MainWindow</name>': {'<name>MainWindow</name>' in updated_content}")
print(f"Updated content still has '<n>MainWindow</n>': {'<n>MainWindow</n>' in updated_content}")
print(f"File updated: {file_path}") 