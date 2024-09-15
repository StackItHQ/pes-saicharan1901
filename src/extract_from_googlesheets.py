import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import pickle
import time  

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

token_pickle = 'token.pickle'
credentials_file = '/Users/cherry/pes-saicharan1901/credentials.json'  

def get_google_sheets_client():
    creds = None


    if os.path.exists(token_pickle):
        with open(token_pickle, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_pickle, 'wb') as token:
            pickle.dump(creds, token)

    client = gspread.authorize(creds)
    return client

def monitor_sheet_for_changes(sheet, polling_interval=5):
    previous_data = None  
    
    while True:
        current_data = sheet.get_all_values()  

        if current_data != previous_data:
            print("Changes detected in Google Sheet:")
            for row in current_data:
                print(row)
            
            previous_data = current_data
        
        time.sleep(polling_interval)

def main():
    client = get_google_sheets_client()

    spreadsheet = client.open("superjoin")  

    sheet = spreadsheet.sheet1

    print("Monitoring changes in the Google Sheet...")
    monitor_sheet_for_changes(sheet, polling_interval=5)

if __name__ == "__main__":
    main()

