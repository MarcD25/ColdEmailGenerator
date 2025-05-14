# Cold Email Internship Generator

This Python script automates the process of generating cold emails for hiring opportunities using Ollama (model: llama3:8b).

## How it works
- Reads `input.txt` with alternating lines of website links and emails.
- Scrapes each website for company/about info.
- Calls the local Ollama API to generate a cold email.
- Outputs each email as a separate `.txt` file in the `output_emails` folder, named after the website.

## Requirements
- Python 3.8+
- `requests`, `beautifulsoup4`, `pyPDF2`, and some `google` libraries
- Ollama running locally with the `llama3:8b` model installed

## Setup Instructions

### Prerequisites
1. **Python Environment**:
   - Install Python 3.8 or higher.
   - Install required libraries using:
     ```bash
     pip install -r requirements.txt
     ```

2. **Google API Setup**:
   - Enable the Gmail API in your Google Cloud Console.
   - Download the `credentials.json` file and place it in the project root directory.
   - Run the script once to authenticate and generate the `token.pickle` file.

3. **Ollama API**:
   - Install and run Ollama locally.
   - Ensure the `llama3:8b` model is installed.

### Input File Structure
- The `input.txt` file should have alternating lines of website URLs and email addresses:
  ```plaintext
  https://example.com
  contact@example.com
  ```

### Running the Script
1. Place your resume in the project root and update the `RESUME_PATH` in `main.py`.
2. Run the script:
   ```bash
   python main.py
   ```
3. Follow the prompts to select the mode (Actual or Test).

### Output
- A log of sent emails is appended to `sent.txt`.

## Usage
1. Place your resume as a `resume.pdf` and place it in the directory of `main.py`.
2. Create an `input.txt` file with alternating lines of website links and emails.
3. Run the script:
   ```bash
   python main.py
   ```
4. Check the `output_emails` folder for results.

## Note
- Make sure Ollama is running and the model is available.

## License

- © 2025 Marc Jacob Guerzon Doria. All rights reserved.
- This repository and its contents are proprietary and confidential.  
- Unauthorized copying, distribution, modification, or derivative works of any part of this code is strictly prohibited without express written permission from the author.
