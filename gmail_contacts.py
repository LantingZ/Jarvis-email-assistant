import os
import json
import pickle
import base64
from email.utils import parseaddr
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
SEEN_EMAILS_FILE = 'seen_emails.json'

def authenticate_gmail():
    creds = None
    if os.path.exists('token.pkl'):
        with open('token.pkl', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        with open('token.pkl', 'wb') as token:
            pickle.dump(creds, token)

    return build('gmail', 'v1', credentials=creds)

def load_seen_ids():
    if os.path.exists(SEEN_EMAILS_FILE):
        with open(SEEN_EMAILS_FILE, 'r') as f:
            return set(json.load(f))
    return set()

def save_seen_ids(seen_ids):
    with open(SEEN_EMAILS_FILE, 'w') as f:
        json.dump(list(seen_ids), f, indent=2)

def extract_contacts_from_sent_and_inbox(max_emails=50):
    service = authenticate_gmail()
    seen_ids = load_seen_ids()
    contact_dict = {}
    new_seen_ids = set()

    for label in ['SENT', 'INBOX']:
        results = service.users().messages().list(userId='me', labelIds=[label], maxResults=max_emails).execute()
        messages = results.get('messages', [])

        for msg in messages:
            msg_id = msg['id']
            if msg_id in seen_ids:
                continue

            msg_data = service.users().messages().get(
                userId='me',
                id=msg_id,
                format='full',
            ).execute()

            headers = msg_data['payload']['headers']
            name = None
            email = None

            for header in headers:
                if header['name'] in ['To', 'From']:
                    name, email = parseaddr(header['value'])

            if not email:
                continue

            if not name:
                name = extract_name_from_email(msg_data)

            key = name.lower() if name else email.split('@')[0]
            contact_dict[key] = email
            new_seen_ids.add(msg_id)

    seen_ids.update(new_seen_ids)
    save_seen_ids(seen_ids)

    return contact_dict

def extract_name_from_email(msg_data):
    try:
        parts = msg_data['payload'].get('parts', [])
        for part in parts:
            if part['mimeType'] == 'text/plain':
                data = part['body'].get('data')
                if data:
                    decoded = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    return gpt_extract_name(decoded)
    except Exception:
        pass

    snippet = msg_data.get("snippet", "")
    return gpt_extract_name(snippet)

def gpt_extract_name(email_text):
    try:
        system_msg = (
            "You're a smart assistant. Given the body of an email, extract the name of the person writing the email "
            "or the name they are addressing. Do NOT guess full names — return only what is clearly stated. "
            "If the signature is just 'J', return 'J'. If it's 'James' or 'Janice', return that. "
            "Respond with JSON: {\"name\": \"<name>\"}"
        )

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": email_text[:2000]}
            ],
            temperature=0.0
        )

        content = response.choices[0].message.content.strip()

        json_start = content.find('{')
        if json_start != -1:
            json_str = content[json_start:]
            name_data = json.loads(json_str)
            return name_data.get("name")
        else:
            print("⚠️ GPT response missing JSON structure")
            return None
    except Exception as e:
        print("GPT name extraction failed:", e)
        return None

def merge_with_existing_contacts(new_contacts):
    path = 'contacts.json'
    if os.path.exists(path):
        with open(path, 'r') as f:
            contacts = json.load(f)
    else:
        contacts = {}

    contacts.update(new_contacts)

    with open(path, 'w') as f:
        json.dump(contacts, f, indent=2)

    print(f"✅ Synced {len(new_contacts)} new contacts to contacts.json")

if __name__ == "__main__":
    new_contacts = extract_contacts_from_sent_and_inbox()
    merge_with_existing_contacts(new_contacts)
