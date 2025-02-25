#!/usr/bin/env python3

"""
This script directly replaces text in the file without worrying about XML escaping.
"""

def main():
    file_path = 'scout/tests/translations/test_check_translations.py'
    
    print(f"Opening file: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Print some debugging info
    n_tag_present = '<n>MainWindow</n>' in content
    name_tag_present = '<name>MainWindow</name>' in content
    
    print(f"Before replacement:")
    print(f"  '<n>MainWindow</n>' exists: {n_tag_present}")
    print(f"  '<name>MainWindow</name>' exists: {name_tag_present}")
    
    # Direct string replacements
    new_content = content
    
    # First replace the comment
    comment_replaced = new_content.replace('# Translation file with correct <n> tags', 
                                        '# Translation file with correct <name> tags')
    
    comment_replaced_count = 0
    if comment_replaced != new_content:
        comment_replaced_count = 1
        new_content = comment_replaced
    
    # Now replace the XML tag
    tag_replaced = new_content.replace('<n>MainWindow</n>', '<name>MainWindow</name>')
    
    tag_replaced_count = 0
    if tag_replaced != new_content:
        tag_replaced_count = 1
        new_content = tag_replaced
    
    # Check if anything actually changed
    changed = content != new_content
    
    print(f"After replacement:")
    print(f"  Comment replacements: {comment_replaced_count}")
    print(f"  Tag replacements: {tag_replaced_count}")
    print(f"  Content changed: {changed}")
    
    if changed:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"File updated successfully")
    else:
        print(f"No changes were made to the file")
    
    return 0

if __name__ == "__main__":
    exit(main()) 