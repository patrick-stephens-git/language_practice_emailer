# Language Practice Emailer

## Overview
Language Practice Emailer is a Python project designed to help users practice a new language by sending them emails with words the user struggles with. The project fetches language content from a Google Sheet file (e.g: https://docs.google.com/spreadsheets/d/1e4xSr0ZxLaeDICGxBgR4zbNmDhrN-Yl7Cy7b5e4lT0w/edit?usp=sharing) and compiles it into a structured email format.

## Installation
1. Clone the repository:
    ```
    git clone https://github.com/patrick-stephens-git/language_practice_emailer_llm.git
    ```
2. Navigate to the project directory:
    ```
    cd language_practice_emailer_llm
    ```
3. Install the required dependencies:
    ```
    pip install -r requirements.txt
    ```

## Configuration
1. Create an environment file `.env` in the project root directory with the following structure:
    ```
    SHEET_ID={google_sheet_id}
    SHEET_GID={worksheet_tab_id}
    EMAIL_ACCOUNT={sending_email_address}
    EMAIL_PASSWORD={sending_email_password}
    EMAIL_RECIPIENTS={email_recipients}
    OPENAI_API_KEY={api_key}
    WEB_APP_URL={apps_script_web_app_exec_url}
    LINK_SECRET={any_random_string}
    ```
2. Create a Google service account, download its JSON key as `service_account.json` in the project root, and share the sheet with the account's `client_email` as Editor. The sheet can stay private.
3. Customize the configuration file with your target country, target language, and focus variables
4. (Optional) Enable the "I did not know this word" link at the end of each email. Tapping it adds +1 to that word's `Lookup Count`:
    1. In the sheet, open Extensions > Apps Script and paste in `apps_script/Code.gs`.
    2. Under Project Settings > Script Properties, add `LINK_SECRET` with the same value as in `.env`.
    3. Set `SHEET_GID` at the top of `Code.gs` to your tab id (the number after `gid=` in the sheet URL).
    4. Deploy > New deployment > Web app (Execute as: Me, Who has access: Anyone), then put the `/exec` URL in `.env` as `WEB_APP_URL`. After editing `Code.gs` later, redeploy with Manage deployments > New version.

    Every tap adds +1. Without `WEB_APP_URL` the link is left out.

## Usage
Run the main script to start sending language practice emails.

## Logs
Each run prints its progress to the terminal and writes it to `logs/app.log`: the picked word, the prompts, the AI responses, the check verdicts, the email send and the sheet update. Each trigger overwrites the file, so it holds the latest trigger only. Triggers outside the active window leave it untouched.

To follow a run as it happens:
```
tail -f logs/app.log
```

When running from cron, also save the terminal output to a separate file. This catches errors that happen before logging starts, such as a failed import or a bad config value. The `logs` directory must already exist.
```
cd /path/to/language_practice_emailer && .venv/bin/python main.py > logs/cron.log 2>&1
```
`cron.log` is also overwritten on each trigger, including one skipped for being outside the active window.
