import os
# from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import requests
import base64



# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def get_credential():

  creds = None
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists("token.json"):
      creds = Credentials.from_authorized_user_file("token.json", SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
      if creds and creds.expired and creds.refresh_token:
          creds.refresh(Request())
      else:
          flow = InstalledAppFlow.from_client_secrets_file(
              "credentials.json", SCOPES
          )
          creds = flow.run_local_server(port=0)
      # Save the credentials for the next run
      with open("token.json", "w") as token:
          token.write(creds.to_json())

  # Call the Gmail API
  # service = build("gmail", "v1", credentials=creds)
  
  return creds

def fetch_server(url):
      
    token = get_credential().token
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    response= requests.get(url, headers=headers)
    return response

# Get unread messages and extract IDs
def get_unread_message_ids(max_results=10):
    
    # Make the request to get unread messages
    url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages?q=is:unread&maxResults={max_results}"
    response = fetch_server(url)
    
    # Check if the request was successful
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.text)
        return []
    
    # Parse the response
    data = response.json()
    
    # The response structure has a 'messages' key that contains a list of message objects
    # Each message object has an 'id' and 'threadId'
    messages = data.get('messages', [])
    
    # Extract just the IDs
    message_ids = [msg['id'] for msg in messages]
    
    return message_ids

# Function to decode a base64url encoded email message
def decode_raw_message(raw_data):
    # Gmail's raw format is base64url encoded
    # Add padding if needed
    if not raw_data:
        return ""
    padded_data = raw_data + '=' * (4 - len(raw_data) % 4) if len(raw_data) % 4 else raw_data
    
    # Use base64.urlsafe_b64decode for proper decoding
    message_bytes = base64.urlsafe_b64decode(padded_data)
    
    # Convert to string
    msg = message_bytes.decode('utf-8', errors='replace')
  
    return msg

def find_parts(parts):
    body = ""
    if parts:
        for part in parts:
            if part.get("mimeType") == "text/plain":
                body += decode_raw_message(part.get("body", {}).get("data"))
            elif part.get("mimeType") == "text/html":
                # Fallback to HTML if plain text is not available
                if not body:
                    body += decode_raw_message(part.get("body", {}).get("data"))
            elif "parts" in part:
                body += find_parts(part["parts"])
    return body
  
def get_email_details(message_id : str):
    """
    Fetch and parse details for a specific email message.
        
    Returns:
        Dictionary containing email details (subject, sender, recipient, message body)
    """
    # Make the API request
    url = "https://www.googleapis.com/gmail/v1/users/me/messages/" + message_id
    response = fetch_server(url)
    
    # Parse the response
    try:
        message_data = response.json()
        
        # Extract headers
        mail_headers = message_data['payload']['headers']
        header_dict = {header['name']: header['value'] for header in mail_headers}
        
        subject = header_dict.get('Subject', 'No Subject')
        sender = header_dict.get('From', 'Unknown Sender')
        recipient = header_dict.get('To', 'Unknown Recipient')
        
        # Extract message body 
        body = ""
        if "parts" in message_data["payload"]:
            body = find_parts(message_data["payload"]["parts"])
        else:
            body = decode_raw_message(message_data["payload"].get("body", {}).get("data"))

        
        return {
            "subject": subject,
            "sender": sender,
            "recipient": recipient,
            "body": body,
            "success": True
        }
        
    except (KeyError, ValueError, IndexError) as e:
        return {
            "error": f"Error parsing message data: {str(e)}",
            "raw_data": response.json() if response.status_code == 200 else {},
            "success": False
        }



def get_unread_emails(max_results=10):
    """
    Firstly, fetch unread message IDs, 
    Then, get the details of each message through those IDs.
    
    Args:
        max_results: Maximum number of unread emails to fetch (default 10)
        
    Returns:
        List of dictionaries containing email details for all unread messages
    """
    # First, get the IDs of all unread messages
    unread_ids = get_unread_message_ids(max_results)
    
    if not unread_ids:
        print("No unread messages found.")
        return []
    
    # Now fetch details for each unread message
    unread_emails = []
    for msg_id in unread_ids:
        # Get email details for this message ID
        email_details = get_email_details(msg_id)
        
        # Add message ID to the details dictionary
        email_details['id'] = msg_id
        
        # Add to our list of unread emails
        if email_details["success"]:
            unread_emails.append(email_details)
        else:
            print(f"Failed to process email with ID: {msg_id}")
            print(f"Error: {email_details.get('error')}")

        
    print(f"Fetched details for {len(unread_emails)} unread emails.")
    return unread_emails

# TODO: make unread messages read when fetching them

if __name__ == "__main__":

  unread_emails = get_unread_emails()
  if len(unread_emails)>0:
    for key, value in unread_emails[0].items():
        print(f'{key}:{value}')
