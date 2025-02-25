"""
Psutil Stub Module

This is a simple stub implementation of the psutil module, providing only the
functionality required by the Scout application. This allows the application to
run without installing the actual psutil dependency.

For production use, the real psutil module should be installed via pip.
"""

import os
import time
import platform

class Process:
    """Stub implementation of psutil.Process class."""
    
    def __init__(self, pid=None):
        """Initialize the Process object with a pid."""
        self.pid = pid if pid is not None else os.getpid()
    
    def memory_info(self):
        """Return a named tuple with memory usage info."""
        # Return a stub object with rss and vms attributes
        class MemInfo:
            def __init__(self):
                self.rss = 0  # Resident Set Size
                self.vms = 0  # Virtual Memory Size
        
        return MemInfo()
    
    def cpu_percent(self, interval=None):
        """Return CPU usage percentage."""
        # Stub implementation that returns a reasonable value
        return 5.0
    
    def memory_percent(self):
        """Return memory usage as a percentage of system memory."""
        # Stub implementation
        return 2.0
    
    def num_threads(self):
        """Return the number of threads used by the process."""
        # Stub implementation
        return 4
    
    def cpu_times(self):
        """Return CPU times as a named tuple."""
        # Return a stub object with attributes
        class CPUTimes:
            def __init__(self):
                self.user = 0.0
                self.system = 0.0
        
        return CPUTimes()

# Stub for psutil.virtual_memory()
def virtual_memory():
    """Return virtual memory statistics as a named tuple."""
    # Return a stub object with basic attributes
    class VirtualMemory:
        def __init__(self):
            self.total = 8 * 1024 * 1024 * 1024  # 8 GB
            self.available = 4 * 1024 * 1024 * 1024  # 4 GB
            self.used = 4 * 1024 * 1024 * 1024  # 4 GB
            self.percent = 50.0
    
    return VirtualMemory()

# Stub for psutil.cpu_count()
def cpu_count(logical=True):
    """Return the number of CPUs in the system."""
    return 4 if logical else 2

# Stub for psutil.cpu_percent()
def cpu_percent(interval=None, percpu=False):
    """Return CPU utilization as a percentage."""
    if percpu:
        return [5.0, 8.0, 3.0, 7.0]  # Sample values for multiple CPUs
    else:
        return 5.0  # Sample value for overall CPU usage

# Stub for psutil.disk_usage()
def disk_usage(path):
    """Return disk usage statistics for the given path."""
    # Return a stub object with basic attributes
    class DiskUsage:
        def __init__(self):
            self.total = 500 * 1024 * 1024 * 1024  # 500 GB
            self.used = 250 * 1024 * 1024 * 1024  # 250 GB
            self.free = 250 * 1024 * 1024 * 1024  # 250 GB
            self.percent = 50.0
    
    return DiskUsage()

# Additional stub functions as needed
def boot_time():
    """Return system boot time as a timestamp."""
    return time.time() - 86400  # 1 day ago

def sensors_temperatures():
    """Return hardware temperatures."""
    return {}  # Empty dict as stub 