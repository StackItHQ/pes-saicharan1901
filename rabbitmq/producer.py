import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import mysql.connector
import os
import pickle
import time
from dotenv import load_dotenv
import pika  # RabbitMQ library
from dotenv import load_dotenv
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

TOKEN_PICKLE = 'token.pickle'
CREDENTIALS_FILE = '/Users/cherry/pes-saicharan1901/credentials.json'  # Your OAuth2 credentials file

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

def get_google_sheets_client():
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
    return client

def get_mysql_connection():
    return mysql.connector.connect(**mysql_config)

def clear_cursor_results(cursor):
    while cursor.nextset():
        pass

def get_table_columns(cursor, table_name):
    cursor.execute(f"DESCRIBE {table_name}")
    columns = cursor.fetchall()
    return [column[0] for column in columns]

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

def sync_sheet_to_db(sheet, cursor):
    data = sheet.get_all_values()
    headers = data[0]
    
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
    print(f"Changes detected in Google Sheet '{sheet.title}'. Updated MySQL database.")

def sync_db_to_sheet(cursor, sheet):
    cursor.execute(f"SELECT * FROM {sheet.title}")
    rows = cursor.fetchall()
    headers = [desc[0] for desc in cursor.description]

    sheet.update([headers] + [list(row) for row in rows])
    clear_cursor_results(cursor)
    print(f"Changes detected in MySQL database. Updated Google Sheet '{sheet.title}'.")

def send_message(message):
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_host))
    channel = connection.channel()
    channel.queue_declare(queue=rabbitmq_queue, durable=True)
    channel.basic_publish(
        exchange='',
        routing_key=rabbitmq_queue,
        body=message,
        properties=pika.BasicProperties(
            delivery_mode=2  # Make message persistent
        )
    )
    connection.close()

def monitor_and_sync():
    client = get_google_sheets_client()
    connection = get_mysql_connection()
    cursor = connection.cursor()

    spreadsheet = client.open("superjoin")
    last_sheet_data = {}
    last_db_data = {}

    while True:
        # Track changes for each sheet
        changes_detected = {}

        # Check Google Sheets for changes
        for sheet in spreadsheet.worksheets():
            current_data = sheet.get_all_values()
            current_data_str = str(current_data)
            last_data_str = last_sheet_data.get(sheet.title)

            if last_data_str is None:
                last_data_str = ''

            if last_data_str != current_data_str:
                changes_detected[sheet.title] = 'sheet'
                last_sheet_data[sheet.title] = current_data_str

        # Check MySQL for changes
        for sheet in spreadsheet.worksheets():
            table_name = sheet.title

            # Check if the table exists in MySQL
            cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
            table_exists = cursor.fetchone()

            if not table_exists:
                # Create the table if it doesn't exist
                headers = sheet.row_values(1)
                create_or_update_table(cursor, table_name, headers)
                connection.commit()  # Commit the table creation

            # Now fetch the data from the newly created or existing table
            try:
                cursor.execute(f"SELECT * FROM {table_name}")
                rows = cursor.fetchall()
                headers = [desc[0] for desc in cursor.description]
                current_db_data = [list(row) for row in rows]
                current_db_data_str = str(current_db_data)
                last_data_str = last_db_data.get(table_name)

                if last_data_str is None:
                    last_data_str = ''

                if last_data_str != current_db_data_str:
                    changes_detected[table_name] = 'db'
                    last_db_data[table_name] = current_db_data_str
            except mysql.connector.errors.ProgrammingError as e:
                print(f"Error fetching data from table '{table_name}': {e}")
                # Skip further processing for this sheet

        # Enqueue detected changes
        for sheet_title, change_type in changes_detected.items():
            message = f"{sheet_title}:{change_type}"
            send_message(message)

        connection.commit()
        time.sleep(20)


if __name__ == "__main__":
    monitor_and_sync()
