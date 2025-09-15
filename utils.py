import json
import os
import random
import tempfile
import time

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Literal, Union
from zoneinfo import ZoneInfo

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


@dataclass
class AlumniProfile:
    name: str
    url: str
    # records key
    uid: int
    # sent (successfully sent), viewed (couldn't send), skipped (sent before)
    status: Literal["sent", "viewed", "skipped"]
    # time data
    created_at : str 
    updated_at : str


def _now_et() -> str:
    """Daylight savings time-aware now function for Eastern Time."""
    return datetime.now(ZoneInfo("America/New_York")).strftime("%m-%d-%Y %H:%M:%S")


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


def send_from_modal(driver: WebDriver, subject: str, message: str, send_copy: bool = True, timeout: int = 15)-> None:
    """Send an email with the provided message to the alumni via the modal.

    The modal must be on the screen in order for this to work.

    Parameters
    ----------
    driver : WebDriver
        Selenium webdriver.

    subject : str
        Subject line for the email.

    message : str
        Message content of the email.
    
    send_copy : bool
        Whether or not to send a copy of the email to yourself.
        Defaults to True.

    timeout : int
        Seconds to wait for presence and clickability of elements.
        Defaults to 15.

    """
    # subject
    subject_input = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "input#subject"))
    )
    subject_input.click()
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
    copy_checkbox = WebDriverWait(driver, timeout).until(
        EC.visibility_of_element_located((By.ID, "copySender"))
    )
    if copy_checkbox.is_selected() != send_copy:
        copy_checkbox.click()

    # click the Send button
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
        x_btn = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#aceEmailForm button.close[data-dismiss='modal']"))
        )
        x_btn.click()

    # confirm the modal actually closed
    WebDriverWait(driver, timeout).until(
        EC.invisibility_of_element_located((By.CSS_SELECTOR, "#aceEmailForm .modal-content"))
    )


def lookup_alum(records: Dict[int, Dict[str, Any]], alum: AlumniProfile) -> bool:
    """Lookup an alumni in the records dictionary (keyed by uid (int)).

    Parameters
    ----------
    records : Dict[int, Dict[str, Any]]
        Alumni records dictionary keyed by uid (int).
    
    alum : AlumniProfile
        AlumniProfile instance of the alumni to lookup.

    Returns
    -------
    bool
        Whether or not the alum is present in the records dict.

    """

    try:
        records[alum.uid]
        return True

    except KeyError:
        return False


def load_records(path: Path) -> Dict[int, Dict[str, Any]]:
    """Return a plain dict of records keyed by unique identifier (uid : int).
    
    Parameters
    ----------
    path : Path
        Path object to the records file.

    Returns
    -------
    Dict[int, Dict[str, Any]]
        Plain dict of records keyed by uid (int).

    """
    if not path.exists():
        return {}
    
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Convert string keys back to int keys
        return {int(k): v for k, v in data.items()} if isinstance(data, dict) else {}
    except (json.JSONDecodeError, ValueError, OSError):
        return {}


def record_result(records: Dict[int, Dict[str, Any]], alum: AlumniProfile) -> Dict[str, Any]:
    """Record an AlumniProfile instance in the records dictionary as a plain dict.

    Parameters
    ----------
    records : Dict[int, Dict[str, Any]]
        Alumni records dictionary keyed by uid (int).
    
    alum : AlumniProfile
        AlumniProfile instance of the alumni to record.

    Returns
    -------
    Dict[str, Any]
        Dictionary instance of the record.

    """
    existing = records.get(alum.uid)

    new_rec = {
        "uid": alum.uid,
        "name": alum.name,
        "url": alum.url,
        "status": alum.status,
        "created_at": getattr(alum, "created_at", _now_et()),
        "updated_at": _now_et(),
    }

    # preserve existing created_at field
    if isinstance(existing, dict):
        if "created_at" in existing:
            new_rec["created_at"] = existing["created_at"]

    records[alum.uid] = new_rec

    # return the instance
    return new_rec


def write_json_atomic(path: Path, data: Dict[str, Dict[str, Any]]) -> None:
    """Atomically write JSON to `path` (safe on POSIX/NTFS)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, dir=path.parent, encoding="utf-8") as tmp:
        json.dump(data, tmp, indent=2)
        tmp.flush()           # ensure bytes hit disk
        os.fsync(tmp.fileno())  # extra safety on crashes
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, path)  # atomic replace
