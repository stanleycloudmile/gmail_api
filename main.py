import os
import datetime
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

def create_service(client_secret_file, api_name, api_version, *scopes, prefix=''):
    CLIENT_SECRET_FILE = client_secret_file
    API_SERVICE_NAME = api_name
    API_VERSION = api_version
    SCOPES = [scope for scope in scopes[0]]
    
    creds = None
    working_dir = os.getcwd()
    token_dir = 'token files'
    token_file = f'token_{API_SERVICE_NAME}_{API_VERSION}{prefix}.json'

    if not os.path.exists(os.path.join(working_dir, token_dir)):
        os.mkdir(os.path.join(working_dir, token_dir))

    if os.path.exists(os.path.join(working_dir, token_dir, token_file)):
        creds = Credentials.from_authorized_user_file(os.path.join(working_dir, token_dir, token_file), SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(os.path.join(working_dir, token_dir, token_file), 'w') as token:
            token.write(creds.to_json())

    try:
        service = build(API_SERVICE_NAME, API_VERSION, credentials=creds, static_discovery=False)
        print(API_SERVICE_NAME, API_VERSION, 'service created successfully')
        return service
    except Exception as e:
        print(e)
        print(f'Failed to create service instance for {API_SERVICE_NAME}')
        os.remove(os.path.join(working_dir, token_dir, token_file))
        return None

def convert_to_RFC_datetime(year=1900, month=1, day=1, hour=0, minute=0):
    dt = datetime.datetime(year, month, day, hour, minute, 0).isoformat() + 'Z'
    return dt

def get_email_messages(service, user_id='me', label_ids=None, folder_name='INBOX', max_results=5, q=None):
    messages = []
    next_page_token = None

    if folder_name:
        label_results = service.users().labels().list(userId = user_id).execute()
        labels = label_results.get('labels',[])
        folder_label_id = next((label['id'] for label in labels if label['name'].lower() == folder_name.lower()))
        if folder_label_id:
            if label_ids:
                label_ids.append(folder_label_id)
            else:
                label_ids = [folder_label_id]
        else:
            raise ValueError(f"Folder '{folder_name}' not found.")
        
    while True:
        result = service.users().messages().list(
            userId=user_id,
            labelIds=label_ids,
            maxResults=min(500, max_results-len(messages) if max_results else 500),
            pageToken=next_page_token,
            q=q
        ).execute()

        messages.extend(result.get('messages', []))

        next_page_token = result.get('nextPageToken')

        if not next_page_token or (max_results and len(messages) >= max_results):
            break

    return messages[:max_results] if max_results else messages

def get_message_details(service, msg_id):
    message = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
    payload = message['payload']
    headers = payload.get('headers',[])

    subject = next(((header['value'] for header in headers if header['name'].lower() == 'subject')))
    if not subject:
        subject = message.get('subject', 'No subject')

    sender = next((header['value'] for header in headers if header['name'] == 'From'), 'No sender')
    recipients = next((header['value'] for header in headers if header['name'] == 'To'), 'No recipients')
    snippet = message.get('snippet', 'No snippet')
    date = next((header['value'] for header in headers if header['name'] == 'Date'), 'No Date')

    return {
        'subject': subject,
        'sender': sender,
        'recipients': recipients,
        'snippet': snippet,
        'date': date,
    }


if __name__ == '__main__':
    client_secret_file = 'token.json'
    API_SERVICE_NAME = 'gmail'
    API_VERSION = 'v1'
    SCOPES = ['https://mail.google.com/']
    max_result = 500

    start_date = '2024-11-25'
    end_date = '2024-12-05'
    sender = "milelync.com"
    query = f"from:{sender} after:{start_date} before:{end_date}"

    service = create_service(client_secret_file, API_SERVICE_NAME, API_VERSION, SCOPES)
    messages = get_email_messages(service, max_results=max_result, q=query)

    for msg in messages:
        details = get_message_details(service, msg['id'])
        print(details)
        print('-'*10)