#!/usr/bin/env python3
"""Extract invoice fields from PDFs into an Excel sales register.

Usage:
    python sales_extract.py --input /path/to/invoices --output Sales_Register.xlsx

The script is tolerant to missing fields and attempts to normalize numeric values.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import pdfplumber
import pandas as pd


# try to use dateutil if available for robust date parsing
try:
    from dateutil import parser as dateparser
except Exception:
    dateparser = None


LOG = logging.getLogger(__name__)


def parse_number(s: Optional[str]) -> Optional[float]:
    if not s:
        return None
    s = str(s).strip()
    # remove common non-numeric characters
    s = s.replace(',', '')
    s = s.replace(' ', '')
    # handle parentheses as negative numbers
    if s.startswith('(') and s.endswith(')'):
        s = '-' + s[1:-1]
    try:
        return float(s)
    except ValueError:
        return None


def first_match(pattern: re.Pattern, text: str, group: int = 1) -> str:
    m = pattern.search(text)
    if not m:
        return ""
    try:
        return (m.group(group) or "").strip()
    except IndexError:
        return m.group(1).strip()


def extract_text_from_pdf(path: Path) -> str:
    text_parts = []
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ''
                text_parts.append(page_text)
    except Exception as exc:
        LOG.warning("Failed to open %s: %s", path, exc)
    return "\n".join(text_parts)


def normalize_date(date_str: str) -> str:
    if not date_str:
        return ""
    date_str = date_str.strip()
    # try dateutil if available
    if dateparser:
        try:
            dt = dateparser.parse(date_str, dayfirst=False)
            return dt.strftime('%Y-%m-%d')
        except Exception:
            pass
    # fallback: try common formats
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%y"):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime('%Y-%m-%d')
        except Exception:
            continue
    return date_str


def process_folder(folder_path: Path) -> pd.DataFrame:
    if not folder_path.exists() or not folder_path.is_dir():
        raise FileNotFoundError(f"Input folder does not exist: {folder_path}")

    # compile regex patterns (case-insensitive)
    invoice_re = re.compile(r"Invoice\s*(?:No\.?|Number)?[:\s\-]*([A-Z0-9\-/]+)", re.I)
    date_re = re.compile(r"(?:Invoice\s*Date|Date)[:\s\-]*([0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4}|[0-9]{4}[-/][0-9]{2}[-/][0-9]{2})", re.I)
    gstn_re = re.compile(r"GST(?:IN| No\.?|IN)?[:\s\-]*([0-9A-Z]{15,20})", re.I)

    taxable_re = re.compile(r"Taxable\s*Value[:\s\-]*([\d,]+\.?\d*)", re.I)
    igst_re = re.compile(r"IGST[:\s\-]*([\d,]+\.?\d*)", re.I)
    cgst_re = re.compile(r"CGST[:\s\-]*([\d,]+\.?\d*)", re.I)
    sgst_re = re.compile(r"SGST[:\s\-]*([\d,]+\.?\d*)", re.I)
    total_re = re.compile(r"Total(?:\s*Amount)?[:\s\-]*([\d,]+\.?\d*)", re.I)

    # party detection: look for 'Bill To', 'Sold To', 'Party' etc.
    party_re = re.compile(r"(?:Bill To|Sold To|Party|Consignee)[:\s\-]*([A-Z0-9&\.,\-\s]+)", re.I)

    rows = []

    for pdf_file in sorted(folder_path.iterdir()):
        if pdf_file.suffix.lower() != '.pdf':
            continue
        LOG.info("Processing %s", pdf_file.name)
        text = extract_text_from_pdf(pdf_file)
        if not text.strip():
            LOG.warning("No text extracted from %s", pdf_file.name)
            continue

        invoice_no = first_match(invoice_re, text)
        date_raw = first_match(date_re, text)
        date_norm = normalize_date(date_raw)

        gstn = first_match(gstn_re, text)
        party = first_match(party_re, text)

        taxable = parse_number(first_match(taxable_re, text))
        igst = parse_number(first_match(igst_re, text))
        cgst = parse_number(first_match(cgst_re, text))
        sgst = parse_number(first_match(sgst_re, text))
        total = parse_number(first_match(total_re, text))

        rows.append({
            'Invoice No': invoice_no,
            'Date': date_norm,
            'Party': party,
            'GSTN': gstn,
            'Taxable': taxable,
            'IGST': igst,
            'CGST': cgst,
            'SGST': sgst,
            'Total': total,
            'Source File': pdf_file.name,
        })

    df = pd.DataFrame(rows)
    if df.empty:
        LOG.warning("No invoices found in %s", folder_path)
    else:
        df.insert(0, 'Sr', range(1, len(df) + 1))
    return df


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description='Extract sales invoice data from PDFs into Excel')
    p.add_argument(
        '--input', '-i',
        type=Path,
        default=Path(r"C:\Users\jhanw\Downloads\FEBRUARY 2026"),
        help='Input folder containing PDF invoices (default: %(default)s)'
    )
    p.add_argument(
        '--output', '-o',
        type=Path,
        default=Path('Sales_Register.xlsx'),
        help='Output Excel file'
    )
    p.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format='%(levelname)s: %(message)s')

    try:
        df = process_folder(args.input)
    except Exception as exc:
        LOG.error("Failed to process folder: %s", exc)
        return 2

    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        df.to_excel(args.output, index=False)
        LOG.info('Wrote %d rows to %s', len(df), args.output)
    except Exception as exc:
        LOG.error("Failed to write Excel file: %s", exc)
        return 3

    LOG.info('Sales Register Created Successfully')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
