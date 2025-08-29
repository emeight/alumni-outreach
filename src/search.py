from typing import Literal

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from src.utils import safe_select_option_by_value, shutdown_on_exceptions, sleep_randomly

VIEW_OPTIONS = {10, 25, 50}
SORT_OPTIONS = Literal["relevance", "lastName", "firstName", "classyear", "lastLogin"]

@shutdown_on_exceptions
def search_keyword(driver: WebDriver, query: str, timeout: int = 10) -> None:
    """Search the alumni directory for profiles related to the query. 
    
    Parameters
    ----------
    driver : WebDriver
        Selenium WebDriver.

    query : str
        String to search for.

    timeout : int
        Seconds to wait for presence and clickability of elements.
        Defaults to 10.

    """
    # ensure the search bar is present on the page
    search_input_locator = (By.ID, "searchForText")
    WebDriverWait(driver, timeout).until(EC.presence_of_element_located(search_input_locator))

    # find, clear, and input the query into the search bar
    search_input = driver.find_element(*search_input_locator)
    search_input.clear()
    search_input.send_keys(str(query))

    # sleep for a random amount of time then submit the query
    sleep_randomly(3, 5)
    search_input.submit()


@shutdown_on_exceptions
def organize_results(driver: WebDriver, view_results: Literal[10, 25, 50] = 50, sort_results: SORT_OPTIONS = "lastName", include_decased: bool = False, timeout: int = 10) -> None:
    """Organize directory results based on view and sort parameters.
    
    Parameters
    ----------
    driver : WebDriver
        Selenium WebDriver.
    
    view_results : Literal[10, 25, 50]
        Number of results to view per page.
        Defaults to 50.

    sort_results : Literal["relevance", "lastName", "firstName", "classyear", "lastLogin"]
        Method to sort the results of the query.
        Defaults to "Last Name".

    include_deceased : bool
        Whether or not to include deceased alumni in results.
        Defaults to False.

    timeout : int
        Seconds to wait for presence and clickability of elements.
        Defaults to 10.

    """
    # ensure that the result options are valid, otherwise default
    view_results = view_results if view_results in VIEW_OPTIONS else 50
    sort_results = sort_results if sort_results in SORT_OPTIONS else "lastName"

    # ensure the search bar is present on the page
    result_limit_locator = (By.ID, "limit")
    WebDriverWait(driver, timeout).until(EC.presence_of_element_located(result_limit_locator))
    safe_select_option_by_value(driver, result_limit_locator, str(view_results), timeout, (3, 5))

    pre_limit_url = driver.current_url

    try:
        # wait for URL to change
        WebDriverWait(driver, timeout).until(
            lambda driver: driver.current_url != pre_limit_url
        )
    except TimeoutException:
        # if the page doesn't reload (e.g., selecting default value)
        pass

    pre_sort_url = driver.current_url

    # ensure the search bar is present on the page
    sort_by_locator = (By.ID, "sortBy")
    WebDriverWait(driver, timeout).until(EC.presence_of_element_located(sort_by_locator))
    safe_select_option_by_value(driver, sort_by_locator, str(sort_results), timeout, (3, 5))

    try:
        # wait for URL to change
        WebDriverWait(driver, timeout).until(
            lambda driver: driver.current_url != pre_sort_url
        )
    except TimeoutException:
        # if the page doesn't reload (e.g., selecting default value)
        pass

    # open "Advanced Search Options"
    advanced_link = driver.find_element(By.CSS_SELECTOR, "a.hu2020-top-extra__collapser")
    if advanced_link.get_attribute("aria-expanded") == "false":
        advanced_link.click()
        WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located((By.ID, "facet-deceased"))
        )

    # include/exclude deceased alumni as specified
    checkbox = driver.find_element(By.ID, "facet-deceased")
    if not checkbox.is_selected() and not include_decased:
        # select the checkbox
        checkbox.click()
        
        # the url should change here
        try:
            # wait for URL to change
            WebDriverWait(driver, timeout).until(
                lambda driver: driver.current_url != pre_sort_url
            )
        except TimeoutException:
            # if the page doesn't reload (e.g., selecting default value)
            pass
    else:
        # close "Advanced Search Options"
        if advanced_link.get_attribute("aria-expanded") == "true":
            advanced_link.click()
    
    # chill
    sleep_randomly(2, 5)
