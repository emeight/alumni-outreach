import os
import time

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By

from src.login import login_user
from src.parse import parse_card
from src.records import end_record_keeping, check_records, start_record_keeping
from src.search import search_keyword, organize_results
from src.send import send_from_card, send_from_profile


# load environment variables
load_dotenv()

# fetch environment variables
# alumni directory url
alumni_dir_url = os.getenv("ALUMNI_DIR_URL")

# user credentials
username = os.getenv("USERNAME")
password = os.getenv("PASSWORD")

# query
query = os.getenv("QUERY")

# message content
subject = os.getenv("SUBJECT")
base_message = os.getenv("MESSAGE")

# get email limit and set to integer to limit sends
email_limit = input("How many emails would you like to send?: ")
email_limit = min(int(email_limit), 100)

# load the records and initialize the run data
sent_dict, run_dict = start_record_keeping(query=query)

# set the driver
driver = webdriver.Chrome()

# automated actions
login_user(driver, alumni_dir_url, username, password)
search_keyword(driver, query)
organize_results(driver, 50, "Last Name")

# results are served as cards, iterate over them
cards = driver.find_elements(By.CSS_SELECTOR, ".card-and-gutter.card-search")

# default sent count to zero
sent_count = 0
for idx, card in enumerate(cards, start=1):
    # ensure sent count is below limit
    if sent_count >= email_limit:
        print(f"Email limit reached ({email_limit}).")
        break

    # parse result card
    result = parse_card(card)

    # personalize message with greeting
    title = result.get("title", None)
    first_name = result.get("first", None)
    last_name = result.get("last", None)

    # make sure we haven't previously emailed this alumni
    if not check_records(sent_dict, id):
        if (title or last_name) is None:
            greeting = "Hi,"
        else:
            greeting = f"Hi {title} {last_name},"

        # defining message here to keep sanitized
        message = greeting + "\n\n" + base_message

        # attempt email sending
        status = (
            send_from_card(driver, card, subject, message)
            if result["quick_send"]
            else send_from_profile(driver, card, subject, message)
        )

        # if incorrectly routed to card, try again via profile
        if status == "skipped" and result["quick_send"]:
            status = send_from_profile(driver, card, subject, message)
    else:
        status = "seen"

    if status == "sent":
        print(f"Email sent to {first_name} {last_name}")
        sent_count += 1

    # set status
    result["status"] = status
    # record result
    run_dict["results"].append(result)

# write results to records
end_record_keeping(run_dict)

time.sleep(30)

driver.quit()