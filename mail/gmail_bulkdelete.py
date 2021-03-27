#
# 1. Go to https://console.cloud.google.com/, API and Service, Credentials.
# 2. Download OAuth 2.0 Creds file.
# 3. Run this script. First parameter is the creds, second parameter is the gmail filter.
#
# WARNING: Use with care, there is no way to recover deleted emails I think.
#

from __future__ import print_function
import pickle
import os.path
import sys
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://mail.google.com/',
        'https://www.googleapis.com/auth/gmail.modify']

def main(creds_path, qfilter, confirm):
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('/tmp/token.pickle'):
        with open('/tmp/token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('/tmp/token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('gmail', 'v1', credentials=creds)

    ptoken = None
    print("Deleting msgs matching with: ", qfilter)
    while True:
        results = service.users().messages().\
                list(userId='me', q=qfilter, pageToken=ptoken).execute()

        msgs = results.get('messages', [])
        if len(msgs) == 0:
            break

        ptoken = results.get('nextPageToken', None)
        if not ptoken:
            break

        if confirm == "YES":
            msg_ids = []
            for msg in msgs:
                msg_ids.append(msg['id'])

            service.users().messages().\
                    batchDelete(userId='me', body=dict({"ids":msg_ids})).execute()

        else:
            for msg in msgs:
                fullmsg = service.users().messages().\
                    get(userId='me', id=msg["id"]).execute()
                subject = ""
                msgfrom = ""
                for header in fullmsg["payload"]["headers"]:
                    if header["name"] == "Subject":
                        subject = header["value"]
                    if header["name"] == "From":
                        msgfrom = header["value"]
                print(msgfrom, subject)

    profile = service.users().getProfile(userId='me').execute()
    print(profile)

if __name__ == '__main__':
    try:
        confirm = sys.argv[3]
    except:
        confirm = "NO"
    main(sys.argv[1], sys.argv[2], confirm)

