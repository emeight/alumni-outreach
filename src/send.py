from typing import Optional

from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from src.utils import shutdown_on_exceptions, sleep_randomly


@shutdown_on_exceptions
def send_from_modal(driver: WebDriver, subject: str, message: str, send_copy: bool = True, timeout: int = 10)-> None:
    """Send an email with the provided message to the alumni via the modal.

    The modal must be on the screen in order for this to work.

    Parameters
    ----------
    driver : WebDriver
        Selenium webdriver.

    card : WebElement
        HTML card element holding contact information.

    subject : str
        Subject line for the email.

    message : str
        Text to send to the alumni associated with the card.
    
    send_copy : bool
        Whether or not to send a copy of the email to yourself.
        Defaults to True.

    timeout : int
        Seconds to wait for presence and clickability of elements.
        Defaults to 10.

    Raises
    ------
    RuntimeError
        If unable to close the modal.

    """
    # subject
    subject_input = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "input#subject"))
    )
    subject_input.clear()
    subject_input.send_keys(subject)

    # message
    message_input = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "textarea#message"))
    )
    message_input.click()
    message_input.clear()
    message_input.send_keys(message)

    # handle copy checkbox
    try:
        copy_checkbox = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((By.ID, "copySender"))
        )
        if copy_checkbox.is_selected() != send_copy:
            copy_checkbox.click()
    except (TimeoutException, NoSuchElementException):
        # treat as a non-fatal; modal still usable
        pass

    # click the Send button
    send_button = driver.find_element(By.CSS_SELECTOR, "button.btn.btn-ace-primary.btn-sm.btn-wide[type='submit']")
    send_button.click()
    
    send_button = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn.btn-ace-primary.btn-sm.btn-wide[type='submit']"))
    )
    send_button.click()

    # close the modal
    try:
        close_btn = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#aceEmailForm button.btn.btn-ace-primary.btn-sm.btn-wide[data-dismiss='modal']"))
        )
        close_btn.click()
    except TimeoutException:
        # fallback to the top-right x button
        try:
            x_btn = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#aceEmailForm button.close[data-dismiss='modal']"))
            )
            x_btn.click()
        except TimeoutException as e:
            err_msg = "Fatal: unable to close the email modal."
            raise RuntimeError(err_msg) from e

    # confirm the modal actually closed
    WebDriverWait(driver, timeout).until(
        EC.invisibility_of_element_located((By.CSS_SELECTOR, "#aceEmailForm .modal-content"))
    )


@shutdown_on_exceptions
def send_from_card(driver: WebDriver, card: WebElement, subject: str, message: str, send_copy: bool = True, timeout: int = 10) -> str:
    """Send an email with the provided message to the alumni associated with the card.

    This method relies on the presence of the "Email" button on the result card.

    Parameters
    ----------
    driver : WebDriver
        Selenium webdriver.

    card : WebElement
        HTML card element holding contact information.

    subject : str
        Subject line for the email.

    message : str
        Text to send to the alumni associated with the card.
    
    send_copy : bool
        Whether or not to send a copy of the email to yourself.
        Defaults to True.

    timeout : int
        Seconds to wait for presence and clickability of elements.
        Defaults to 10.

    Returns
    -------
    str
        Status of the action ("sent" or "fail").

    """
    try:
        # locate the email button on the card
        email_button = card.find_element(By.CSS_SELECTOR, "a.btn.btn-sm.btn-ace-primary[data-ace-email]")
        email_button.click()

        # ensure modal is up before we look for buttons
        WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "#aceEmailForm .modal-content"))
        )

        # this should shutdown the driver on self contained exceptions
        send_from_modal(driver, subject, message, send_copy, timeout)

        return "sent"
    except (NoSuchElementException, TimeoutException):
        return "fail"


@shutdown_on_exceptions
def get_email_addresses_section(driver: WebDriver, timeout: int = 10) -> Optional[WebElement]:
    """Return the 'Email Addresses' section element if present; otherwise None.

    Looks for a "section" with class 'profile-subsection' whose header "h6"
    text contains 'Email Address' (case-insensitive, handles plural/singular).

    Parameters
    ----------
    driver : WebDriver
        Selenium WebDriver.

    timeout : int
        Seconds to wait for presence and clickability of elements.
        Defaults to 10.

    Returns
    -------
    Optional[WebElement]
        Selenium WebElement object if the email addresses section is found, otherwise None.
    
    """
    xpath = (
        "//section[contains(@class,'profile-subsection')][.//header//h6"
        "[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'email address')]]"
    )
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
    except TimeoutException:
        return None


def send_from_profile(driver: WebDriver, card: WebElement, subject: str, message: str, send_copy: bool = True, timeout: int = 10) -> str:
    """Send an email with the provided message to the alumni associated with the card.

    This method relies on the ability to access the alumni's profile via their result card.

    Parameters
    ----------
    driver : WebDriver
        Selenium webdriver.

    card : WebElement
        HTML card element holding contact information.

    subject : str
        Subject line for the email.

    message : str
        Text to send to the alumni associated with the card.
    
    send_copy : bool
        Whether or not to send a copy of the email to yourself.
        Defaults to True.

    timeout : int
        Seconds to wait for presence and clickability of elements.
        Defaults to 10.

    Returns
    -------
    str
        Status of the action ("sent" or "skipped").

    """
    # access the user's profile
    name_link = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, ".card__name a"))
    )
    name_link.click()

    # chill
    sleep_randomly(3, 6)

    # check for alternative emails
    addresses = get_email_addresses_section(driver, timeout)
    if addresses is None:
        return "skipped"

    # default the status to viewed
    status = "viewed"

    # check if there's a preferred email
    try:
        # try preferred email first
        preferred = driver.find_element(
            By.CSS_SELECTOR,
            "section.profile-subsection ul li.address-preferred a"
        )
        WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(preferred))
        preferred.click()

    except NoSuchElementException:
        # no preferred email, fall back
        try:
            # fallback: first email link in the list
            first_email = driver.find_element(
                By.CSS_SELECTOR,
                "section.profile-subsection ul li.address-url a"
            )
            WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(first_email))
            first_email.click()
        except NoSuchElementException:
            # can't access the email
            status = "skipped"

    if status != "skipped":
        # send the email if the modal is available
        send_from_modal(driver, subject, message, send_copy, timeout)

    # exit the profile page
    driver.back()
    
    # ensure we're back to the card results
    WebDriverWait(driver, timeout).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "div.search-results"))
    )

    return "sent"