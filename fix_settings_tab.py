"""
Fix Settings Tab

This script fixes syntax errors in the settings_tab.py file.
"""

import re

def fix_settings_tab():
    file_path = 'scout/ui/views/settings_tab.py'
    
    # Read the current content
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace _on_reset_clicked method
    reset_method = '''    def _on_reset_clicked(self) -> None:
        """Handle reset button click."""
        # Ask for confirmation
        response = QMessageBox.question(
            self,
            tr("Reset Settings"),
            tr("Are you sure you want to reset all settings to their default values? This cannot be undone."),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if response == QMessageBox.StandardButton.Yes:
            try:
                # Reset settings
                self.settings_model.reset_to_defaults()
                
                # Reload UI with default values
                self._load_settings_to_ui()
                
                # Mark as not changed
                self._modified = False
                
                # Update UI elements
                if hasattr(self, 'save_button') and self.save_button is not None:
                    self.save_button.setEnabled(False)
                
                if hasattr(self, 'status_label') and self.status_label is not None:
                    self.status_label.setText("")
                
                # Show success message
                QMessageBox.information(
                    self,
                    tr("Reset Complete"),
                    tr("Settings have been reset to their default values."),
                    QMessageBox.StandardButton.Ok
                )
            except Exception as e:
                # Log error
                logger.error(f"Error resetting settings: {str(e)}")
                
                # Show error message
                QMessageBox.critical(
                    self,
                    tr("Error"),
                    tr("Failed to reset settings: {0}").format(str(e)),
                    QMessageBox.StandardButton.Ok
                )
'''
    
    # Find the start and end of the _on_reset_clicked method
    reset_pattern = re.compile(r'^\s{4}def _on_reset_clicked.*?(?=^\s{4}def)', re.DOTALL | re.MULTILINE)
    new_content = reset_pattern.sub(reset_method, content)
    
    # Write the corrected content back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"Successfully updated {file_path}")

if __name__ == "__main__":
    fix_settings_tab() 