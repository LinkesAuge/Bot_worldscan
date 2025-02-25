#!/usr/bin/env python3

# Script to replace <n> tags with <name> tags in the test file
file_path = 'scout/tests/translations/test_check_translations.py'

with open(file_path, 'r') as f:
    content = f.read()

# Replace <n>MainWindow</n> with <name>MainWindow</name>
new_content = content.replace('<n>MainWindow</n>', '<name>MainWindow</name>')

with open(file_path, 'w') as f:
    f.write(new_content)

print('File updated successfully')
