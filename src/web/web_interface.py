#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ROM Sorter Pro - Web Interface v2.1.8

This module implements a web interface for ROM Sorter Pro that enables
remote access to the application's functions and provides a modern
dashboard for ROM management.

Features:
- RESTful API for ROM management
- Web-based dashboard
- Remote access to ROM database
- Support for file upload and download
- WebSocket for real-time updates

NOTE: This is a simplified version of the web interface.
The main implementation is in src/web_interface.py.
This module provides backward compatibility for old imports.
"""

# Compatibility imports
import sys
import logging
from importlib import import_module
from pathlib import Path

logger = logging.getLogger(__name__)

# Add parent directory to path to allow importing src.web_interface
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import the main web interface implementation
try:
    # Import from parent module without referencing 'src'
    web_interface_module = import_module('web_interface')
    # Re-export all symbols from the main module
    for attr in dir(web_interface_module):
        if not attr.startswith('_'):  # Skip private attributes
            globals()[attr] = getattr(web_interface_module, attr)
    logger.debug("Successfully imported web_interface")
except ImportError as e:
    logger.error(f"Failed to import web_interface: {e}")
    # If import fails, keep the simplified version

import os
import json
import logging
import threading
import webbrowser
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path
import time
import hashlib
import base64
import shutil
import tempfile
import mimetypes
from datetime import datetime, timedelta

# Flask for web interface
try:
    from flask import (
        Flask, request, jsonify, send_from_directory, redirect,
        render_template_string, url_for, Response, session, send_file
    )
    from flask_cors import CORS
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False
    # Dummy class for type hints
    class Flask:
        pass

# Configure logger
logger = logging.getLogger(__name__)

# Paths for the web interface
WEB_ROOT = os.path.join(os.path.dirname(__file__), '..', '..', 'web')
STATIC_PATH = os.path.join(WEB_ROOT, 'static')
TEMPLATES_PATH = os.path.join(WEB_ROOT, 'templates')
UPLOAD_PATH = os.path.join(WEB_ROOT, 'uploads')

# Ensure directories exist
os.makedirs(STATIC_PATH, exist_ok=True)
os.makedirs(TEMPLATES_PATH, exist_ok=True)
os.makedirs(UPLOAD_PATH, exist_ok=True)

# Token management for API access
API_TOKENS = {}
TOKEN_EXPIRY = timedelta(hours=24)

# API version
API_VERSION = "2.1.8"


class WebInterfaceError(Exception):
    """Base class for web interface errors."""
    pass


class WebInterface:
    """Implements a web interface for ROM Sorter Pro."""

    def __init__(self, host: str = '127.0.0.1', port: int = 8080, debug: bool = False):
        """
        Initializes the web interface.

        Args:
            host: Hostname or IP address on which the server listens
            port: Port on which the server listens
            debug: Enable debug mode
        """
        self.host = host
        self.port = port
        self.debug = debug
        self.app = None
        self.server_thread = None
        self.is_running = False

        # Check if Flask is available
        if not HAS_FLASK:
            logger.error("Flask is not installed. The web interface is not available.")
            raise ImportError("Flask is not installed. Install it with 'pip install flask flask-cors'.")

    def _create_app(self) -> Flask:
        """
        Creates the Flask application for the web interface.

        Returns:
            Flask application
        """
        app = Flask(__name__,
                  static_folder=STATIC_PATH,
                  template_folder=TEMPLATES_PATH)

        # Configuration
        app.secret_key = os.urandom(24)
        app.config['UPLOAD_FOLDER'] = UPLOAD_PATH
        app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB max upload

        # CORS configuration for API access
        CORS(app, resources={r"/api/*": {"origins": "*"}})

        # Enable CORS for API access
        CORS(app, resources={r"/api/*": {"origins": "*"}})

        # Routes for web pages
        @app.route('/')
        def index():
            # If an index.html file exists in the "templates" directory, use it
            if os.path.exists(os.path.join(TEMPLATES_PATH, 'index.html')):
                return render_template_string(
                    open(os.path.join(TEMPLATES_PATH, 'index.html')).read()
                )

            # OtherWise Generates A Simple Dashboard
            return render_template_string(self._generate_dashboard_template())

        @app.route('/login', methods=['GET', 'POST'])
        def login():
            if request.method == 'POST':
                username = request.form.get('username')
                password = request.form.get('password')

                # Simple authentication - in a real application you would use
                # password hashing and secure storage
                if username == 'admin' and password == 'password':
                    session['logged_in'] = True
                    return redirect(url_for('index'))

                return render_template_string(
                    self._generate_login_template(error="Invalid login credentials")
                )

            return render_template_string(self._generate_login_template())

        @app.route('/logout')
        def logout():
            session.pop('logged_in', None)
            return redirect(url_for('login'))

        # API routes
        @app.route('/api/v1/status', methods=['GET'])
        def api_status():
            return jsonify({
                'status': 'online',
                'version': API_VERSION,
                'timestamp': datetime.now().isoformat()
            })

        @app.route('/api/v1/auth/token', methods=['POST'])
        def get_token():
            # Simple API token generation - in a real application you would use
            # secure authentication
            if request.json and 'api_key' in request.json:
                api_key = request.json['api_key']

                # Check API key (example)
                if api_key == 'test_key':
                    token = self._generate_token()
                    return jsonify({
                        'token': token,
                        'expires': (datetime.now() + TOKEN_EXPIRY).isoformat()
                    })

            return jsonify({'error': 'Invalid API key'}), 401

        @app.route('/api/v1/roms', methods=['GET'])
        def list_roms():
            # Check token authentication
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({'error': 'Not authorized'}), 401

            token = auth_header[7:]  # Remove "Bearer "
            if not self._validate_token(token):
                return jsonify({'error': 'Invalid or expired token'}), 401

            # Example implementation - in a real application, the actual
            # ROM data would be retrieved from the database
            roms = [
                {'id': 1, 'name': 'Super Mario Bros.', 'platform': 'NES', 'size': 32768},
                {'id': 2, 'name': 'Sonic the Hedgehog', 'platform': 'Genesis', 'size': 524288},
                {'id': 3, 'name': 'Final Fantasy VII', 'platform': 'PlayStation', 'size': 734003200}
            ]

            return jsonify({'roms': roms})

        @app.route('/api/v1/roms/<int:rom_id>', methods=['GET'])
        def get_rom(rom_id):
            # Check token authentication
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({'error': 'Not authorized'}), 401

            token = auth_header[7:]  # Remove "Bearer "
            if not self._validate_token(token):
                return jsonify({'error': 'Invalid or expired token'}), 401

            # Example implementation - in a real application, the actual
            # ROM data would be retrieved from the database
            roms = {
                1: {'id': 1, 'name': 'Super Mario Bros.', 'platform': 'NES', 'size': 32768},
                2: {'id': 2, 'name': 'Sonic the Hedgehog', 'platform': 'Genesis', 'size': 524288},
                3: {'id': 3, 'name': 'Final Fantasy VII', 'platform': 'PlayStation', 'size': 734003200}
            }

            if rom_id in roms:
                return jsonify(roms[rom_id])

            return jsonify({'error': 'ROM not found'}), 404

        @app.route('/api/v1/upload', methods=['POST'])
        def upload_file():
            # Check token authentication
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({'error': 'Not authorized'}), 401

            token = auth_header[7:]  # Remove "Bearer "
            if not self._validate_token(token):
                return jsonify({'error': 'Invalid or expired token'}), 401

            # Check if a file is in the request
            if 'file' not in request.files:
                return jsonify({'error': 'No file in request'}), 400

            file = request.files['file']

            # Check if a filename was selected
            if file.filename == '':
                return jsonify({'error': 'No filename selected'}), 400

            # Save the file if it exists
            if file:
                filename = os.path.basename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)

                return jsonify({
                    'success': True,
                    'filename': filename,
                    'size': os.path.getsize(filepath)
                })

            return jsonify({'error': 'Error uploading file'}), 500

        # Error handling
        @app.errorhandler(404)
        def not_found(error):
            return jsonify({'error': 'Not found'}), 404

        @app.errorhandler(500)
        def server_error(error):
            return jsonify({'error': 'Server error'}), 500

        return app

    def _generate_dashboard_template(self) -> str:
        """
        Generates a simple dashboard template.

        Returns:
            HTML template as a string
        """
        return '''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>ROM Sorter Pro - Dashboard</title>
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0;
                    padding: 0;
                    background-color: #f5f5f5;
                    color: #333;
                }
                header {
                    background-color: #2c3e50;
                    color: white;
                    padding: 1rem;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 1rem;
                }
                .dashboard {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                    gap: 1rem;
                    margin-top: 1rem;
                }
                .card {
                    background-color: white;
                    border-radius: 5px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                    padding: 1rem;
                    transition: transform 0.3s ease;
                }
                .card:hover {
                    transform: translateY(-5px);
                }
                .card h3 {
                    margin-top: 0;
                    color: #2c3e50;
                }
                .footer {
                    margin-top: 2rem;
                    padding: 1rem;
                    text-align: center;
                    color: #666;
                    font-size: 0.8rem;
                }
                .upload-area {
                    border: 2px dashed #ccc;
                    border-radius: 5px;
                    padding: 2rem;
                    text-align: center;
                    margin: 1rem 0;
                    background-color: #f9f9f9;
                    cursor: pointer;
                }
                .upload-area:hover {
                    border-color: #2c3e50;
                    background-color: #f0f0f0;
                }
                button {
                    background-color: #2c3e50;
                    color: white;
                    border: none;
                    padding: 0.5rem 1rem;
                    border-radius: 3px;
                    cursor: pointer;
                    font-size: 1rem;
                    transition: background-color 0.3s ease;
                }
                button:hover {
                    background-color: #1a252f;
                }
                input[type="file"] {
                    display: none;
                }
            </style>
        </head>
        <body>
            <header>
                <div class="container">
                    <h1>ROM Sorter Pro</h1>
                    <p>Web Interface for ROM Management</p>
                </div>
            </header>

            <div class="container">
                <h2>Dashboard</h2>

                <div class="upload-area" id="uploadArea">
                    <h3>Upload ROMs</h3>
                    <p>Drag files here or click to select files</p>
                    <input type="file" id="fileInput" multiple>
                    <button id="uploadButton">Select Files</button>
                </div>

                <div class="dashboard">
                    <div class="card">
                        <h3>Statistics</h3>
                        <p>Total ROMs: <strong>0</strong></p>
                        <p>Sorted ROMs: <strong>0</strong></p>
                        <p>Unidentified ROMs: <strong>0</strong></p>
                    </div>

                    <div class="card">
                        <h3>Recent Activity</h3>
                        <p>No activity available</p>
                    </div>

                    <div class="card">
                        <h3>API Status</h3>
                        <p>Status: <span id="apiStatus">Checking...</span></p>
                        <p>Version: <span id="apiVersion">-</span></p>
                        <button id="checkApiButton">Check API</button>
                    </div>
                </div>
            </div>

            <footer class="footer">
                <p>ROM Sorter Pro &copy; 2025 | Web Interface Version 2.1.8</p>
            </footer>

            <script>
                // JavaScript for dashboard functionality
                document.addEventListener('DOMContentLoaded', function() {
                    // Upload area
                    const uploadArea = document.getElementById('uploadArea');
                    const fileInput = document.getElementById('fileInput');
                    const uploadButton = document.getElementById('uploadButton');

                    uploadArea.addEventListener('dragover', function(e) {
                        e.preventDefault();
                        uploadArea.style.borderColor = '#2c3e50';
                        uploadArea.style.backgroundColor = '#f0f0f0';
                    });

                    uploadArea.addEventListener('dragleave', function() {
                        uploadArea.style.borderColor = '#ccc';
                        uploadArea.style.backgroundColor = '#f9f9f9';
                    });

                    uploadArea.addEventListener('drop', function(e) {
                        e.preventDefault();
                        uploadArea.style.borderColor = '#ccc';
                        uploadArea.style.backgroundColor = '#f9f9f9';

                        const files = e.dataTransfer.files;
                        handleFiles(files);
                    });

                    uploadButton.addEventListener('click', function() {
                        fileInput.click();
                    });

                    fileInput.addEventListener('change', function() {
                        handleFiles(fileInput.files);
                    });

                    function handleFiles(files) {
                        if (files.length === 0) return;

                        // In a real application, the upload would happen via AJAX here
                        console.log(`${files.length} files selected`);
                        alert(`${files.length} files have been selected. In a real application, these would now be uploaded.`);
                    }

                    // Check API status
                    const checkApiButton = document.getElementById('checkApiButton');
                    checkApiButton.addEventListener('click', checkApiStatus);

                    // Check API status on load
                    checkApiStatus();

                    function checkApiStatus() {
                        const apiStatus = document.getElementById('apiStatus');
                        const apiVersion = document.getElementById('apiVersion');

                        apiStatus.textContent = 'Checking...';
                        apiVersion.textContent = '-';

                        fetch('/api/v1/status')
                            .then(response => response.json())
                            .then(data => {
                                apiStatus.textContent = data.status;
                                apiVersion.textContent = data.version;
                                apiStatus.style.color = 'green';
                            })
                            .catch(error => {
                                console.error('Error checking API status:', error);
                                apiStatus.textContent = 'Offline';
                                apiStatus.style.color = 'red';
                            });
                    }
                });
            </script>
        </body>
        </html>
        '''

    def _generate_login_template(self, error: str = None) -> str:
        """
        Generates a simple login template.

        Args:
            error: Optional error message

        Returns:
            HTML template as a string
        """
        return f'''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>ROM Sorter Pro - Login</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0;
                    padding: 0;
                    background-color: #f5f5f5;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                }}
                .login-container {{
                    background-color: white;
                    border-radius: 5px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    padding: 2rem;
                    width: 100%;
                    max-width: 400px;
                }}
                .login-container h1 {{
                    margin-top: 0;
                    color: #2c3e50;
                    text-align: center;
                }}
                .form-group {{
                    margin-bottom: 1rem;
                }}
                label {{
                    display: block;
                    margin-bottom: 0.5rem;
                    color: #333;
                }}
                input {{
                    width: 100%;
                    padding: 0.5rem;
                    border: 1px solid #ddd;
                    border-radius: 3px;
                    font-size: 1rem;
                }}
                button {{
                    width: 100%;
                    background-color: #2c3e50;
                    color: white;
                    border: none;
                    padding: 0.75rem;
                    border-radius: 3px;
                    cursor: pointer;
                    font-size: 1rem;
                    margin-top: 1rem;
                }}
                button:hover {{
                    background-color: #1a252f;
                }}
                .error-message {{
                    color: #e74c3c;
                    margin-bottom: 1rem;
                    text-align: center;
                }}
            </style>
        </head>
        <body>
            <div class="login-container">
                <h1>ROM Sorter Pro</h1>

                {f'<div class="error-message">{error}</div>' if error else ''}

                <form action="/login" method="post">
                    <div class="form-group">
                        <label for="username">Username</label>
                        <input type="text" id="username" name="username" required>
                    </div>
                    <div class="form-group">
                        <label for="password">Password</label>
                        <input type="password" id="password" name="password" required>
                    </div>
                    <button type="submit">Login</button>
                </form>
            </div>
        </body>
        </html>
        '''

    def _generate_token(self) -> str:
        """
        Generates an API token.

        Returns:
            API token
        """
        # Simple token generation - in a real application you would
        # use a more secure method
        token = base64.b64encode(os.urandom(32)).decode('utf-8')
        API_TOKENS[token] = datetime.now() + TOKEN_EXPIRY
        return token

    def _validate_token(self, token: str) -> bool:
        """
        Validates an API token.

        Args:
            token: Token to validate

        Returns:
            True if the token is valid, otherwise False
        """
        if token not in API_TOKENS:
            return False

        expiry = API_TOKENS[token]
        if datetime.now() > expiry:
            # Token has expired
            del API_TOKENS[token]
            return False

        return True

    def start(self) -> None:
        """Starts the web server in a separate thread."""
        if self.is_running:
            logger.warning("Web interface is already running")
            return

        try:
            self.app = self._create_app()

            def run_server():
                self.app.run(host=self.host, port=self.port, debug=self.debug)

            # Start the server in a separate thread
            self.server_thread = threading.Thread(target=run_server)
            self.server_thread.daemon = True
            self.server_thread.start()

            self.is_running = True
            logger.info(f"Web interface started at http://{self.host}:{self.port}")

            # Wait short to ensure that the server has started
            time.sleep(1)

            # Open the browser if the server is running on localhost
            if self.host in ['127.0.0.1', 'localhost']:
                webbrowser.open(f"http://{self.host}:{self.port}")

        except Exception as e:
            logger.error(f"Error starting web interface: {e}")
            raise WebInterfaceError(f"Error starting web interface: {e}")

    def stop(self) -> None:
        """Stops the web server."""
        if not self.is_running:
            logger.warning("Web interface is not running")
            return

        # Flask does not have a simple way to stop the server
        # In a real application, you would implement a shutdown function here
        self.is_running = False
        logger.info("Web interface stopped")


def start_web_interface(host: str = '127.0.0.1', port: int = 8080,
                       open_browser: bool = True) -> WebInterface:
    """
    Starts the web interface for ROM Sorter Pro.

    Args:
        host: Hostname or IP address on which the server listens
        port: Port on which the server listens
        open_browser: Whether to automatically open the browser

    Returns:
        WebInterface instance
    """
    # Check if Flask is installed
    if not HAS_FLASK:
        logger.error("Flask is not installed. The web interface is not available.")
        raise ImportError("Flask is not installed. Install it with 'pip install flask flask-cors'.")

    web_interface = WebInterface(host=host, port=port, debug=False)
    web_interface.start()

    return web_interface


# Example for using the web interface
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO,
                      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    try:
        # Start the web interface
        web_interface = start_web_interface()

        # Keep the program running until interrupted
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping the web interface...")
            web_interface.stop()

    except ImportError as e:
        print(f"Error: {e}")
        print("Install Flask with: pip install flask flask-cors")

    except WebInterfaceError as e:
        print(f"Error: {e}")

    except Exception as e:
        print(f"Unexpected error: {e}")
