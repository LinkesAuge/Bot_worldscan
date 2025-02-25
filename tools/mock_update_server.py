#!/usr/bin/env python3
"""
Mock Update Server

This script creates a simple HTTP server that mocks the Scout application's update API.
It responds to requests with predefined update information for testing the update system.
"""

import os
import sys
import json
import logging
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 8000
DEFAULT_LATEST_VERSION = "1.0.1"
DEFAULT_DOWNLOAD_URL = "https://download.example.com/Scout_Setup_1.0.1.exe"


class MockUpdateHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the mock update server."""
    
    def do_POST(self):
        """Handle POST requests."""
        # Parse URL
        parsed_url = urlparse(self.path)
        
        # Check if this is an update check request
        if parsed_url.path == "/updates":
            self._handle_update_check()
        else:
            # Not found
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Not Found")
    
    def _handle_update_check(self):
        """Handle update check requests."""
        # Get request content length
        content_length = int(self.headers.get("Content-Length", 0))
        
        # Read request body
        request_data = self.rfile.read(content_length)
        
        try:
            # Parse request JSON
            request = json.loads(request_data.decode("utf-8"))
            
            # Log the request
            logger.info(f"Update check request: {request}")
            
            # Get current version from request
            current_version = request.get("current_version", "0.0.0")
            
            # Prepare response
            response_data = {
                "latest_version": self.server.latest_version,
                "download_url": self.server.download_url,
                "update_info": f"Update from {current_version} to {self.server.latest_version}",
                "changelog": (
                    "<ul>"
                    "<li>New feature: Automatic updates</li>"
                    "<li>Improved detection accuracy</li>"
                    "<li>Fixed various bugs</li>"
                    "</ul>"
                )
            }
            
            # Log the response
            logger.info(f"Update check response: {response_data}")
            
            # Send response
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode("utf-8"))
            
        except Exception as e:
            # Log error
            logger.error(f"Error handling update check: {e}")
            
            # Send error response
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(f"Error: {str(e)}".encode("utf-8"))
    
    def log_message(self, format, *args):
        """Override default logging to use our logger."""
        logger.info(f"{self.address_string()} - {format % args}")


class MockUpdateServer(HTTPServer):
    """HTTP server with update configuration."""
    
    def __init__(
        self, 
        server_address, 
        RequestHandlerClass, 
        latest_version=DEFAULT_LATEST_VERSION,
        download_url=DEFAULT_DOWNLOAD_URL
    ):
        super().__init__(server_address, RequestHandlerClass)
        self.latest_version = latest_version
        self.download_url = download_url


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Mock update server for Scout")
    
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"Host to listen on (default: {DEFAULT_HOST})"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Port to listen on (default: {DEFAULT_PORT})"
    )
    
    parser.add_argument(
        "--latest-version",
        default=DEFAULT_LATEST_VERSION,
        help=f"Latest version to report (default: {DEFAULT_LATEST_VERSION})"
    )
    
    parser.add_argument(
        "--download-url",
        default=DEFAULT_DOWNLOAD_URL,
        help=f"Download URL to provide (default: {DEFAULT_DOWNLOAD_URL})"
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    # Parse arguments
    args = parse_args()
    
    # Log startup
    logger.info(f"Starting mock update server on {args.host}:{args.port}")
    logger.info(f"Latest version: {args.latest_version}")
    logger.info(f"Download URL: {args.download_url}")
    
    # Create server
    server = MockUpdateServer(
        (args.host, args.port),
        MockUpdateHandler,
        args.latest_version,
        args.download_url
    )
    
    try:
        # Run server
        logger.info("Server running, press Ctrl+C to stop")
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.server_close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 