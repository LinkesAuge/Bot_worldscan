file_path = 'scout/tests/translations/test_check_translations.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the text using string slices to avoid using angle brackets in the code
old_text = 'n>MainWindow</n'
new_text = 'name>MainWindow</name'

content = content.replace(old_text, new_text)

# Update the comment
content = content.replace('# Translation file with correct <n> tags', '# Translation file with correct <name> tags')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("File updated successfully") 