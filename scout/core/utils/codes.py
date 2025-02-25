"""
Application Exit Codes

This module defines exit codes used by the Scout application
to indicate different termination states.
"""

from enum import IntEnum


class Codes(IntEnum):
    """
    Exit codes for the Scout application.
    
    These codes indicate different termination states of the application
    and can be used to determine the reason for application exit.
    """
    
    # Normal exit
    SUCCESS = 0
    
    # Update-related exit codes
    UPDATE_CODE = 10  # Application is exiting to apply an update
    
    # Error-related exit codes
    GENERAL_ERROR = 1       # General application error
    CONFIG_ERROR = 2        # Configuration error
    RESOURCE_ERROR = 3      # Resource loading error
    INITIALIZATION_ERROR = 4  # Application initialization error
    
    # User-initiated exit codes
    USER_CANCEL = 20   # User canceled operation
    USER_LOGOUT = 21   # User logged out
    
    # System-related exit codes
    SYSTEM_REQUEST = 30  # System requested termination
    
    @classmethod
    def get_description(cls, code: int) -> str:
        """
        Get a human-readable description for an exit code.
        
        Args:
            code: The exit code to describe
            
        Returns:
            String description of the exit code
        """
        descriptions = {
            cls.SUCCESS: "Application exited normally",
            cls.UPDATE_CODE: "Application exited for update",
            cls.GENERAL_ERROR: "Application encountered a general error",
            cls.CONFIG_ERROR: "Application encountered a configuration error",
            cls.RESOURCE_ERROR: "Application failed to load required resources",
            cls.INITIALIZATION_ERROR: "Application failed to initialize",
            cls.USER_CANCEL: "User canceled operation",
            cls.USER_LOGOUT: "User logged out",
            cls.SYSTEM_REQUEST: "System requested application termination"
        }
        
        return descriptions.get(code, f"Unknown exit code: {code}") 