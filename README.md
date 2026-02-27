# tempsaleread

A small utility to extract sales invoice data from PDF files and output an Excel register.

## Features

* Scans a directory for `.pdf` invoice files
* Extracts key fields like invoice number, date, party, GSTN, tax amounts, and totals
* Normalises numeric values and dates
* Provides a CLI with configurable input/output paths and verbose logging

## Requirements

```sh
pip install pdfplumber pandas python-dateutil
```

`python-dateutil` is optional; the script will still work without it.

## Usage

```sh
python sales_extract.py [--input DIR] [--output FILE] [-v]
```

* `--input` / `-i` – folder containing invoice PDFs.
  Defaults to `C:\Users\jhanw\Downloads\FEBRUARY 2026`.
* `--output` / `-o` – path of the Excel file to create (default: `Sales_Register.xlsx`).
* `-v` – verbose logging to see progress and warnings.

### Example

```sh
python sales_extract.py \
    --input "C:\Users\jhanw\Downloads\FEBRUARY 2026" \
    --output my_register.xlsx -v
```

## Development

`src` file is `sales_extract.py`; feel free to adjust regex patterns or add new
fields as needed.

### Running tests

A minimal `pytest` suite verifies error handling and ignores for non-PDF
files. Install `pytest` and run from the repo root:

```sh
pip install pytest
pytest -q
```


---

*Generated on February 27, 2026.*