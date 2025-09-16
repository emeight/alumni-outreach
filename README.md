# alumni-outreach
Automation script for alumni outreach.

This tool logs into the alumni directory, retrieves contact details, and sends personalized emails while maintaining a record of prior outreach to ensure no individual is contacted more than once.

## Quickstart
If you're in a hurry to get things moving, follow the steps below:

1. Setup the virtual environment

    ```
    poetry install
    poetry shell
    ```

2. Create a .env file

    This must include the following variables, set as strings:
    ```
    # alumni directory url (must start with "https://")
    ALUMNI_DIR_URL="https://umich.edu/alumni/"

    # login credentials
    USERNAME="jackblack123"
    PASSWORD="supersecretpassword"

    # data directory path
    DATA_DIR="data/"

    # action delay factor (float >= 0)
    JITTER = 1.0

    # query
    QUERY = "rocket scientist"

    # message content
    SUBJECT = "Rocketship for Sale"
    MESSAGE = "Are you intersted in buying a rocketship?"
    ```

3. Run the script
    ```
    python main.py
    ```

4. Specify quantity of emails to send (max 100)
    ```console
    $ poetry run python main.py
    Maximum emails to send (0 to 100):
    ```

5. Complete multi-factor authentication on your mobile device

Following completion of MFA, no further action is necessary from the user. The results will be saved to the location specified by the `DATA_DIR` variable within the `.env` file.

## Virtual Environment

This project uses [Poetry](https://python-poetry.org/) to manage dependencies and virtual environments.  
All dependencies are defined in the `pyproject.toml` file. To get started:

1. Install the project dependencies via poetry (this creates the virtual environment automatically):

    ```
    poetry install
    ```

2. Activate the virtual environment:

    ```
    poetry shell
    ```

## Environment Variables

This project relies on a `.env` file to configure sensitive information and runtime settings.  
Create a `.env` file in the project root and define the following variables:

- **`ALUMNI_DIR_URL`** – Base URL of the alumni directory to scrape.  
- **`USERNAME`** – Login username for the alumni directory.  
- **`PASSWORD`** – Login password for the alumni directory.  
- **`DATA_DIR`** – Local directory path where run logs, records, and other output data will be stored.
- **`JITTER`** - Action delay factor.
- **`QUERY`** - Keywords to search for.
- **`SUBJECT`** - Email subject line.
- **`MESSAGE`** - Email body content.


Example `.env` file:

```
# alumni directory url
ALUMNI_DIR_URL="https://umich.edu/alumni/"

# login credentials
USERNAME="jackblack123"
PASSWORD="supersecretpassword"

# data directory path
DATA_DIR="data/"

# action delay factor (float >= 0)
JITTER = 1.0

# query
QUERY = "rocket scientist"

# message content
SUBJECT = "Rocketship for Sale"
MESSAGE = "Are you intersted in buying a rocketship?"
```

## Running the Script

Once the environment variables are setup and the virtual environment is active, running the script is as simple as executing the following command:

```
python main.py
```

You will then be prompted for the number of emails you would like to send (max 100). The only other action that's necessary will be approving the MFA notification on your mobile device.

## Saving Results

The results of each run are saved to a `/runs` folder within the `DATA_DIR` (directory) specified in your `.env` file. 

A `records.json` file will be created inside the `DATA_DIR` directory. This file is automatically loaded and updated on each run to keep track of alumni who have already been contacted, ensuring that no individual is emailed more than once.
