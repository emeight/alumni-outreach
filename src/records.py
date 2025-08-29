import json
import os

from datetime import datetime
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional, Union
from zoneinfo import ZoneInfo

# default timezone
user_tz = ZoneInfo("America/New_York")


def load_records_jsonl(path: str, id_key: str = "id") -> Dict[str, Dict[str, Any]]:
    """Load a .jsonl file into a dictionary keyed by the given id field.

    Parameters
    ----------
    path : str
        Path to the .jsonl file.

    id_key : str, default "id"
        The key inside each JSON object that uniquely identifies the record.

    Returns
    -------
    Dict[str, Dict[str, Any]]
        Dictionary keyed by id, where each value is the record dict.

    """
    records: Dict[str, Dict[str, Any]] = {}

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue  # skip blank lines
            record = json.loads(line)
            record_id = record.get(id_key)
            if record_id is not None:
                records[str(record_id)] = record

    return records


def start_record_keeping(folder_path: str = "records", query: Optional[str] = None, id_key: str = "id") -> Tuple[Dict, Dict]:
    """Load existing records into memory and 

    Parameters
    ----------
    folder_path : str
        Path to the directory used to store records.
        Defaults to "records".

    query : Optional[str]
        Keyword(s) used for search.
        Defaults to None.

    id_key : str
        The key inside each JSON object that uniquely identifies the record.
        Defaults to "id".

    Returns
    -------
    Dict
        Run-specific serializable dictionary.
    
    """

    # remove trailing slash
    if folder_path.endswith("/"):
        folder_path = folder_path[:-1]

    # check that the records folder is correctly structured
    RECORDS_PATH = Path(folder_path)
    if not RECORDS_PATH.is_dir():
        RECORDS_PATH.mkdir(parents=True, exist_ok=True)

    RUNS_PATH = Path(folder_path + "/runs")
    if not RUNS_PATH.is_dir():
        RUNS_PATH.mkdir(parents=True, exist_ok=True)

    SENT_PATH = Path(folder_path + "/sent.jsonl")
    if not SENT_PATH.is_file():
        SENT_PATH.touch()
        sent_dict = {}
    else:
        sent_dict = load_records_jsonl(SENT_PATH, id_key)

    # format the run dictionary
    run_dict = {
        "metadata": {
            "run_start": datetime.now(user_tz).strftime("%Y-%m-%d %H:%M:%S %Z"),
            "run_end": None,
            "path": folder_path + "/" + datetime.now(user_tz).strftime("%Y-%m-%dT%H-%M-%S") + ".json",
            "query": query,
        },
        "results": [],
        "summary": {
            "sent": 0,
            "skipped": 0,
            "seen": 0,
        },
        "success": False,
    }

    return sent_dict, run_dict

def end_record_keeping(run_dict: Dict[str, Union[Dict, List]], folder_path: str = "records") -> None:
    """Save the run and add the key data to the sent file.
    
    Parameters
    ----------
    run_dict : Dict
        Run-specific content pertaining to this instance of the script.

    folder_path : str
        Path to the directory used to store records.
        Defaults to "records".

    """

    # remove trailing slash
    if folder_path.endswith("/"):
        folder_path = folder_path[:-1]

    # the run is complete, record the time
    run_dict["metadata"]["run_end"] = datetime.now(user_tz).strftime("%Y-%m-%d %H:%M:%S %Z")

    # update status counts
    status_counts = Counter(record["status"] for record in run_dict["results"])
    run_dict["metadata"]["sent"] = getattr(status_counts, "sent", 0)
    run_dict["metadata"]["skipped"] = getattr(status_counts, "skipped", 0)
    run_dict["metadata"]["seen"] = getattr(status_counts, "seen", 0)

    # compress results from the run dictionary into the sent records
    with open(folder_path + "/sent.jsonl", "w", encoding="utf-8") as f:
        for result in run_dict["results"]:
            # skip if the result is None or empty
            if result is None or not result:
                continue
            
            # skip if no email was sent
            if getattr(result, "status", None) != "sent":
                continue

            # define the structure for sent entries
            formatted_result = {
                "id": getattr(result, "id", None),
                "first": getattr(result, "first", None),
                "last": getattr(result, "last", None),
                "employment": getattr(result, "employment", None),
            }
            f.write(json.dumps(formatted_result) + "\n")

    # attempt to retrieve the run's start time
    file_path: str = getattr(
        run_dict["metadata"],
        "path",
        folder_path + "/runs/" + datetime.now(user_tz).strftime("%Y-%m-%dT%H-%M-%S") + ".json",
    )

    # save the run
    path = Path(file_path)
    tmp = path.with_suffix(path.suffix + ".tmp")

    # write JSON to a temporary file
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(run_dict, f, indent=2)

    # atomically replace the old file with the new one
    os.replace(tmp, path)


def check_records(
        records_dict: Dict[str, Optional[Union[str, bool]]],
        id: Optional[str] = None,
        first: Optional[str] = None,
        last: Optional[str] = None,
        employment: Optional[str] = None, 
    ) -> bool:
    """Check records to see if any entries match the non-null parameters.

    Parameters
    ----------
    records_dict : Dict[str, Optional[Union[str, bool]]]
        Dictionary corresponding to the .jsonl file where all alumni who've already received an email are logged.
    
    id : Optional[str]
        Alumni unique identifier.
        Defaults to None.

    first : Optional[str]
        First name of alumni.
        Defaults to None.

    last : Optional[str]
        Last name of alumni.
        Defaults to None.

    employment : Optional[str]
        Employment of alumni.
        Defaults to None.

    Returns
    -------
    bool
        True if all parameters match an entry in the provided records_dict.

    """
    # collect all filters that are not None
    filters = {
        "id": id,
        "first": first,
        "last": last,
        "employment": employment,
    }
    filters = {k: v for k, v in filters.items() if v is not None}

    if not filters:
        return False  # nothing to match on

    # assumes records_dict is keyed by id
    for record in records_dict.values():
        if not isinstance(record, dict):
            continue

        # check if *all* non-null filters match this record
        if all(record.get(k) == v for k, v in filters.items()):
            return True

    return False
