# Divar Real Estate Scraper

A small Python project for collecting real-estate listings from Divar in Lahijan, Iran.

I built this project to gather property listings in one place, clean the useful information, and make it easier to compare listings by neighborhood and transaction type.

## What it does

The scraper:

- Collects real-estate listings from Lahijan
- Goes through multiple result pages automatically
- Opens each listing and extracts detailed property information
- Keeps personal listings
- Detects the transaction type
- Saves the final data into a CSV file

Supported transaction types include:

- Sale
- Full deposit
- Deposit + rent
- Rent
- Short-term rent

## Collected fields

For each listing, the project currently saves:

- Transaction type
- District
- Area
- Construction year
- Number of rooms
- Total price
- Price per square meter
- Floor
- Publication date
- Direct Divar link

Some fields may be empty depending on the type of property. For example, land listings may not have a construction year, room count, or floor number.

## Requirements

- Python 3
- requests

Install the dependencies with:

```bash
pip install -r requirements.txt
```

## How to run

Run the scraper from the project directory:

```bash
python3 divar_csv.py
```

After the script finishes, the results are saved in:

```text
divar_lahijan.csv
```

## Project structure

```text
SCRAPER/
├── divar_csv.py
├── README.md
├── requirements.txt
├── .gitignore
└── divar_lahijan.csv
```

The CSV output is excluded from Git through `.gitignore`.

## Output

Each row in the CSV represents one property listing.

The dataset can later be used for things like:

- Comparing property prices between neighborhoods
- Grouping listings by transaction type
- Comparing price per square meter
- Studying the Lahijan housing market
- Preparing tables or reports for further analysis