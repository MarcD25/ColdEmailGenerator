import os
import re
import requests
import PyPDF2
import logging
import pickle
import base64
import time
import google.auth.exceptions
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from bs4 import BeautifulSoup

OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3:8b"
RESUME_PATH = "resume.pdf"
ACT_INPUT = "input.txt"
TEST_INPUT = "test_input.txt"
INPUT_FILE = None

SCOPES = ['https://www.googleapis.com/auth/gmail.compose']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.pickle'

def read_resume(path, max_chars):
    if path.lower().endswith('.pdf'):
        try:
            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                text = " ".join(page.extract_text() or '' for page in reader.pages)
                text = text.replace("\n", " ").strip()
                return text[:max_chars] + ("..." if len(text) > max_chars else "")
        except Exception as e:
            return "[Resume PDF not found or unreadable]"
    else:
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
                return text[:max_chars] + ("..." if len(text) > max_chars else "")
        except Exception as e:
            return "[Resume not found or unreadable]"

def scrape_website(url, max_chars):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36"
    }
    retries = 3
    delay = 5  
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")

            title = soup.title.string.strip() if soup.title else "[No title found]"
            
            meta_desc = "[No meta description found]"
            desc_tag = soup.find("meta", attrs={"name": "description"})
            if desc_tag and desc_tag.get("content"):
                meta_desc = desc_tag["content"].strip()
            
            about = "[No about section found]"
            for tag in soup.find_all(["section", "div", "p", "span"]):
                if tag.get_text() and re.search(r"about|company", tag.get_text(), re.I):
                    about = tag.get_text().strip()
                    if len(about) > max_chars:
                        about = about[:max_chars] + "..."
                    break

            print(f"Scraped Data for {url}:")
            print(f"- Title: {title}")
            print(f"- Meta Description: {meta_desc}")
            
            info = f"Title: {title}\nMeta: {meta_desc}\nAbout: {about}"
            return info[:max_chars] + ("..." if len(info) > max_chars else "")
        except requests.exceptions.RequestException as e:
            print(f"[Attempt {attempt + 1} failed for {url}: {e}]")
            if attempt < retries - 1:
                time.sleep(delay)  
            else:
                print(f"[All attempts failed for {url}. Generating template for manual editing...]")
                return f"Title: [Manual Entry]\nMeta: [Manual Entry]\nAbout: [Manual Entry]"
        except Exception as e:
            print(f"[Error scraping {url}: {e}]")
            return f"Title: [Manual Entry]\nMeta: [Manual Entry]\nAbout: [Manual Entry]"

def generate_email(website_info, email, resume, system_prompt):
    
    company_name = "[Company]"
    company_mission = "[Company's mission]"
    company_values = "[Company's values]"

    
    if "Title:" in website_info:
        company_name = website_info.split("Title:")[1].split("\n")[0].strip()
    if "Meta:" in website_info:
        company_mission = website_info.split("Meta:")[1].split("\n")[0].strip()
    if "About:" in website_info:
        company_values = website_info.split("About:")[1].split("\n")[0].strip()

    personalized_prompt = system_prompt.replace("[Company]", company_name)
    personalized_prompt = personalized_prompt.replace("[Company's mission]", company_mission)
    personalized_prompt = personalized_prompt.replace("[Company's values]", company_values)    
    personalized_prompt = personalized_prompt.replace("To the Team at ...", f"To the Team at {company_name},")
    personalized_prompt = personalized_prompt.replace("whether ... offers", f"whether {company_name} offers")

    prompt = f"{personalized_prompt}\n\nWebsite Info:\n{website_info.strip()}\n\nContact Email: {email.strip()}\n\nResume (use only the information below, do not invent or use placeholders):\n{resume.strip()}\n\nWrite the email using only the details from the resume above. Do not use any placeholders or generic skills. The email must be fully personalized and ready to send."
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }
    retries = 3
    for attempt in range(retries):
        try:
            resp = requests.post(OLLAMA_API_URL, json=payload, timeout=300)
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "[No response from Ollama]").strip()
        except requests.exceptions.HTTPError as e:
            try:
                err_msg = resp.text
            except Exception:
                err_msg = str(e)
            print(f"[Ollama API error: {e}\nResponse: {err_msg}]")
            exit(1)
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                logging.warning(f"Attempt {attempt + 1} failed. Retrying... Error: {e}")
            else:
                print(f"[Ollama API error after {retries} attempts: {e}]")
                exit(1)
        except Exception as e:
            print(f"[Ollama API error: {e}]")
            exit(1)

def authenticate_gmail():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        try:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                raise google.auth.exceptions.RefreshError("Token expired or invalid")
        except google.auth.exceptions.RefreshError:
            print("Token has expired or been revoked. Reauthenticating...")
            if os.path.exists(TOKEN_FILE):
                os.remove(TOKEN_FILE)
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            with open(TOKEN_FILE, 'wb') as token:
                pickle.dump(creds, token)
    return build('gmail', 'v1', credentials=creds)

import re

def is_valid_email(email):    
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(email_regex, email) is not None

def is_valid_url(url):
    url_regex = r'^(https?://)?[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$'
    return re.match(url_regex, url) is not None

def create_draft(service, user_id, subject, body, recipient):
    if not is_valid_email(recipient):
        print(f"Invalid email address: {recipient}")
        return

    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from email.mime.base import MIMEBase
    from email import encoders
    
    message = MIMEMultipart()
    message['Subject'] = subject
    message['To'] = recipient
    message.attach(MIMEText(body, 'plain', 'utf-8'))
    
    resume_path = RESUME_PATH
    with open(resume_path, 'rb') as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename="{os.path.basename(resume_path)}"',
        )
        message.attach(part)
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    
    try:
        draft = service.users().drafts().create(
            userId=user_id,
            body={'message': {'raw': raw_message}}
        ).execute()
        print(f"Draft created with ID: {draft['id']}")
    except Exception as e:
        print(f"An error occurred: {e}")

def log_sent_email(site, email):
    with open("sent.txt", "a", encoding="utf-8") as sent_file:
        sent_file.write(f"{site} - {email}\n")

def main():    
    try:
        gmail_service = authenticate_gmail()
    except Exception as e:
        print(f"Failed to authenticate Gmail: {e}")
        return

    resume = read_resume(RESUME_PATH, max_chars=3000)

    print("Don't forget to turn on your VPN.\nModes:\n1. Actual\n2. Test")
    choice = input("Enter your choice: ")

    if choice == "1":
        print("You selected option 1: Actual mode.")
        input_file = ACT_INPUT
    elif choice == "2":
        print("You selected option 2: Test mode.")
        input_file = TEST_INPUT
    else:
        print("Invalid choice. Please select 1 or 2.")
        return

    if not os.path.exists(input_file):
        print(f"Input file '{input_file}' not found.")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    i = 0
    while i < len(lines):
        link = lines[i]
        i += 1

        if not is_valid_url(link):
            print(f"Invalid URL: {link}. Skipping...")
            continue

        emails = []
        
        while i < len(lines) and is_valid_email(lines[i]):
            emails.extend([email.strip() for email in lines[i].split(",")])
            i += 1

        if not emails:
            print(f"No valid emails found for {link}. Skipping...")
            continue

        website_info = scrape_website(link, max_chars=3000)        
        with open("prompt.txt", "r", encoding="utf-8") as prompt_file:
            system_prompt = prompt_file.read()

        for email in emails:
            email_text = generate_email(website_info, email, resume, system_prompt)
            company_name = "[Company]"
            if "Title:" in website_info:
                company_name = website_info.split("Title:")[1].split("\n")[0].strip()
            subject = f"INQUIRY: CS/IT Internship Opportunities at {company_name}"

            try:
                create_draft(gmail_service, 'me', subject, email_text, email)
                log_sent_email(link, email)
                print(f"Generated draft for {link} and email {email}")
            except Exception as e:
                print(f"Failed to create draft for {email}: {e}")

if __name__ == "__main__":
    main()