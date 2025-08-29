import random
import sys
import time
import traceback

from functools import wraps
from typing import Optional, Tuple, Union
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC


def sleep_randomly(min_time: Union[int, float] = 0, max_time: Union[int, float] = 0) -> None:
    """Sleep for a random amount of time.

    Parameters
    ----------
    min_time : Union[int, float]
        Minimum number of seconds to sleep for.
    
    max_time : Union[int, float]
        Maximum number of seconds to sleep for.

    """
    time.sleep(random.uniform(*map(float, sorted((min_time, max_time)))))


def kill_gracefully(driver: WebDriver, exception: Optional[BaseException] = None, message: Optional[str] = None, code: int = 1) -> None:
    """Terminate the script and WebDriver cleanly.
    
    Parameters
    ----------
    driver : WebDriver
        Selenium WebDriver.

    exception : Optional[BaseException]
        Exception that triggered shutdown.
        Defaults to None.

    message : Optional[str]
        Additional context message.
        Defaults to None.

    code : int
        Exit code; nonzero means error.
        Defaults to 1.

    """
    if message:
        print(message, file=sys.stderr)
    if exception:
        print(f"{type(exception).__name__}: {exception}", file=sys.stderr)
        traceback.print_exc()
    try:
        driver.quit()
    finally:
        sys.exit(code)


def shutdown_on_exceptions(func):
    """Exit scripts and quit drivers on exceptions.

    Decorator that catches *all* exceptions in the decorated function,
    attempts to locate a Selenium WebDriver in the arguments,
    and shuts down cleanly via kill_gracefully.

    Usage
    -----
    @shutdown_on_exceptions
    def my_func(driver, ...):
        ...

    """
    @wraps(func)
    def _inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except BaseException as e:  # catch literally everything
            # Try to locate WebDriver in args/kwargs
            driver: Optional[WebDriver] = None
            for arg in args:
                if isinstance(arg, WebDriver):
                    driver = arg
                    break
            if driver is None:
                for value in kwargs.values():
                    if isinstance(value, WebDriver):
                        driver = value
                        break

            if driver:
                kill_gracefully(driver, e, message=f"Fatal error in {func.__name__}")
            else:
                print(f"Fatal error in {func.__name__}: {type(e).__name__}: {e}", file=sys.stderr)
                sys.exit(1)

    return _inner


def safe_button_click(driver: WebDriver, locator: Tuple[str, str], timeout: int = 10, sleep_range: Tuple[float, float] = (0, 0)) -> None:
    """Find a button, wait until clickable, and click once.

    If the button is not found and clicked, the script will be killed gracefully.

    Parameters
    ----------
    driver : WebDriver
        Selenium WebDriver.

    locator : Tuple[str, str]
        Tuple of (By, value), i.e., (By.XPATH, "//button[.='Verify']").

    timeout : int
        Seconds to wait for presence and clickability.
        Defaults to 10.

    sleep_range : Tuple[float, float]
        Tuple of (float, float), representing a range of seconds to randomly select between to sleep before clicking.
        Defaults to (0, 0).

    """
    # default errors to None
    err_msg, e = None, None

    try:
        try:
            # wait for element to be present in DOM
            WebDriverWait(driver, timeout).until(EC.presence_of_element_located(locator))
        except TimeoutException:
            err_msg = f"Element {locator} not found within {timeout}s."
            raise

        try:
            # wait for element to be visible and clickable
            WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(locator))
        except TimeoutException:
            err_msg = f"Element {locator} not clickable within {timeout}s."
            raise

        try:
            # sleep for a random amount of time before clicking the button
            sleep_randomly(*sleep_range)
            # click the button
            driver.find_element(*locator).click()
        except (NoSuchElementException, StaleElementReferenceException, ElementClickInterceptedException, ElementNotInteractableException) as ex:
            err_msg = f"Failed to click element {locator}: {ex}"
            raise

    except Exception as ex:
        e = ex
        # only set if not already set by inner try/catch
        if not err_msg:
            err_msg = f"Unexpected error while attempting to safely click {locator}: {ex}"

    finally:
        # if an error was encountered, shutdown the script
        if e is not None:
            kill_gracefully(driver, e, err_msg)


def safe_select_option_by_value(
    driver: WebDriver, 
    locator: Tuple[str, str], 
    option_value: str,
    timeout: int = 10, 
    sleep_range: Tuple[float, float] = (0, 0)
) -> None:
    """Find a select element, wait until interactable, and select option by value.

    If the select element is not found or option cannot be selected, the script will be killed gracefully.

    Parameters
    ----------
    driver : WebDriver
        Selenium WebDriver.

    locator : Tuple[str, str]
        Tuple of (By, value), i.e., (By.ID, "limit").

    option_value : str
        The value attribute of the option to select, i.e., "25".

    timeout : int
        Seconds to wait for presence and interactability.
        Defaults to 10.

    sleep_range : Tuple[float, float]
        Tuple of (float, float), representing a range of seconds to randomly select between to sleep before selecting.
        Defaults to (0, 0).

    """
    # default errors to None
    err_msg, e = None, None

    try:
        try:
            # wait for select element to be present in DOM
            WebDriverWait(driver, timeout).until(EC.presence_of_element_located(locator))
        except TimeoutException:
            err_msg = f"Select element {locator} not found within {timeout}s."
            raise

        try:
            # wait for select element to be visible and interactable
            WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(locator))
        except TimeoutException:
            err_msg = f"Select element {locator} not interactable within {timeout}s."
            raise

        try:
            # sleep for a random amount of time before selecting the option
            sleep_randomly(*sleep_range)
            
            # find the select element and create Select object
            select_element = driver.find_element(*locator)
            select = Select(select_element)
            
            # verify the option exists before attempting to select it
            available_options = [option.get_attribute('value') for option in select.options]
            if option_value not in available_options:
                err_msg = f"Option with value '{option_value}' not found in select {locator}. Available options: {available_options}"
                raise NoSuchElementException(err_msg)
            
            # select the option by value
            select.select_by_value(option_value)
            
        except (NoSuchElementException, StaleElementReferenceException, ElementNotInteractableException) as ex:
            err_msg = f"Failed to select option '{option_value}' from select element {locator}: {ex}"
            raise

    except Exception as ex:
        e = ex
        # only set if not already set by inner try/catch
        if not err_msg:
            err_msg = f"Unexpected error while attempting to safely select option '{option_value}' from {locator}: {ex}"

    finally:
        # if an error was encountered, shutdown the script
        if e is not None:
            kill_gracefully(driver, e, err_msg)



def process_name_str(name_str: str) -> Tuple[str, str, str]:
    """Break a name string into parts.
    
    Parameters
    ----------
    name_str : str
        String containing a full name.

    Raises
    ------
    ValueError
        If the string cannot be split into title, first, last names.

    Returns
    -------
    Tuple[str, str, str]
        Tuple of name elements ordered as (title, first name, last name)

    """
    titles = ["Mr.", "Mrs.", "Ms.", "Dr."]
    suffixes = ["CFA", "ESQ", "I", "II", "III", "IV", "V", "Jr.", "Sr."]


    # combine for filtering
    remove_words = set(w.lower() for w in titles + suffixes)

    split_str = name_str.split()

    # keep only words not in remove_words (case-insensitive check)
    cleaned_name = [x for x in split_str if x.lower() not in remove_words]

    # ensure our name candidates exist
    try:
        # the title is always first
        title = split_str[0] if split_str[0] in titles else "Mr."
    
        # grab names from cleaned string
        first = cleaned_name[0]
        last = cleaned_name[-1]

    except IndexError:
        err_msg = "Full name not retrieved."
        raise ValueError(err_msg)

    return (title, first, last)
