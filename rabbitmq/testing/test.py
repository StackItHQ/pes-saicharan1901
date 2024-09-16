import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import mysql.connector
import os
import pickle
import time
from dotenv import load_dotenv

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

TOKEN_PICKLE = 'token.pickle'
CREDENTIALS_FILE = '/Users/cherry/pes-saicharan1901/credentials.json'  # Your OAuth2 credentials file

load_dotenv()

mysql_config = {
    'host': os.getenv('MYSQL_HOST'),
    'user': os.getenv('MYSQL_USER'),
    'password': os.getenv('MYSQL_PASSWORD'),
    'database': os.getenv('MYSQL_DATABASE')
}

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

def monitor_and_sync():
    client = get_google_sheets_client()
    connection = get_mysql_connection()
    cursor = connection.cursor()

    spreadsheet = client.open("superjoin")  
    last_sheet_data = {}
    last_db_data = {}

    while True:
        for sheet in spreadsheet.worksheets():
            current_data = sheet.get_all_values()
            current_data_str = str(current_data)
            last_data_str = last_sheet_data.get(sheet.title)

            if last_data_str != current_data_str:
                sync_sheet_to_db(sheet, cursor)
                last_sheet_data[sheet.title] = current_data_str

        for sheet in spreadsheet.worksheets():
            cursor.execute(f"SELECT * FROM {sheet.title}")
            rows = cursor.fetchall()
            headers = [desc[0] for desc in cursor.description]
            current_db_data = [list(row) for row in rows]
            current_db_data_str = str(current_db_data)
            last_data_str = last_db_data.get(sheet.title)

            if last_data_str != current_db_data_str:
                sync_db_to_sheet(cursor, sheet)
                last_db_data[sheet.title] = current_db_data_str

        connection.commit() 
        time.sleep(20)

if __name__ == "__main__":
    monitor_and_sync()


