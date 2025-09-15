import os

from collections import Counter
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path
from zoneinfo import ZoneInfo

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from utils import (
    AlumniProfile,
    load_records,
    lookup_alum,
    record_result,
    send_from_modal,
    sleep_randomly,
    write_json_atomic
)


# load environment variables
load_dotenv()

alumni_dir_url = os.getenv("ALUMNI_DIR_URL")

data_dir_path = os.getenv("DATA_DIR")

username = os.getenv("USERNAME")
password = os.getenv("PASSWORD")

query = os.getenv("QUERY")
view_options = os.getenv("VIEW_OPTIONS")
sort_results = os.getenv("SORT_RESULTS")

subject = os.getenv("SUBJECT")
message = os.getenv("MESSAGE")

# get max emails
max_emails = 10  # default
try:
    max_emails = int(input("Maximum emails to send (0 to 100): "))
except ValueError:
    try:
        max_emails = int(input("Try again (0 to 100): "))
    except ValueError:
        print("Defaulting maximum emails to 10.")

max_emails = max(0, min(max_emails, 100))
if max_emails == 0:
    print("Number provided was less than zero, no emails will be sent.")
elif max_emails == 100:
    print("Number provided was greater than 100, defaulting to 100 (maximum).")

# get jitter factor  
jitter_factor = 1.0  # default
try:
    jitter_factor = float(input("Jitter (float >= 0): "))
except ValueError:
    try:
        jitter_factor = float(input("Try again (float >= 0): "))
    except ValueError:
        print("Defaulting jitter factor to 1.")

if jitter_factor < 0:
    print(f"Negatives are not allowed, assuming a jitter factor of {abs(jitter_factor)}")
    jitter_factor = abs(jitter_factor)

# config
timeout = 15  # seconds
min_sleep = 3  # seconds
max_sleep = min_sleep + (min_sleep * jitter_factor)

data_dir = Path(data_dir_path or "data")
data_dir.mkdir(parents=True, exist_ok=True)

records_path = data_dir / "records.json"

runs_dir = data_dir / "runs"
runs_dir.mkdir(parents=True, exist_ok=True)

run_time_format = "%Y-%m-%d %H:%M:%S"
safe_time_format = "%Y-%m-%d_%H-%M-%S"

tz_info = ZoneInfo("America/New_York")
run_start_time = datetime.now(tz_info)
run_path = runs_dir / f"{run_start_time.strftime(safe_time_format)}.json"

# load existing records
records = load_records(records_path)

# run-specific metadata setup
run_data = {
    "query": query,
    "started_at": run_start_time.strftime(run_time_format),
    "ended_at": "",
    "time_elapsed": 0.0,
    "counts": {
        "sent": 0,
        "viewed": 0,
        "skipped": 0,
    },
    "results": {},
}

# initialize the webdriver
driver = webdriver.Chrome()
driver.get(alumni_dir_url)
print(f'Successfully accessed "{alumni_dir_url}".')

# wait until the user provides the query
query_url = alumni_dir_url + "query"
print(f'Please login and enter your query. \nThis script will takeover once the url starts with "{query_url}".')
WebDriverWait(driver, 180).until(
    lambda d: d.current_url.startswith(query_url)
)

# login user
print(f'Logging in via: "{driver.title}".')
if username is None:
    err_msg = "USERNAME environment variable is not set."
    raise ValueError(err_msg)

if password is None:
    err_msg = "PASSWORD environment variable is not set."
    raise ValueError(err_msg)

username_input = WebDriverWait(driver, timeout).until(
    EC.presence_of_element_located((By.ID, "identifier"))
)
username_input.clear()
username_input.send_keys(username)

sleep_randomly(min_sleep, max_sleep)

login_btn = WebDriverWait(driver, timeout).until(
    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-se="save"]'))
)
login_btn.click()

password_input = WebDriverWait(driver, timeout).until(
    EC.presence_of_element_located((By.ID, "credentials.passcode"))
)
password_input.clear()
password_input.send_keys(password)

sleep_randomly(min_sleep, max_sleep)

continue_btn = WebDriverWait(driver, timeout).until(
    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-se="save"]'))
)
continue_btn.click()

print("Login successful, awaiting multi-factor authentication.")

mfa_element = WebDriverWait(driver, timeout).until(
    EC.element_to_be_clickable((By.XPATH, '//button[normalize-space()="Verify"]'))
)
mfa_element.click()

print("MFA request sent, please approve on your device.")
dont_trust_browser_btn = WebDriverWait(driver, 300).until(
    EC.element_to_be_clickable((By.ID, "dont-trust-browser-button"))
)
print("Multi-factor authentication approved.")
sleep_randomly(min_sleep, max_sleep)
dont_trust_browser_btn.click()

dont_stay_signed_in_btn = WebDriverWait(driver, timeout).until(
    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-se="do-not-stay-signed-in-btn"]'))
)
sleep_randomly(min_sleep, max_sleep)
dont_stay_signed_in_btn.click()

print("Successfully accessed the alumni directory.")

# keyword search
search_input = WebDriverWait(driver, timeout).until(
    EC.presence_of_element_located((By.ID, "searchForText"))
)
search_input.clear()
search_input.send_keys(query)
sleep_randomly(min_sleep, max_sleep)
search_input.submit()

# organize results
try:
    view_int = int(view_options)
    # number of results per page, must be one of {10, 25, 50}
    view_options = view_int if view_int in {10, 25, 50} else 50
except ValueError:
    # defaults to 50
    view_options = 50

pre_limit_select_url = driver.current_url
result_limiter = WebDriverWait(driver, timeout).until(
    EC.element_to_be_clickable((By.ID, "limit"))
)
result_limiter_selector = Select(result_limiter)
# view options provided as strings (not integers)
result_limiter_selector.select_by_value(str(view_options))

try:
    # wait for URL to change
    WebDriverWait(driver, timeout).until(
        lambda driver: driver.current_url != pre_limit_select_url
    )
except TimeoutException:
    # if the page doesn't reload (i.e., selecting default value)
    pass

try:
    sort_str = str(sort_results)
    # method to sort the query, must be one of {}"relevance", "lastName", "firstName", "classyear", "lastLogin"}
    valid_sorts = {"relevance", "lastName", "firstName", "classyear", "lastLogin"}
    sort_results = sort_str if sort_str in valid_sorts else "lastName"
except (ValueError, TypeError, AttributeError):
    sort_results = "lastName"

pre_sort_select_url = driver.current_url
result_sorter = WebDriverWait(driver, timeout).until(
    EC.element_to_be_clickable((By.ID, "sortBy"))
)
result_sorter_selector = Select(result_sorter)
result_sorter_selector.select_by_value(str(sort_results))

try:
    # wait for URL to change
    WebDriverWait(driver, timeout).until(
        lambda driver: driver.current_url != pre_sort_select_url
    )
except TimeoutException:
    # if the page doesn't reload (i.e., selecting default value)
    pass

# open "Advanced Search Options"
advanced_link = driver.find_element(By.CSS_SELECTOR, "a.hu2020-top-extra__collapser")
if advanced_link.get_attribute("aria-expanded") == "false":
    advanced_link.click()
    WebDriverWait(driver, 5).until(
        EC.visibility_of_element_located((By.ID, "facet-deceased"))
    )

# exclude deceased alumni
pre_deceseased_sort_url = driver.current_url
checkbox = driver.find_element(By.ID, "facet-deceased")
if not checkbox.is_selected():
    # select the checkbox
    checkbox.click()
    
    # the url should change here
    try:
        # wait for URL to change
        WebDriverWait(driver, timeout).until(
            lambda driver: driver.current_url != pre_deceseased_sort_url
        )
    except TimeoutException:
        # if the page doesn't reload (i.e., selecting default value)
        pass
else:
    # close "Advanced Search Options"
    if advanced_link.get_attribute("aria-expanded") == "true":
        advanced_link.click()

sleep_randomly(min_sleep, max_sleep)

keep_alive = True
emails_sent = 0

while keep_alive:
    # wait until the search-results container is present
    search_results = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CLASS_NAME, "search-results"))
    )

    # wait until there is at least one card inside it
    cards = WebDriverWait(driver, timeout).until(
        EC.presence_of_all_elements_located((By.CLASS_NAME, "card-and-gutter"))
    )

    # iterate over each card
    for idx, card in enumerate(cards, start=1):
        # ensure we have not hit the maximum
        if emails_sent >= max_emails:
            print(f"Maximum number of sent emails has been reached ({max_emails}).")
            keep_alive = False
            break  # break inner (card) loop

        # grab important card elements
        link_elem = WebDriverWait(card, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".card__name a"))
        )

        # extract attributes
        profile_name = link_elem.text.strip()
        profile_url = link_elem.get_attribute("href")

        # url structured as "/person/12345"
        profile_uid = int(profile_url.split("/")[4])

        # creation time
        creation_time = datetime.now(tz_info).strftime(run_time_format)

        # instantiate a record of the profile
        alum_record = AlumniProfile(
            name=profile_name,
            url=profile_url,
            uid=profile_uid,
            status="viewed",
            created_at=creation_time,
            updated_at=creation_time,
        )

        # tailor the messageg
        greeting = f"Hi {alum_record.name},\n\n"
        tailored_message = greeting + message

        try:
            # check if we've seen this alumni before
            if lookup_alum(records, alum_record):
                alum_record.status = "skipped"
                continue

            # check if the quicksend is present
            quicksend_btn = card.find_element(
                By.XPATH,
                ".//a[@data-ace-email and contains(text(), 'Email')]"
            )
            sleep_randomly(min_sleep, max_sleep)
            quicksend_btn.click()

            # send email
            send_from_modal(driver, subject, tailored_message)
            alum_record.status = "sent"
            emails_sent += 1

            # jitter
            sleep_randomly(min_sleep, max_sleep)

        except NoSuchElementException:
            # no quicksend button on this card
            try:
                # try to send from profile
                profile_link = WebDriverWait(driver, timeout).until(
                    EC.element_to_be_clickable((By.XPATH, f"//a[@href='/person/{alum_record.uid}']"))
                )
                sleep_randomly(min_sleep, max_sleep)
                profile_link.click()

                # wait for URL
                WebDriverWait(driver, timeout).until(
                    EC.url_contains(f"/person/{alum_record.uid}")
                )

                # wait for the contact section (may not exist)
                WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.XPATH, "//section[@id='profileContact']"))
                )

                # locate the 'Email Addresses' subsection
                subsection = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        # find the profile-subsection whose <h6> header is exactly "Email Addresses"
                        "//section[@id='profileContact']"
                        "//section[contains(@class,'profile-subsection')][.//h6[normalize-space()='Email Addresses']]"
                    ))
                )

                # find the first <a> in the list under that subsection
                first_email_link = WebDriverWait(subsection, timeout).until(
                    EC.element_to_be_clickable((
                        By.XPATH,
                        ".//ul[contains(@class,'list-unstyled')]//a[1]"
                    ))
                )
                sleep_randomly(min_sleep, max_sleep)
                first_email_link.click()

                # send email
                send_from_modal(driver, subject, tailored_message)
                alum_record.status = "sent"
                emails_sent += 1

                # jitter
                sleep_randomly(min_sleep, max_sleep)

                # go back to the results page
                driver.back()

            except (TimeoutError, NoSuchElementException):
                # unable to send, entry marked as "Viewed"
                continue
        
        finally:
            # record the result
            fields = record_result(records, alum_record)
            run_data["results"][idx] = fields

            # pretty print the result
            max_key_len = max(len(k) for k in fields)
            max_val_len = max(len(str(v)) for v in fields.values())
            box_width = max_key_len + max_val_len + 5

            print("+" + ("-" * box_width) + "+")
            for k, v in fields.items():
                print(f"| {k:<{max_key_len}} : {v:<{max_val_len}} |")
            print("+" + ("-" * box_width) + "+")

    if not keep_alive:
        break  # break the outer (page) loop

    try:
        # go to the next page of results
        next_link = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, "//a[@aria-label='Next Page']"))
        )
        sleep_randomly(min_sleep, max_sleep)
        next_link.click()
    except TimeoutException:
        print("Results exhausted.")
        keep_alive = False


# shutdown the driver
driver.close()

# save the run
run_end_time = datetime.now(tz_info)
elapsed_time = run_end_time - run_start_time
elapsed_time_rounded = round(elapsed_time.total_seconds(), 2)

print(f"Run complete in {elapsed_time_rounded} seconds.")

run_data["ended_at"] = run_end_time.strftime(run_time_format)
run_data["time_elapsed"] = elapsed_time_rounded

# count statuses
status_counts = Counter(
    result.get("status", "").lower() 
    for result in run_data["results"].values()
)

# update run_data
run_data["counts"].update(status_counts)

print("Status Counts:")
for status, count in run_data["counts"].items():
    print(f"  {status.capitalize()}: {count}")

# safe write of the run
write_json_atomic(run_path, run_data)

# safe rewrite of the results
write_json_atomic(records_path, records)
