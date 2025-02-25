"""
Simple patch to add status_label to _auto_save_settings method
"""

def main():
    file_path = 'scout/ui/views/settings_tab.py'
    
    try:
        # Read original content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if status_label already exists in _create_ui
        if 'self.status_label = QLabel("")' in content:
            print("Status label already exists in _create_ui method.")
        else:
            print("Adding status label to _create_ui method...")
            
            # Find the button bar code block
            button_bar_end = "main_layout.addLayout(button_bar)"
            
            # Add status label before button bar
            status_label_code = """        # Create status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #FF6600;")  # Orange color for visibility
        
        # Add status label and button bar to main layout
        main_layout.addWidget(self.status_label)
        """
            
            # Replace button bar addition with code that includes status label
            content = content.replace(
                f"        # Add button bar to main layout\n        {button_bar_end}", 
                status_label_code + f"        {button_bar_end}"
            )
        
        # Write updated content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Successfully updated {file_path}")
        return True
    
    except Exception as e:
        print(f"Error updating file: {e}")
        return False

if __name__ == "__main__":
    main() 