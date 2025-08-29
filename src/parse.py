from typing import Dict, Optional, Union

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from src.utils import process_name_str


def parse_card(card: WebElement) -> Dict[str, Optional[Union[str, bool]]]:
    """Strip standardized information from a search result card.

    Parameters
    ----------
    driver : WebDriver
        Selenium webdriver.

    card : WebElement
        HTML card element holding contact information.
    
    Returns
    -------
    Dict[str, Optional[Union[str, bool]]]
        Dictionary holding key information on the parsed alumni.
        Keys: "full", "title", "first", "last", "quick_send"

    """
    # grab the name from the card
    full_name = card.find_element(By.CSS_SELECTOR, ".card__name a").text.strip()
    title, first, last = process_name_str(full_name)

    # grab id (if it exists)
    try:
        # anchor tag inside the card__name
        link = card.find_element(By.CSS_SELECTOR, "h2.card__name a")
        href = link.get_attribute("href")
        
        # the ID is the last segment of the URL (after /person/)
        person_id = href.rstrip("/").split("/")[-1]
    except (NoSuchElementException, Exception):
        person_id = None

    # grab employment (if it exists)
    try:
        # within each card, look for the current-employment section
        employment_div = card.find_element(By.CSS_SELECTOR, "div.current-employment")
        # extract its text as a clean string
        employment = employment_div.text.strip()
    except (NoSuchElementException, Exception):
        # skip if the section doesn't exist
        employment = None

    # check if it's possible to quick send an email
    try:
        card.find_element(
            By.CSS_SELECTOR,
            ".emailButton.ace-search-email-button .buttons a.btn.btn-sm.btn-ace-primary[data-ace-email]"
        )
        quick_send = True
    except NoSuchElementException:
        # container or anchor not present on this card
        quick_send = False

    return {
        "id": person_id,
        "full": full_name,
        "title": title,
        "first": first,
        "last": last,
        "employment": employment,
        "quick_send": quick_send,
    }
