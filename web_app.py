#!/usr/bin/env python
"""
Web Application for ST_Faktura - Google Cloud Run Deployment

This Flask application provides a web interface for the ST_Faktura invoice
management system, allowing it to run on Google Cloud Run.
"""

import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename

# Import ST_Faktura modules
from google_sheets_client import GoogleSheetsClient
from CreateCustomer import create_customer
from CreateTask import create_task
from CreateInvoice import create_invoice
from Tool_MyCompanyDetails import manage_company_details
from Tool_SearchOldInvoices import search_invoices

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Get configuration from environment
PORT = int(os.environ.get('PORT', 8080))
SPREADSHEET_ID = os.environ.get('DEFAULT_SPREADSHEET_ID', '')


def get_sheets_client():
    """Get Google Sheets client with service account authentication."""
    try:
        return GoogleSheetsClient(auth_method="service_account")
    except Exception as e:
        logger.error(f"Failed to create sheets client: {e}")
        raise


@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('index.html')


@app.route('/api/health')
def health_check():
    """Health check endpoint for Cloud Run."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'st-faktura'
    })


@app.route('/api/customers', methods=['GET'])
def get_customers():
    """Get all customers from Google Sheets."""
    try:
        client = get_sheets_client()
        customers = client.read_sheet(SPREADSHEET_ID, "Customers!A:H")
        return jsonify({
            'success': True,
            'customers': customers[1:] if len(customers) > 1 else [],  # Skip header
            'headers': customers[0] if customers else []
        })
    except Exception as e:
        logger.error(f"Error getting customers: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/customers', methods=['POST'])
def add_customer():
    """Add a new customer."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['customer_id', 'company_name', 'address', 'cvr', 
                          'zip_code', 'town', 'phone', 'email']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing field: {field}'}), 400
        
        # Add customer to Google Sheets
        client = get_sheets_client()
        customer_data = [
            data['customer_id'],
            data['company_name'],
            data['address'],
            data['cvr'],
            data['zip_code'],
            data['town'],
            data['phone'],
            data['email']
        ]
        
        client.append_to_sheet(SPREADSHEET_ID, "Customers!A:H", [customer_data])
        
        return jsonify({
            'success': True,
            'message': 'Customer added successfully',
            'customer': customer_data
        })
    except Exception as e:
        logger.error(f"Error adding customer: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """Get all tasks from Google Sheets."""
    try:
        client = get_sheets_client()
        tasks = client.read_sheet(SPREADSHEET_ID, "Tasks!A:E")
        return jsonify({
            'success': True,
            'tasks': tasks[1:] if len(tasks) > 1 else [],
            'headers': tasks[0] if tasks else []
        })
    except Exception as e:
        logger.error(f"Error getting tasks: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/tasks', methods=['POST'])
def add_task():
    """Add a new task."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['date', 'customer_name', 'task_type', 'description', 'time_minutes']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing field: {field}'}), 400
        
        # Add task to Google Sheets
        client = get_sheets_client()
        task_data = [
            data['date'],
            data['customer_name'],
            data['task_type'],
            data['description'],
            str(data['time_minutes'])
        ]
        
        client.append_to_sheet(SPREADSHEET_ID, "Tasks!A:E", [task_data])
        
        return jsonify({
            'success': True,
            'message': 'Task added successfully',
            'task': task_data
        })
    except Exception as e:
        logger.error(f"Error adding task: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/task-types', methods=['GET'])
def get_task_types():
    """Get all task types from Google Sheets."""
    try:
        client = get_sheets_client()
        task_types = client.read_sheet(SPREADSHEET_ID, "Task Types!A:A")
        return jsonify({
            'success': True,
            'task_types': [t[0] for t in task_types[1:] if t]  # Skip header, flatten
        })
    except Exception as e:
        logger.error(f"Error getting task types: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/invoices', methods=['POST'])
def create_new_invoice():
    """Create a new invoice."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Validate required fields
        if 'customer_id' not in data:
            return jsonify({'success': False, 'error': 'Missing customer_id'}), 400
        
        if 'task_ids' not in data or not data['task_ids']:
            return jsonify({'success': False, 'error': 'No tasks selected'}), 400
        
        # This would integrate with CreateInvoice.py
       