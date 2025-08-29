from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from src.utils import safe_button_click, shutdown_on_exceptions


@shutdown_on_exceptions
def login_user(driver: WebDriver, alumni_dir_url: str, username: str, password: str, timeout: int = 10):
    """Login to the alumni directory.
    
    Parameters
    ----------
    driver : WebDriver
        Selenium WebDriver.

    alumni_dir_url : str
        URL of the alumni directory.

    username : str
        Email associated with user.
    
    password : str
        Password associated with user.

    timeout : int
        Seconds to wait for presence and clickability.
        Defaults to 10.

    """
    # access the alumni directory
    driver.get(alumni_dir_url)
    print("Logging in via", driver.title)

    # raise an error if username or password is None
    if username is None:
        err_msg = "USERNAME environment variable is not set."
        raise ValueError(err_msg)
    
    if password is None:
        err_msg = "PASSWORD environment variable is not set."
        raise ValueError(err_msg)

    identifier_locator = (By.ID, "identifier")
    WebDriverWait(driver, timeout).until(EC.presence_of_element_located(identifier_locator))

    # locate, clear, and input the username
    identifier_input = driver.find_element(*identifier_locator)
    identifier_input.clear()
    identifier_input.send_keys(username)

    # click the "Next" button to continue
    safe_button_click(driver, (By.CSS_SELECTOR, 'button[data-se="save"]'), timeout, (3, 5))

    password_locator = (By.ID, "credentials.passcode")
    WebDriverWait(driver, timeout).until(EC.presence_of_element_located(password_locator))

    # locate, clear, and input the password
    password_input = driver.find_element(*password_locator)
    password_input.clear()
    password_input.send_keys(password)

    # click the "Verify" button to continue
    safe_button_click(driver, (By.CSS_SELECTOR, 'button[data-se="save"]'), timeout, (3, 5))

    mfa_locator = (By.XPATH, '//button[normalize-space()="Verify"]')
    WebDriverWait(driver, timeout).until(EC.presence_of_element_located(mfa_locator))

    # click "Verify" button again to proceed with MFA
    safe_button_click(driver, mfa_locator, timeout, (3, 5))

    # MFA, user must manually approve the request via their own external methods
    print("Please complete MFA authentication on your device...")

    try:
        # wait for MFA to complete and browser configurations to appear
        browser_trust_locator = (By.ID, "dont-trust-browser-button")
        WebDriverWait(driver, 300).until(EC.presence_of_element_located(browser_trust_locator))  # 5 minute timeout
        print("MFA completed, proceeding...")
    except TimeoutException:
        raise TimeoutException("MFA authentication timed out after 5 minutes")
 
    # don't trust the browser
    safe_button_click(driver, (By.ID, "dont-trust-browser-button"), timeout, (3, 5))
    
    # really don't trust the browser
    safe_button_click(driver, (By.CSS_SELECTOR, 'button[data-se="do-not-stay-signed-in-btn"]'), timeout, (3, 5))