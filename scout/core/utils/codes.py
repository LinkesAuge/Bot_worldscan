"""
Application Exit Codes

This module defines exit codes used by the application for different 
scenarios such as restart, update, etc.
"""

class Codes:
    """
    Exit codes used by the application.
    
    These codes signal the application launcher or wrapper about
    special actions to take after the application exits.
    """
    
    # Normal exit code (0) - standard successful termination
    NORMAL_EXIT_CODE = 0
    
    # Restart code (42) - application should be restarted
    RESTART_CODE = 42
    
    # Update code (43) - application should perform an update
    UPDATE_CODE = 43
    
    # Error code (1) - application encountered an error
    ERROR_CODE = 1
    
    # Critical error code (2) - application encountered a critical error
    CRITICAL_ERROR_CODE = 2 