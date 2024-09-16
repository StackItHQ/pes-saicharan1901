import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import mysql.connector
import os
import pickle
import pika  # RabbitMQ library
import threading  # To handle concurrency
import logging  # For enhanced logging
from dotenv import load_dotenv

# Setup logging for better tracking
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Google Sheets and MySQL Scopes/Configs
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
TOKEN_PICKLE = 'token.pickle'
CREDENTIALS_FILE = '/Users/cherry/pes-saicharan1901/credentials.json'

# Load environment variables
load_dotenv()

# MySQL configuration
mysql_config = {
    'host': os.getenv('MYSQL_HOST'),
    'user': os.getenv('MYSQL_USER'),
    'password': os.getenv('MYSQL_PASSWORD'),
    'database': 'superjoin'
}

# RabbitMQ configuration
rabbitmq_host = os.getenv('RABBITMQ_HOST', 'localhost')
rabbitmq_queue = 'conflict_queue'

# Get Google Sheets Client with Authentication
def get_google_sheets_client():
    try:
        creds = None
        if os.path.exists(TOKEN_PICKLE):
            with open(TOKEN_PICKLE, 'rb') as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(TOKEN_PICKLE, 'wb') as token:
                pickle.dump(creds, token)

        client = gspread.authorize(creds)
        logging.info("Successfully connected to Google Sheets")
        return client
    except Exception as e:
        logging.error(f"Failed to connect to Google Sheets: {e}")
        raise

# Establish connection to MySQL
def get_mysql_connection():
    try:
        connection = mysql.connector.connect(**mysql_config)
        logging.info("Successfully connected to MySQL")
        return connection
    except mysql.connector.Error as e:
        logging.error(f"Error connecting to MySQL: {e}")
        raise

# Function to handle synchronization from Google Sheets to MySQL for all sheets
def sync_all_sheets_to_db(spreadsheet, cursor):
    # Get all worksheets in the Google Spreadsheet
    sheets = spreadsheet.worksheets()

    # Get existing MySQL tables
    cursor.execute("SHOW TABLES")
    existing_tables = [table[0] for table in cursor.fetchall()]

    # Loop through each sheet in the spreadsheet
    for sheet in sheets:
        sheet_title = sheet.title

        # Check if the MySQL table exists, if not, create it
        if sheet_title not in existing_tables:
            logging.info(f"New sheet detected: {sheet_title}. Creating corresponding MySQL table.")
            headers = sheet.row_values(1)  # Assume first row has headers
            create_new_table_for_sheet(cursor, sheet_title, headers)
            connection.commit()

        # Sync the sheet data to MySQL
        sync_sheet_to_db(sheet, cursor)

# Create a new MySQL table based on the Google Sheet headers
def create_new_table_for_sheet(cursor, sheet_title, headers):
    clear_cursor_results(cursor)

    create_sql = f"""
    CREATE TABLE {sheet_title} (
        id INT AUTO_INCREMENT PRIMARY KEY,
        {', '.join(f'{header} VARCHAR(255)' for header in headers)}
    )
    """
    cursor.execute(create_sql)
    clear_cursor_results(cursor)
    logging.info(f"Created new MySQL table for sheet: {sheet_title}")

# Function to handle synchronization from Google Sheets to MySQL for a specific sheet
def sync_sheet_to_db(sheet, cursor):
    data = sheet.get_all_values()
    headers = data[0]

    logging.info(f"Syncing Google Sheet '{sheet.title}' to MySQL")

    # Check and create/update the MySQL table based on Google Sheet headers
    create_or_update_table(cursor, sheet.title, headers)

    for row in data[1:]:
        values = [f"'{value}'" for value in row]
        sql = f"""
        INSERT INTO {sheet.title} ({', '.join(headers)})
        VALUES ({', '.join(values)})
        ON DUPLICATE KEY UPDATE {', '.join(f'{header}=VALUES({header})' for header in headers)}
        """
        cursor.execute(sql)
        clear_cursor_results(cursor)

    logging.info(f"Successfully synced Google Sheet '{sheet.title}' to MySQL")

# Function to handle synchronization from MySQL to Google Sheets
def sync_db_to_sheet(cursor, sheet):
    cursor.execute(f"SELECT * FROM {sheet.title}")
    rows = cursor.fetchall()
    headers = [desc[0] for desc in cursor.description]

    logging.info(f"Syncing MySQL '{sheet.title}' table to Google Sheet")

    # Update Google Sheet with MySQL data
    sheet.clear()
    sheet.update([headers] + [list(row) for row in rows])
    clear_cursor_results(cursor)

    logging.info(f"Successfully synced MySQL '{sheet.title}' to Google Sheet")

# Clears pending results from MySQL cursor
def clear_cursor_results(cursor):
    while cursor.nextset():
        pass

# Create or update MySQL table based on Google Sheets headers
def create_or_update_table(cursor, sheet_name, headers):
    clear_cursor_results(cursor)

    cursor.execute(f"SHOW TABLES LIKE '{sheet_name}'")
    if cursor.fetchone():
        existing_columns = get_table_columns(cursor, sheet_name)
        new_columns = [header for header in headers if header not in existing_columns]

        if new_columns:
            alter_sql = f"ALTER TABLE {sheet_name} ADD COLUMN {', ADD COLUMN '.join(f'{col} VARCHAR(255)' for col in new_columns)}"
            cursor.execute(alter_sql)
            clear_cursor_results(cursor)
    else:
        create_sql = f"""
        CREATE TABLE {sheet_name} (
            id INT AUTO_INCREMENT PRIMARY KEY,
            {', '.join(f'{header} VARCHAR(255)' for header in headers)}
        )
        """
        cursor.execute(create_sql)
        clear_cursor_results(cursor)

# Get MySQL table columns
def get_table_columns(cursor, table_name):
    cursor.execute(f"DESCRIBE {table_name}")
    columns = cursor.fetchall()
    return [column[0] for column in columns]

# Function to process incoming messages from RabbitMQ
def process_message(ch, method, properties, body):
    message = body.decode()
    sheet_title, change_type = message.split(':')

    logging.info(f"Processing message: {message}")

    try:
        client = get_google_sheets_client()
        connection = get_mysql_connection()
        cursor = connection.cursor()

        spreadsheet = client.open("superjoin")

        # If a new sheet is created or updated
        if change_type == 'sheet':
            sync_all_sheets_to_db(spreadsheet, cursor)  # Check all sheets for new or updated ones
        elif change_type == 'db':
            # Sync specific sheet to MySQL if DB change
            sheet = spreadsheet.worksheet(sheet_title)
            sync_db_to_sheet(cursor, sheet)

        connection.commit()
        logging.info(f"Finished processing message: {message}")

    except Exception as e:
        logging.error(f"Error processing message '{message}': {e}")

# Function to start consuming messages from RabbitMQ with concurrency
def start_consumer():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_host))
    channel = connection.channel()
    channel.queue_declare(queue=rabbitmq_queue, durable=True)

    def callback(ch, method, properties, body):
        # Use threading to handle multiple messages concurrently
        threading.Thread(target=process_message, args=(ch, method, properties, body)).start()

    channel.basic_consume(queue=rabbitmq_queue, on_message_callback=callback, auto_ack=True)
    logging.info('Waiting for messages. To exit press CTRL+C')
    channel.start_consuming()

if __name__ == "__main__":
    start_consumer()
