"""
Fixed versions of methods for settings_tab.py
"""

def on_save_clicked():
    """Fixed _on_save_clicked method."""
    return """    def _on_save_clicked(self, show_dialog: bool = True) -> None:
        # Save settings and optionally show confirmation dialog.
        # Collect settings from UI
        self._collect_settings_from_ui()
        
        # Save settings
        self.settings_model.save()
        logger.info("Settings saved successfully")
        
        # Reset modified flag
        self._modified = False
        
        # Clear the status label
        if hasattr(self, 'status_label') and self.status_label is not None:
            self.status_label.setText("")
        
        # Disable save button
        if hasattr(self, 'save_button') and self.save_button is not None:
            self.save_button.setEnabled(False)
        
        # Show confirmation dialog if requested
        if show_dialog:
            QMessageBox.information(self, tr("Settings Saved"),
                                  tr("Your settings have been saved successfully."),
                                  QMessageBox.StandardButton.Ok)
"""

def on_reset_clicked():
    """Fixed _on_reset_clicked method."""
    return """    def _on_reset_clicked(self) -> None:
        # Handle reset button click.
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
                logger.error(f"Error resetting settings: {{str(e)}}")
                
                # Show error message
                QMessageBox.critical(
                    self,
                    tr("Error"),
                    tr("Failed to reset settings: {{0}}").format(str(e)),
                    QMessageBox.StandardButton.Ok
                )
""" 