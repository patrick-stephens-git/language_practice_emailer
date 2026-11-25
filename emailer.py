from utils.logging_config import setup_logging
from config import sender_email_account, sender_email_password, email_recipients, target_country, web_app_url, link_secret
import html
import smtplib
from email.mime.text import MIMEText
from urllib.parse import urlencode

def build_lookup_link(word: str) -> str:
    """Return the HTML "I did not know this word" link, or "" when WEB_APP_URL is not configured."""
    if not web_app_url:
        return ""
    query: str = urlencode({"key": link_secret, "word": word}) # urlencode percent-encodes the word (accents, spaces)
    return f'<a href="{html.escape(web_app_url + "?" + query)}">I did not know this word</a>'

def emailer(word: str, translation: str, ai_translation: str, example_sentence: str, example_synonyms: str, is_common: str, is_common_reason: str = "") -> None:
    #####################################
    ## Logging:
    logger = setup_logging()

    #####################################
    ## Setup Recipients:
    recipients: list[str] = email_recipients.split(",") # Convert email_recipients string to a list

    #####################################
    ## Check for empty variables; if empty then fail, else continue:
    try:
        empty_vars = [var_name for var_name, var in [("sender_email_account", sender_email_account), ("sender_email_password", sender_email_password), ("email_recipients", email_recipients)] if not var] # Collect names of any missing auth variables
        if empty_vars:
            raise ValueError(f"Fail: Missing the following email authentication variables: {empty_vars}") # Raise error listing missing variables
        else:
            logger.info("Pass: All email authentication variables exist.")
    except ValueError as e:
        logger.error(e) # Log the error message
        return

    #####################################
    ## Setup Subject Line:
    email_subject_line: str = f"{word}: {example_sentence}" # Prefix the example sentence with the word or phrase being practiced
    logger.info(f"Email subject line: {email_subject_line}")

    #####################################
    ## Show the checks' reason under the Yes/No/Unsure line (omitted when empty):
    reason_line: str = f"Reason: {html.escape(is_common_reason)}<br>" if is_common_reason else ""

    #####################################
    ## Link that adds +1 to this word's Lookup Count when tapped (omitted when WEB_APP_URL is unset):
    lookup_link: str = build_lookup_link(word)
    lookup_line: str = f"<br>{lookup_link}<br>" if lookup_link else "" # blank line before the link

    #####################################
    ## Setup Email Body:
    email_body: str = f"""
    Word or Phrase: {word}<br>
    My Translation: {translation}<br>
    AI Translation: {ai_translation}<br>
    <br>
    Synonyms: {example_synonyms}<br>
    <br>
    Common in {target_country}? {is_common}<br>
    {reason_line}{lookup_line}""" # Body shows the word, both translations, synonyms, the commonality verdict with its reason, and the lookup link
    logger.info(f"Email body: {email_body}")

    #####################################
    ## Email configuration:
    message = MIMEText(email_body, "html") # Create HTML email message
    message["Subject"] = email_subject_line # Set subject line
    message["From"] = sender_email_account # Set sender address
    message["To"] = ','.join(recipients) # Set recipient addresses

    #####################################
    ## Authentication:
    server = smtplib.SMTP("smtp.gmail.com", 587, local_hostname="localhost") # Connect to Gmail SMTP server
    server.ehlo() # Identify client to server
    server.starttls() # Upgrade connection to TLS
    server.ehlo() # Re-identify after TLS upgrade
    server.login(user = sender_email_account, password = sender_email_password) # Authenticate with App Password

    #####################################
    ## Send Email:
    server.sendmail(from_addr = sender_email_account,
                    to_addrs = recipients,
                    msg = message.as_string()) # Send the email
    server.quit() # Close the SMTP connection
    logger.info("Email successfully sent.")

if __name__ == '__main__':
    word: str = "enseñar" # Target language word
    translation: str = "to teach, to show" # Spreadsheet translation
    ai_translation: str = "to teach" # AI-generated translation
    example_sentence: str = "Me gusta enseñar español a mis amigos." # Example sentence
    example_synonyms: str = "instruir, educar, mostrar." # Example synonyms
    is_common: str = "Yes" # Commonality answer

    emailer(word, translation, ai_translation, example_sentence, example_synonyms, is_common, is_common_reason="Mexicans use this word naturally in everyday speech.")
