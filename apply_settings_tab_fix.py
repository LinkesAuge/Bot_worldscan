"""
Apply Settings Tab Fix

This script applies fixed versions of methods to the settings_tab.py file.
"""

import re
import sys
from settings_tab_fixed import on_save_clicked, on_reset_clicked

def apply_fixes(file_path):
    print(f"Reading file {file_path}...")
    
    # Read the original file
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"File read successfully: {len(content)} characters")
    except Exception as e:
        print(f"Error reading file: {e}")
        return False
    
    # Get fixed methods
    save_method = on_save_clicked()
    reset_method = on_reset_clicked()
    
    # Apply fixes using line-based replacement to avoid regex complexity
    lines = content.split('\n')
    
    # Find and replace the methods
    save_start_idx = None
    reset_start_idx = None
    save_end_idx = None
    reset_end_idx = None
    
    for i, line in enumerate(lines):
        if line.strip() == 'def _on_save_clicked(self, show_dialog: bool = True) -> None:':
            save_start_idx = i
        elif line.strip() == 'def _on_reset_clicked(self) -> None:':
            reset_start_idx = i
    
    if save_start_idx is None:
        print("Could not find _on_save_clicked method")
        return False
    
    if reset_start_idx is None:
        print("Could not find _on_reset_clicked method")
        return False
    
    # Find the next method after _on_save_clicked
    for i in range(save_start_idx + 1, len(lines)):
        if lines[i].strip().startswith('def '):
            save_end_idx = i
            break
    
    # Find the next method after _on_reset_clicked
    for i in range(reset_start_idx + 1, len(lines)):
        if lines[i].strip().startswith('def '):
            reset_end_idx = i
            break
    
    if save_end_idx is None or reset_end_idx is None:
        print("Could not determine method boundaries")
        return False
    
    # Create new content with fixes
    new_content = []
    i = 0
    
    while i < len(lines):
        if i == save_start_idx:
            # Replace _on_save_clicked method
            save_lines = save_method.strip().split('\n')
            new_content.extend(save_lines)
            i = save_end_idx
        elif i == reset_start_idx:
            # Replace _on_reset_clicked method
            reset_lines = reset_method.strip().split('\n')
            new_content.extend(reset_lines)
            i = reset_end_idx
        else:
            new_content.append(lines[i])
            i += 1
    
    # Write the fixed content
    fixed_content = '\n'.join(new_content)
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        print(f"Fixed content written to {file_path}")
        return True
    except Exception as e:
        print(f"Error writing fixed content: {e}")
        return False

if __name__ == "__main__":
    file_path = 'scout/ui/views/settings_tab.py'
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    
    success = apply_fixes(file_path)
    
    if success:
        print("Fixes applied successfully!")
    else:
        print("Failed to apply fixes.") 