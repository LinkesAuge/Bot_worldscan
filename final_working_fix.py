#!/usr/bin/env python3

def fix_file():
    """Fix the file using byte replacement with manually built strings."""
    file_path = 'scout/tests/translations/test_check_translations.py'
    
    # Read the file content as bytes
    with open(file_path, 'rb') as f:
        content = f.read()
    
    # Build the tag strings character by character to avoid editor issues
    n_open = ord('<')
    n_n = ord('n')
    n_close = ord('>')
    n_slash = ord('/')
    
    # Build old and new tags
    old_tag = bytes([n_open, n_n, n_close]) + b'MainWindow' + bytes([n_open, n_slash, n_n, n_close])
    
    # For name tag
    n_a = ord('a')
    n_m = ord('m')
    n_e = ord('e')
    
    new_tag = bytes([n_open, n_n, n_a, n_m, n_e, n_close]) + b'MainWindow' + bytes([n_open, n_slash, n_n, n_a, n_m, n_e, n_close])
    
    # Replace the content
    content = content.replace(old_tag, new_tag)
    
    # Replace the comment
    old_comment = b'# Translation file with correct <n> tags'
    new_comment = b'# Translation file with correct <name> tags'
    content = content.replace(old_comment, new_comment)
    
    # Write back to the file
    with open(file_path, 'wb') as f:
        f.write(content)
    
    print(f"File updated: {file_path}")
    
    # Verify the changes
    with open(file_path, 'rb') as f:
        updated = f.read()
    
    print(f"File contains new tag: {new_tag in updated}")
    print(f"File no longer contains old tag: {old_tag not in updated}")

if __name__ == "__main__":
    fix_file() 