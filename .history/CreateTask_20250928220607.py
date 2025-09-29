"""
ST_Faktura Task Management Script

This script allows users to create new tasks by selecting customers and task types,
then storing them in the Google spreadsheet.

Customer data from: https://docs.google.com/spreadsheets/d/170onDFFCveCzV6Q9F1_IhsG2LBRcw5MYxJbyocVJmq0/edit?gid=0#gid=0
Task types from: https://docs.google.com/spreadsheets/d/170onDFFCveCzV6Q9F1_IhsG2LBRcw5MYxJbyocVJmq0/edit?gid=288943747#gid=288943747
Tasks stored in: https://docs.google.com/spreadsheets/d/170onDFFCveCzV6Q9F1_IhsG2LBRcw5MYxJbyocVJmq0/edit?gid=1276274497#gid=1276274497

Following copilot instructions for cross-platform compatibility, proper logging, and clean architecture.
"""

import os
import logging
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

from google_sheets_client import GoogleSheetsClient, SheetsConfig, extract_spreadsheet_id

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('st_faktura_tasks.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Spreadsheet configuration
SPREADSHEET_ID = "170onDFFCveCzV6Q9F1_IhsG2LBRcw5MYxJbyocVJmq0"

# Customer sheet (gid=0)
CUSTOMER_SHEET_URL = "https://docs.google.com/spreadsheets/d/170onDFFCveCzV6Q9F1_IhsG2LBRcw5MYxJbyocVJmq0/edit?gid=0#gid=0"
CUSTOMER_SHEET_RANGE = "A:H"

# Task types sheet (gid=288943747)
TASKTYPE_SHEET_URL = "https://docs.google.com/spreadsheets/d/170onDFFCveCzV6Q9F1_IhsG2LBRcw5MYxJbyocVJmq0/edit?gid=288943747#gid=288943747"
TASKTYPE_SHEET_RANGE = "A:A"

# Tasks sheet (gid=1276274497) 
TASKS_SHEET_URL = "https://docs.google.com/spreadsheets/d/170onDFFCveCzV6Q9F1_IhsG2LBRcw5MYxJbyocVJmq0/edit?gid=1276274497#gid=1276274497"
TASKS_SHEET_RANGE = "A:E"


class TaskManager:
    """
    Manages task operations following clean architecture principles
    """
    
    def __init__(self, sheets_client: GoogleSheetsClient):
        """
        Initialize task manager
        
        Args:
            sheets_client: Configured Google Sheets client
        """
        self.sheets_client = sheets_client
        self.customer_spreadsheet_id = extract_spreadsheet_id(CUSTOMER_SHEET_URL)
        self.tasktype_spreadsheet_id = extract_spreadsheet_id(TASKTYPE_SHEET_URL)
        self.tasks_spreadsheet_id = extract_spreadsheet_id(TASKS_SHEET_URL)
        
    def get_customers(self) -> List[Dict[str, str]]:
        """
        Retrieve all customers from the customer spreadsheet
        
        Returns:
            List of customer dictionaries
        """
        try:
            logger.info("Retrieving customers from spreadsheet")
            customers_data = self.sheets_client.read_sheet(self.customer_spreadsheet_id, CUSTOMER_SHEET_RANGE)
            
            customers = []
            
            # Skip header row and process customer data
            if customers_data and len(customers_data) > 1:
                for row in customers_data[1:]:
                    if row and len(row) >= 2:  # At least ID and name
                        customer = {
                            'id': row[0] if len(row) > 0 else '',
                            'name': row[1] if len(row) > 1 else '',
                            'address': row[2] if len(row) > 2 else '',
                            'cvr': row[3] if len(row) > 3 else '',
                            'zip': row[4] if len(row) > 4 else '',
                            'town': row[5] if len(row) > 5 else '',
                            'phone': row[6] if len(row) > 6 else '',
                            'email': row[7] if len(row) > 7 else ''
                        }
                        customers.append(customer)
            
            logger.info(f"Found {len(customers)} customers")
            return customers
            
        except Exception as e:
            logger.error(f"Failed to retrieve customers: {e}")
            return []
    
    def get_task_types(self) -> List[str]:
        """
        Retrieve task types from the task types spreadsheet
        
        Returns:
            List of task type strings
        """
        try:
            logger.info("Retrieving task types from spreadsheet")
            tasktype_data = self.sheets_client.read_sheet(self.tasktype_spreadsheet_id, TASKTYPE_SHEET_RANGE)
            
            task_types = []
            
            # Look for the "Tasktype" column and extract values
            if tasktype_data:
                # Find the column index for "Tasktype"
                header_row = tasktype_data[0] if tasktype_data else []
                tasktype_col_index = None
                
                for i, header in enumerate(header_row):
                    if header and 'tasktype' in header.lower():
                        tasktype_col_index = i
                        break
                
                if tasktype_col_index is not None:
                    # Extract task types from the found column
                    for row in tasktype_data[1:]:  # Skip header
                        if len(row) > tasktype_col_index and row[tasktype_col_index].strip():
                            task_types.append(row[tasktype_col_index].strip())
                else:
                    # Fallback: assume first column contains task types
                    for row in tasktype_data[1:]:
                        if row and row[0].strip():
                            task_types.append(row[0].strip())
            
            logger.info(f"Found {len(task_types)} task types")
            return task_types
            
        except Exception as e:
            logger.error(f"Failed to retrieve task types: {e}")
            return []
    
    def add_task(self, task_data: Dict[str, str]) -> bool:
        """
        Add a new task to the tasks spreadsheet
        
        Args:
            task_data: Dictionary containing task information
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Prepare task row with current date
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            task_row = [
                current_date,  # Date for creation of task
                task_data['customer_name'],  # Customer name
                task_data['tasktype'],  # Tasktype
                task_data['description'],  # Task description
                task_data['time_minutes']  # Task time in minutes
            ]
            
            logger.info(f"Adding new task for customer: {task_data['customer_name']}")
            self.sheets_client.append_to_sheet(
                self.tasks_spreadsheet_id,
                TASKS_SHEET_RANGE,
                [task_row]
            )
            logger.info(f"Successfully added task: {task_data['description'][:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add task: {e}")
            return False
    
    def setup_tasks_spreadsheet_headers(self) -> None:
        """
        Set up the tasks spreadsheet headers if they don't exist
        """
        try:
            logger.info("Checking tasks spreadsheet headers")
            tasks_data = self.sheets_client.read_sheet(self.tasks_spreadsheet_id, TASKS_SHEET_RANGE)
            
            headers = [
                "Date", "Customer Name", "Tasktype", "Task Description", "Task Time (Minutes)"
            ]
            
            # If no data or headers don't match, set them up
            if not tasks_data or len(tasks_data[0]) != len(headers):
                logger.info("Setting up tasks spreadsheet headers")
                self.sheets_client.write_sheet(
                    self.tasks_spreadsheet_id,
                    "A1:E1",
                    [headers]
                )
                logger.info("Tasks headers added successfully")
                
        except Exception as e:
            logger.error(f"Failed to setup tasks headers: {e}")


def display_customers(customers: List[Dict[str, str]]) -> None:
    """
    Display available customers for selection
    
    Args:
        customers: List of customer dictionaries
    """
    print("\n" + "="*60)
    print("AVAILABLE CUSTOMERS")
    print("="*60)
    
    for i, customer in enumerate(customers, 1):
        print(f"{i:2d}. {customer['name']} (ID: {customer['id']})")
        if customer['town']:
            print(f"     {customer['town']}")
    
    print("="*60)


def select_customer(customers: List[Dict[str, str]]) -> Optional[Dict[str, str]]:
    """
    Allow user to select a customer
    
    Args:
        customers: List of available customers
        
    Returns:
        Selected customer dictionary or None if cancelled
    """
    if not customers:
        print("❌ No customers available. Please add customers first using CreateCustomer.py")
        return None
    
    display_customers(customers)
    
    while True:
        try:
            selection = input(f"\nSelect customer (1-{len(customers)}) or 'q' to quit: ").strip()
            
            if selection.lower() == 'q':
                return None
            
            customer_index = int(selection) - 1
            
            if 0 <= customer_index < len(customers):
                selected_customer = customers[customer_index]
                print(f"\n✅ Selected: {selected_customer['name']}")
                return selected_customer
            else:
                print(f"❌ Invalid selection. Please enter a number between 1 and {len(customers)}")
                
        except ValueError:
            print("❌ Invalid input. Please enter a number or 'q' to quit.")


def display_task_types(task_types: List[str]) -> None:
    """
    Display available task types for selection
    
    Args:
        task_types: List of task type strings
    """
    print("\n" + "="*60)
    print("AVAILABLE TASK TYPES")
    print("="*60)
    
    for i, task_type in enumerate(task_types, 1):
        print(f"{i:2d}. {task_type}")
    
    print("="*60)


def select_task_type(task_types: List[str]) -> Optional[str]:
    """
    Allow user to select a task type
    
    Args:
        task_types: List of available task types
        
    Returns:
        Selected task type string or None if cancelled
    """
    if not task_types:
        print("❌ No task types available. Please check the task types spreadsheet.")
        return None
    
    display_task_types(task_types)
    
    while True:
        try:
            selection = input(f"\nSelect task type (1-{len(task_types)}) or 'q' to quit: ").strip()
            
            if selection.lower() == 'q':
                return None
            
            tasktype_index = int(selection) - 1
            
            if 0 <= tasktype_index < len(task_types):
                selected_tasktype = task_types[tasktype_index]
                print(f"\n✅ Selected: {selected_tasktype}")
                return selected_tasktype
            else:
                print(f"❌ Invalid selection. Please enter a number between 1 and {len(task_types)}")
                
        except ValueError:
            print("❌ Invalid input. Please enter a number or 'q' to quit.")


def get_task_description() -> Optional[str]:
    """
    Get task description from user
    
    Returns:
        Task description string or None if cancelled
    """
    print("\n" + "="*60)
    print("TASK DESCRIPTION")
    print("="*60)
    
    while True:
        description = input("Enter task description (or 'q' to quit): ").strip()
        
        if description.lower() == 'q':
            return None
        
        if description:
            return description
        
        print("❌ Task description cannot be empty. Please enter a description.")


def get_task_time() -> Optional[int]:
    """
    Get task time in minutes from user
    
    Returns:
        Task time in minutes or None if cancelled
    """
    print("\n" + "="*60)
    print("TASK TIME")
    print("="*60)
    
    while True:
        try:
            time_input = input("Enter task time in minutes (or 'q' to quit): ").strip()
            
            if time_input.lower() == 'q':
                return None
            
            time_minutes = int(time_input)
            
            if time_minutes > 0:
                return time_minutes
            else:
                print("❌ Task time must be greater than 0 minutes.")
                
        except ValueError:
            print("❌ Invalid input. Please enter a valid number of minutes.")


def display_task_summary(task_data: Dict[str, str]) -> None:
    """
    Display task data summary for confirmation
    
    Args:
        task_data: Dictionary containing task information
    """
    print("\n" + "="*60)
    print("TASK INFORMATION SUMMARY")
    print("="*60)
    
    print(f"Date:             {datetime.now().strftime('%Y-%m-%d')}")
    print(f"Customer:         {task_data['customer_name']}")
    print(f"Task Type:        {task_data['tasktype']}")
    print(f"Description:      {task_data['description']}")
    print(f"Time (Minutes):   {task_data['time_minutes']}")
    print("="*60)


def main() -> None:
    """
    Main function for task creation
    """
    logger.info("Starting ST_Faktura Task Creation")
    
    try:
        # Initialize Google Sheets client
        config = SheetsConfig()
        auth_method = os.getenv('AUTH_METHOD', 'service_account')
        client = GoogleSheetsClient(auth_method=auth_method, config=config)
        
        # Initialize task manager
        task_manager = TaskManager(client)
        
        # Setup tasks spreadsheet headers if needed
        task_manager.setup_tasks_spreadsheet_headers()
        
        print("\n" + "="*60)
        print("ST_FAKTURA - NEW TASK CREATION")
        print("="*60)
        
        # Step 1: Select customer
        print("\nStep 1: Select Customer")
        customers = task_manager.get_customers()
        selected_customer = select_customer(customers)
        
        if not selected_customer:
            print("\n⏭️ Task creation cancelled.")
            return
        
        # Step 2: Select task type
        print("\nStep 2: Select Task Type")
        task_types = task_manager.get_task_types()
        selected_tasktype = select_task_type(task_types)
        
        if not selected_tasktype:
            print("\n⏭️ Task creation cancelled.")
            return
        
        # Step 3: Get task description
        print("\nStep 3: Task Description")
        task_description = get_task_description()
        
        if not task_description:
            print("\n⏭️ Task creation cancelled.")
            return
        
        # Step 4: Get task time
        print("\nStep 4: Task Time")
        task_time = get_task_time()
        
        if not task_time:
            print("\n⏭️ Task creation cancelled.")
            return
        
        # Prepare task data
        task_data = {
            'customer_name': selected_customer['name'],
            'tasktype': selected_tasktype,
            'description': task_description,
            'time_minutes': str(task_time)
        }
        
        # Display summary and confirm
        display_task_summary(task_data)
        
        confirm = input("\nDo you want to save this task? (y/N): ").strip().lower()
        
        if confirm == 'y':
            # Add task to spreadsheet
            if task_manager.add_task(task_data):
                print(f"\n✅ Task added successfully!")
                print(f"Customer: {selected_customer['name']}")
                print(f"Task Type: {selected_tasktype}")
                print(f"Time: {task_time} minutes")
                logger.info(f"Task creation completed for customer: {selected_customer['name']}")
            else:
                print(f"\n❌ Failed to add task. Please check the logs for details.")
                sys.exit(1)
        else:
            print("\n⏭️ Task creation cancelled.")
            logger.info("Task creation cancelled by user")
    
    except KeyboardInterrupt:
        print("\n\n⏭️ Operation cancelled by user.")
        logger.info("Task creation interrupted by user")
        sys.exit(0)
    
    except Exception as e:
        logger.error(f"Unexpected error in task creation: {e}")
        print(f"\n❌ An unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()