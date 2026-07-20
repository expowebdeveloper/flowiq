import re

MONEY_RE = re.compile(r"(?:rs\.?|inr|₹)\s?([\d,]+(?:\.\d+)?)", re.IGNORECASE)
GRAMS_RE = re.compile(r"([\d.]+)\s?(?:grams?|gms?|g\b)", re.IGNORECASE)
CARAT_RE = re.compile(r"\b(1[0-9]|2[0-4])\s?k(?:arat)?\b", re.IGNORECASE)

US_STATES = (
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado", "connecticut",
    "delaware", "florida", "georgia", "hawaii", "idaho", "illinois", "indiana", "iowa",
    "kansas", "kentucky", "louisiana", "maine", "maryland", "massachusetts", "michigan",
    "minnesota", "mississippi", "missouri", "montana", "nebraska", "nevada",
    "new hampshire", "new jersey", "new mexico", "new york", "north carolina",
    "north dakota", "ohio", "oklahoma", "oregon", "pennsylvania", "rhode island",
    "south carolina", "south dakota", "tennessee", "texas", "utah", "vermont",
    "virginia", "washington", "west virginia", "wisconsin", "wyoming",
)

# Driver's licenses/state IDs pack several short label:value pairs on the same
# printed line (e.g. "SEX F EYES BR HT 5-09", "ISSUED 09-30-08 EXPIRES
# 10-01-16") rather than one label per line like a tabular document, so each
# field needs its own regex anchored on its specific label rather than a
# generic "take the rest of the line" line-scan.
# License/ID numbers vary by state — some are pure digits (e.g. New York's
# "012 345 678"), others prefix a letter or two before the digits (e.g.
# California's "F1234567"). Matches either shape after an ID/DL/LIC label.
_ID_NUMBER_RE = re.compile(r"\b(?:id|dl|lic)\s*[:#]?\s*([A-Z]{0,2}[0-9][0-9 ]{5,15}[0-9])\b", re.IGNORECASE)
_DOB_RE = re.compile(r"\bdob\s*[:\-]?\s*(\d{1,2}[\-/]\d{1,2}[\-/]\d{2,4})", re.IGNORECASE)
_ISSUED_RE = re.compile(r"\b(?:iss|issued)\s*[:\-]?\s*(\d{1,2}[\-/]\d{1,2}[\-/]\d{2,4})", re.IGNORECASE)
_EXPIRES_RE = re.compile(r"\b(?:exp|expires)\s*[:\-]?\s*(\d{1,2}[\-/]\d{1,2}[\-/]\d{2,4})", re.IGNORECASE)
_SEX_RE = re.compile(r"\bsex\s*[:\-]?\s*([MF])\b", re.IGNORECASE)
_EYES_RE = re.compile(r"\beyes\s*[:\-]?\s*([A-Z]{2,3})\b", re.IGNORECASE)
_HEIGHT_RE = re.compile(r"\bht\s*[:\-]?\s*(\d{1,2}[\-'′]\s?\d{1,2}\"?)", re.IGNORECASE)
_CLASS_RE = re.compile(r"\bclass\s*[:\-]?\s*([A-Z0-9]{1,3})\b", re.IGNORECASE)

# Social Security card: always exactly 9 digits, printed as XXX-XX-XXXX (OCR
# sometimes misreads the dash as a space).
_SSN_CARD_RE = re.compile(r"\b(\d{3}[\s\-]?\d{2}[\s\-]?\d{4})\b")
_SSN_NAME_LINE_RE = re.compile(r"has\s+been\s+established\s+for", re.IGNORECASE)

_USD_RE = re.compile(r"\$\s?([\d,]+(?:\.\d{2})?)")
_PAY_DATE_RE = re.compile(r"\bpay\s*date\s*[:\-]?\s*(\d{1,2}[\-/]\d{1,2}[\-/]\d{2,4})", re.IGNORECASE)
_EMPLOYEE_NAME_LINE_RE = re.compile(r"employee\s*name", re.IGNORECASE)

# The pay stub's YTD/totals row is a table: a header line naming each column
# ("YTD GROSS", "YTD DEDUCTION", "YTD NET PAY", "TOTAL", "DEDUCTION", "NET
# PAY") followed by a separate line with that many dollar amounts in the same
# order — there's no label:value pairing on one line like the other
# extractors rely on, so these columns are matched by POSITION (see
# extract_pay_stub_fields): find the header line, then read the Nth dollar
# amount off the very next line. This regex requires all 6 column names to
# appear in that fixed order (this template's only known layout), and its
# negative lookbehind on the final "net pay" stops "YTD NET PAY" earlier in
# the same line from being mistaken for the "NET PAY" column.
_PAY_STUB_TOTALS_HEADER_RE = re.compile(
    r"ytd\s*gross.*?ytd\s*deduction.*?ytd\s*net\s*pay.*?total.*?deduction.*?(?<!ytd )net\s*pay",
    re.IGNORECASE,
)

# W-2: EIN is IRS-standard XX-XXXXXXX; SSN reuses the same 9-digit shape as
# the SSN card (see _SSN_CARD_RE above). Box labels matched individually
# since a W-2's OCR text has no reliable single delimiter between a box's
# label and its dollar value across every layout variant.
_EIN_RE = re.compile(r"\b(\d{2}-\d{7})\b")
_TAX_YEAR_RE = re.compile(r"\b(20\d{2})\b")
_BOX1_RE = re.compile(r"wages,?\s*tips,?\s*other\s*comp\w*\s*\.?\s*\$?\s*([\d,]+(?:\.\d{2})?)", re.IGNORECASE)
_BOX2_RE = re.compile(r"federal\s*income\s*tax\s*withheld\s*\$?\s*([\d,]+(?:\.\d{2})?)", re.IGNORECASE)
_BOX3_RE = re.compile(r"social\s*security\s*wages\s*\$?\s*([\d,]+(?:\.\d{2})?)", re.IGNORECASE)
_BOX5_RE = re.compile(r"medicare\s*wages\s*(?:and\s*tips)?\s*\$?\s*([\d,]+(?:\.\d{2})?)", re.IGNORECASE)
_W2_EMPLOYER_NAME_LINE_RE = re.compile(r"employer'?s\s*name", re.IGNORECASE)
_W2_EMPLOYEE_NAME_LINE_RE = re.compile(r"employee'?s\s*name", re.IGNORECASE)

# Form 1040: filing status has no printed value to extract (it's a checkbox
# on the paper form, not OCR-readable text), so only the line-item labels
# that DO print a value alongside them are extracted.
_1040_NAME_LINE_RE = re.compile(r"your\s*(?:first\s*name\s*and\s*)?name\b", re.IGNORECASE)
_1040_WAGES_RE = re.compile(r"wages[\s/,]*salaries\s*\$?\s*([\d,]+(?:\.\d{2})?)", re.IGNORECASE)
_1040_AGI_RE = re.compile(r"adjusted\s*gross\s*income\s*\$?\s*([\d,]+(?:\.\d{2})?)", re.IGNORECASE)

# US bank statement: ABA routing number is always exactly 9 digits (see
# ROUTING_NUMBER_RE in agents/documents.py, which requires the "routing"
# label — this reuses the same shape for extraction once a document is
# already confirmed to be a bank statement).
_ROUTING_NUMBER_RE = re.compile(r"\brouting\s*(?:number|no\.?|#)?\s*[:\-]?\s*(\d{9})\b", re.IGNORECASE)
_ACCOUNT_NUMBER_RE = re.compile(r"\baccount\s*(?:number|no\.?|#)?\s*[:\-]?\s*(\d{4,17})\b", re.IGNORECASE)
_STATEMENT_PERIOD_RE = re.compile(
    r"statement\s*period\s*[:\-]?\s*(\d{1,2}[\-/]\d{1,2}[\-/]\d{2,4}\s*(?:-|to|through)\s*\d{1,2}[\-/]\d{1,2}[\-/]\d{2,4})",
    re.IGNORECASE,
)
_BEGINNING_BALANCE_RE = re.compile(r"beginning\s*balance\s*\$?\s*([\d,]+(?:\.\d{2})?)", re.IGNORECASE)
_ENDING_BALANCE_RE = re.compile(r"ending\s*balance\s*\$?\s*([\d,]+(?:\.\d{2})?)", re.IGNORECASE)

# Purchase agreement/sales contract: parties and the effective date are
# introduced by fixed phrases ("is made and effective", "BETWEEN:", "AND:");
# the total price is the last dollar amount in the goods/pricing table,
# which conventionally ends with a "Total" row.
_EFFECTIVE_DATE_RE = re.compile(r"(?:is\s*made\s*and\s*effective|effective\s*date)\s*[:\-]?\s*(\d{1,2}[\-/]\d{1,2}[\-/]\d{2,4})", re.IGNORECASE)
# Party names are followed by a comma introducing their address/role clause
# (e.g. "BETWEEN: Acme Supply Co, with an address of..."), so the name is
# only the text up to that first comma, not the whole clause.
_SELLER_LINE_RE = re.compile(r"^between\s*[:\-]?\s*([^,]+)", re.IGNORECASE)
_BUYER_LINE_RE = re.compile(r"^and\s*[:\-]?\s*([^,]+)", re.IGNORECASE)
_TOTAL_PRICE_LINE_RE = re.compile(r"^total\b", re.IGNORECASE)

# Down payment proof: reference number and account holder name have their
# own labels; total available funds and the designated down-payment amount
# each sit on a row of their own table (see extract_down_payment_proof_fields
# for how the row is picked out — "TOTAL AVAILABLE FUNDS" ends the account
# summary table, "Designated Amount" heads the down-payment detail table).
_REFERENCE_NUMBER_RE = re.compile(r"reference\s*number\s*[:\-]?\s*([A-Z0-9\-]+)", re.IGNORECASE)
_ACCOUNT_HOLDER_NAME_RE = re.compile(r"account\s*name\s*[:\-]?\s*(.+)", re.IGNORECASE)
_TOTAL_AVAILABLE_FUNDS_LINE_RE = re.compile(r"total\s*available\s*funds", re.IGNORECASE)
_DESIGNATED_AMOUNT_HEADER_RE = re.compile(r"designated\s*amount", re.IGNORECASE)

# Homeowners insurance: policy number sits in its own labeled box; coverage
# lines are prefixed with a letter code ("(A) Dwelling", "(E) Liability")
# that's specific enough to anchor on directly, unlike the pay stub's
# same-named columns.
_POLICY_NUMBER_RE = re.compile(r"policy\s*number\s*[:\-]?\s*([A-Z0-9]+)", re.IGNORECASE)
_POLICY_HOLDER_LINE_RE = re.compile(r"policy\s*holder|named\s*insured", re.IGNORECASE)
_PROPERTY_ADDRESS_LINE_RE = re.compile(r"property\s*address", re.IGNORECASE)
_DWELLING_COVERAGE_RE = re.compile(r"\(a\)\s*dwelling\s*\$?\s*([\d,]+(?:\.\d{2})?)", re.IGNORECASE)
_LIABILITY_COVERAGE_RE = re.compile(r"\(e\)\s*liability\s*\$?\s*([\d,]+(?:\.\d{2})?)", re.IGNORECASE)
_DEDUCTIBLE_RE = re.compile(r"deductible\s*[:=]?\s*\$?\s*([\d,]+(?:\.\d{2})?)", re.IGNORECASE)
_POLICY_PREMIUM_RE = re.compile(r"policy\s*premium\s*[:=]?\s*\$?\s*([\d,]+(?:\.\d{2})?)", re.IGNORECASE)

# Property appraisal: property address is a bulleted "Property Address:"
# line; the final appraised value is the last row of the appraisal summary
# table ("Final Appraisal Value"), which may be prefixed with a footnote
# marker (e.g. "**$450,000.00") that the money regex's fallback handles.
_APPRAISAL_ADDRESS_RE = re.compile(r"property\s*address\s*[:\-]?\s*(.+)", re.IGNORECASE)
_FINAL_APPRAISED_VALUE_LINE_RE = re.compile(r"final\s*appraisal\s*value", re.IGNORECASE)
_APPRAISAL_DATE_RE = re.compile(r"^date\s*[:\-]?\s*(.+)", re.IGNORECASE)


def _first_money(text: str) -> str | None:
    match = MONEY_RE.search(text or "")
    return match.group(1).replace(",", "") if match else None


def extract_gold_fields(text: str) -> dict:
    fields = {}
    grams = GRAMS_RE.search(text or "")
    if grams:
        fields["gold_weight_grams"] = grams.group(1)
    carat = CARAT_RE.search(text or "")
    if carat:
        fields["gold_purity_carats"] = f"{carat.group(1)}K"
    return fields


def extract_home_fields(text: str) -> dict:
    fields = {}
    price = _first_money(text)
    if price:
        fields["property_value"] = price
    return fields


def extract_personal_fields(text: str) -> dict:
    fields = {}
    income = _first_money(text)
    if income:
        fields["monthly_income"] = income
    return fields


def extract_education_fields(text: str) -> dict:
    # College/course names have no reliable fixed format to regex out safely,
    # left for a human/bank reviewer to confirm from the uploaded documents.
    return {}


def extract_vehicle_fields(text: str, extra_texts: list[str] | None = None) -> dict:
    # No vehicle document type is currently defined in require.json — this
    # returns no fields until a new vehicle document's extraction logic is
    # written (see CATEGORY_FIELD_EXTRACTORS below).
    return {}


def extract_photo_id_fields(text: str) -> dict:
    """
    Pulls structured fields off a government-issued photo ID (driver's
    license or state ID): ID number, date of birth, sex, eye color, height,
    license class, issue/expiration dates, issuing state. These cards pack
    several short label:value pairs onto the same printed line (e.g. "SEX F
    EYES BR HT 5-09"), so each field is matched by its own label-anchored
    regex across the whole text rather than a per-line scan, which would
    otherwise capture an entire multi-field line as one value.
    """
    text = text or ""
    fields: dict = {}

    dob_match = _DOB_RE.search(text)
    if dob_match:
        fields["date_of_birth"] = dob_match.group(1)

    issued_match = _ISSUED_RE.search(text)
    if issued_match:
        fields["issue_date"] = issued_match.group(1)

    expires_match = _EXPIRES_RE.search(text)
    if expires_match:
        fields["expiration_date"] = expires_match.group(1)

    sex_match = _SEX_RE.search(text)
    if sex_match:
        fields["sex"] = sex_match.group(1).upper()

    eyes_match = _EYES_RE.search(text)
    if eyes_match:
        fields["eye_color"] = eyes_match.group(1).upper()

    height_match = _HEIGHT_RE.search(text)
    if height_match:
        fields["height"] = height_match.group(1)

    class_match = _CLASS_RE.search(text)
    if class_match:
        fields["license_class"] = class_match.group(1).upper()

    id_match = _ID_NUMBER_RE.search(text)
    if id_match:
        fields["id_number"] = re.sub(r"\s+", " ", id_match.group(1)).strip()

    text_lower = text.lower()
    for state in US_STATES:
        if state in text_lower:
            fields["issuing_state"] = state.title()
            break

    return fields


def extract_ssn_card_fields(text: str) -> dict:
    """
    Pulls structured fields off a Social Security card: the 9-digit SSN
    (normalized to XXX-XX-XXXX) and the cardholder's name. The name has no
    label of its own — it's the line immediately following "HAS BEEN
    ESTABLISHED FOR" — so it's found by line position relative to that phrase
    rather than a label-anchored regex like the other extractors use.
    """
    text = text or ""
    fields: dict = {}

    ssn_match = _SSN_CARD_RE.search(text)
    if ssn_match:
        digits = re.sub(r"\D", "", ssn_match.group(1))
        if len(digits) == 9:
            fields["ssn_number"] = f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for i, line in enumerate(lines):
        if _SSN_NAME_LINE_RE.search(line):
            # The name is usually the remainder of this same line after the
            # phrase, but cards that wrap the phrase onto its own line print
            # the name on the next line instead — check both.
            remainder = _SSN_NAME_LINE_RE.sub("", line).strip(" :")
            if remainder:
                fields["full_name"] = remainder
            elif i + 1 < len(lines):
                fields["full_name"] = lines[i + 1]
            break

    return fields


def extract_pay_stub_fields(text: str) -> dict:
    """
    Pulls core income fields off a US pay stub/earnings statement: employee
    name, pay date, current (this-period) gross pay, YTD gross, YTD net pay,
    and net pay. Deduction line items (FICA/federal/state tax) are
    intentionally not extracted — not needed for a loan income check, and a
    pay stub's deduction table has no consistent OCR-friendly layout across
    employers to anchor on reliably.
    """
    text = text or ""
    fields: dict = {}

    pay_date_match = _PAY_DATE_RE.search(text)
    if pay_date_match:
        fields["pay_date"] = pay_date_match.group(1)

    # The YTD/totals row is a table: one line names each column ("YTD GROSS
    # YTD DEDUCTION YTD NET PAY TOTAL DEDUCTION NET PAY"), the next line has
    # that many dollar amounts in the same order — no label:value pairing on
    # a single line to regex out directly, so match by column position
    # instead (see _PAY_STUB_TOTALS_HEADER_RE above).
    lines_raw = text.splitlines()
    for i, line in enumerate(lines_raw):
        if not _PAY_STUB_TOTALS_HEADER_RE.search(line):
            continue
        if i + 1 >= len(lines_raw):
            break
        amounts = _USD_RE.findall(lines_raw[i + 1])
        if len(amounts) < 6:
            break
        # Column order: YTD GROSS(0), YTD DEDUCTION(1), YTD NET PAY(2), TOTAL(3), DEDUCTION(4), NET PAY(5).
        fields["ytd_gross"] = amounts[0].replace(",", "")
        fields["ytd_net_pay"] = amounts[2].replace(",", "")
        fields["net_pay"] = amounts[5].replace(",", "")
        break

    # "Current pay" has no label of its own on the sample layout — it's the
    # right-most dollar amount on the "REGULAR" earnings row. Falls back to
    # the first dollar amount found anywhere if that row isn't present, since
    # stub layouts vary by payroll provider.
    regular_line = next((line for line in text.splitlines() if "regular" in line.lower()), None)
    amounts_in_line = _USD_RE.findall(regular_line) if regular_line else []
    if amounts_in_line:
        fields["current_gross_pay"] = amounts_in_line[-1].replace(",", "")

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for i, line in enumerate(lines):
        if _EMPLOYEE_NAME_LINE_RE.search(line) and i + 1 < len(lines):
            fields["employee_name"] = lines[i + 1]
            break

    return fields


def extract_w2_fields(text: str) -> dict:
    """
    Pulls core income/identity fields off IRS Form W-2: employee SSN,
    employer EIN, tax year, employer/employee name, and the wage/withholding
    boxes lenders check most (box 1 wages, box 2 federal tax withheld, box 3
    Social Security wages, box 5 Medicare wages). Less common boxes (7-14,
    12a-d codes, state/local tax lines) are intentionally not extracted —
    rarely needed for a loan decision, and the numbered-box grid has no
    single consistent OCR text order across scanned/photographed copies to
    anchor further boxes on reliably.
    """
    text = text or ""
    fields: dict = {}

    ssn_match = _SSN_CARD_RE.search(text)
    if ssn_match:
        digits = re.sub(r"\D", "", ssn_match.group(1))
        if len(digits) == 9:
            fields["employee_ssn"] = f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"

    ein_match = _EIN_RE.search(text)
    if ein_match:
        fields["employer_ein"] = ein_match.group(1)

    year_match = _TAX_YEAR_RE.search(text)
    if year_match:
        fields["tax_year"] = year_match.group(1)

    box1_match = _BOX1_RE.search(text)
    if box1_match:
        fields["wages_tips_box1"] = box1_match.group(1).replace(",", "")

    box2_match = _BOX2_RE.search(text)
    if box2_match:
        fields["federal_tax_withheld_box2"] = box2_match.group(1).replace(",", "")

    box3_match = _BOX3_RE.search(text)
    if box3_match:
        fields["social_security_wages_box3"] = box3_match.group(1).replace(",", "")

    box5_match = _BOX5_RE.search(text)
    if box5_match:
        fields["medicare_wages_box5"] = box5_match.group(1).replace(",", "")

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for i, line in enumerate(lines):
        if _W2_EMPLOYER_NAME_LINE_RE.search(line) and i + 1 < len(lines):
            fields["employer_name"] = lines[i + 1]
        elif _W2_EMPLOYEE_NAME_LINE_RE.search(line) and i + 1 < len(lines):
            fields["employee_name"] = lines[i + 1]

    return fields


def extract_tax_return_fields(text: str) -> dict:
    """
    Pulls core identity/income fields off IRS Form 1040: taxpayer name, SSN,
    tax year, wages/salaries, and adjusted gross income. Filing status
    (single/married/etc.) is a checkbox on the paper form with no printed
    text value next to it, so it's intentionally not extracted here — no
    OCR text reliably distinguishes which box was checked.
    """
    text = text or ""
    fields: dict = {}

    ssn_match = _SSN_CARD_RE.search(text)
    if ssn_match:
        digits = re.sub(r"\D", "", ssn_match.group(1))
        if len(digits) == 9:
            fields["ssn"] = f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"

    year_match = _TAX_YEAR_RE.search(text)
    if year_match:
        fields["tax_year"] = year_match.group(1)

    wages_match = _1040_WAGES_RE.search(text)
    if wages_match:
        fields["wages_salaries"] = wages_match.group(1).replace(",", "")

    agi_match = _1040_AGI_RE.search(text)
    if agi_match:
        fields["adjusted_gross_income"] = agi_match.group(1).replace(",", "")

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for i, line in enumerate(lines):
        if _1040_NAME_LINE_RE.search(line) and i + 1 < len(lines):
            fields["taxpayer_name"] = lines[i + 1]
            break

    return fields


def extract_us_bank_statement_fields(text: str) -> dict:
    """
    Pulls core fields off a US bank statement: account holder name, account
    number, routing number, statement period, and beginning/ending balance.
    """
    text = text or ""
    fields: dict = {}

    routing_match = _ROUTING_NUMBER_RE.search(text)
    if routing_match:
        fields["routing_number"] = routing_match.group(1)

    account_match = _ACCOUNT_NUMBER_RE.search(text)
    if account_match:
        fields["account_number"] = account_match.group(1)

    period_match = _STATEMENT_PERIOD_RE.search(text)
    if period_match:
        fields["statement_period"] = re.sub(r"\s+", " ", period_match.group(1)).strip()

    beginning_match = _BEGINNING_BALANCE_RE.search(text)
    if beginning_match:
        fields["beginning_balance"] = beginning_match.group(1).replace(",", "")

    ending_match = _ENDING_BALANCE_RE.search(text)
    if ending_match:
        fields["ending_balance"] = ending_match.group(1).replace(",", "")

    account_name_match = re.search(r"account\s*name\s*[:\-]?\s*(.+)", text, re.IGNORECASE)
    if account_name_match:
        fields["account_holder_name"] = account_name_match.group(1).strip()

    return fields


def extract_purchase_agreement_fields(text: str) -> dict:
    """
    Pulls core deal terms off a purchase agreement/sales contract: seller
    name, buyer name, effective date, and total price. Seller/buyer are
    introduced by fixed "BETWEEN:"/"AND:" lines immediately preceding each
    party's name in this template; the total price is taken from the last
    dollar amount on a line starting with "Total" (the goods/pricing table's
    closing row), since that's the only reliably distinctive anchor for it —
    a bare "$9400" elsewhere in the document could be any line item's price.
    """
    text = text or ""
    fields: dict = {}

    effective_match = _EFFECTIVE_DATE_RE.search(text)
    if effective_match:
        fields["effective_date"] = effective_match.group(1)

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        seller_match = _SELLER_LINE_RE.match(line)
        if seller_match and "seller_name" not in fields:
            fields["seller_name"] = seller_match.group(1).strip(" ,")
            continue
        buyer_match = _BUYER_LINE_RE.match(line)
        if buyer_match and "buyer_name" not in fields:
            fields["buyer_name"] = buyer_match.group(1).strip(" ,")

    for line in lines:
        if _TOTAL_PRICE_LINE_RE.match(line):
            amounts = _USD_RE.findall(line)
            if amounts:
                fields["total_price"] = amounts[-1].replace(",", "")
            break

    return fields


def extract_down_payment_proof_fields(text: str) -> dict:
    """
    Pulls core verification fields off a bank-issued down-payment funds
    letter: reference number, account holder name, total available funds,
    and the designated down-payment amount. The per-account balance
    breakdown (checking/savings) is intentionally not extracted — only the
    designated total matters for the loan decision, and account summary
    tables have no standardized layout across banks to anchor further rows
    on reliably.
    """
    text = text or ""
    fields: dict = {}

    ref_match = _REFERENCE_NUMBER_RE.search(text)
    if ref_match:
        fields["reference_number"] = ref_match.group(1).strip()

    name_match = _ACCOUNT_HOLDER_NAME_RE.search(text)
    if name_match:
        fields["account_holder_name"] = name_match.group(1).strip()

    # "TOTAL AVAILABLE FUNDS" is the account summary table's closing row —
    # its dollar amount is the last one on that same line.
    for line in text.splitlines():
        if _TOTAL_AVAILABLE_FUNDS_LINE_RE.search(line):
            amounts = _USD_RE.findall(line)
            if amounts:
                fields["total_available_funds"] = amounts[-1].replace(",", "")
            break

    # "Designated Amount" heads the down-payment detail table; its value is
    # a dollar figure on the line(s) immediately following the header.
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if _DESIGNATED_AMOUNT_HEADER_RE.search(line):
            for value_line in lines[i + 1 : i + 3]:
                amounts = _USD_RE.findall(value_line)
                if amounts:
                    fields["designated_down_payment_amount"] = amounts[0].replace(",", "")
                    break
            break

    return fields


def extract_homeowners_insurance_fields(text: str) -> dict:
    """
    Pulls core policy fields off a homeowners insurance declarations page:
    policy number, policy holder name, property address, dwelling coverage
    (Section 1(A)), liability coverage (Section 2(E)), deductible, and
    policy premium. The other coverage lines (Other Structures, Personal
    Property, Loss of Use, Medical) are intentionally not extracted — a
    lender checks dwelling coverage against the loan amount and liability
    coverage for general risk, not the smaller supplementary limits.
    """
    text = text or ""
    fields: dict = {}

    policy_match = _POLICY_NUMBER_RE.search(text)
    if policy_match:
        fields["policy_number"] = policy_match.group(1).strip()

    dwelling_match = _DWELLING_COVERAGE_RE.search(text)
    if dwelling_match:
        fields["dwelling_coverage"] = dwelling_match.group(1).replace(",", "")

    liability_match = _LIABILITY_COVERAGE_RE.search(text)
    if liability_match:
        fields["liability_coverage"] = liability_match.group(1).replace(",", "")

    deductible_match = _DEDUCTIBLE_RE.search(text)
    if deductible_match:
        fields["deductible"] = deductible_match.group(1).replace(",", "")

    premium_match = _POLICY_PREMIUM_RE.search(text)
    if premium_match:
        fields["policy_premium"] = premium_match.group(1).replace(",", "")

    # "POLICY HOLDER" and "NAMED INSURED" print as two consecutive label
    # lines above the actual name (both match _POLICY_HOLDER_LINE_RE), so the
    # name is the first line AFTER the run of matching label lines, not
    # simply the very next line.
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for i, line in enumerate(lines):
        if _POLICY_HOLDER_LINE_RE.search(line) and "policy_holder_name" not in fields:
            j = i + 1
            while j < len(lines) and _POLICY_HOLDER_LINE_RE.search(lines[j]):
                j += 1
            if j < len(lines):
                fields["policy_holder_name"] = lines[j]
        elif _PROPERTY_ADDRESS_LINE_RE.search(line) and i + 1 < len(lines) and "property_address" not in fields:
            fields["property_address"] = lines[i + 1]

    return fields


def extract_property_appraisal_fields(text: str) -> dict:
    """
    Pulls core valuation fields off a property appraisal report: property
    address, final appraised value, appraisal date, and appraiser name. The
    per-methodology breakdown (Comparable Sales/Cost/Income Approach values)
    is intentionally not extracted — only the final reconciled value matters
    for the loan decision.
    """
    text = text or ""
    fields: dict = {}

    address_match = _APPRAISAL_ADDRESS_RE.search(text)
    if address_match:
        fields["property_address"] = address_match.group(1).strip(" :-")

    # "Final Appraisal Value" is the summary table's closing row — its
    # dollar amount is the last one on that same line, tolerant of a
    # footnote marker prefix (e.g. "**$450,000.00").
    for line in text.splitlines():
        if _FINAL_APPRAISED_VALUE_LINE_RE.search(line):
            amounts = _USD_RE.findall(line)
            if amounts:
                fields["final_appraised_value"] = amounts[-1].replace(",", "")
            break

    for line in text.splitlines():
        date_match = _APPRAISAL_DATE_RE.match(line.strip())
        if date_match:
            fields["appraisal_date"] = date_match.group(1).strip()
            break

    # The appraiser's typed name follows their signature, immediately before
    # their credential line ("Certified Residential Appraiser").
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for i, line in enumerate(lines):
        if "certified residential appraiser" in line.lower() and i > 0:
            fields["appraiser_name"] = lines[i - 1]
            break

    return fields


DOCUMENT_FIELD_EXTRACTORS = {
    "Government-issued Photo ID": extract_photo_id_fields,
    "Social Security Number (SSN)": extract_ssn_card_fields,
    "Recent Pay Stubs": extract_pay_stub_fields,
    "W-2 Forms": extract_w2_fields,
    "Federal Tax Returns": extract_tax_return_fields,
    "Bank Statements": extract_us_bank_statement_fields,
    "Purchase Agreement / Sales Contract": extract_purchase_agreement_fields,
    "Proof of Down Payment Funds": extract_down_payment_proof_fields,
    "Homeowners Insurance Declaration Page": extract_homeowners_insurance_fields,
    "Property Appraisal Report": extract_property_appraisal_fields,
}


CATEGORY_FIELD_EXTRACTORS = {
    "Gold Loan": extract_gold_fields,
    "Vehicle Loan": extract_vehicle_fields,
    "Home Loan": extract_home_fields,
    "Personal Loan": extract_personal_fields,
    "Education Loan": extract_education_fields,
}


def extract_fields_from_text(
    category: str, text: str, label: str | None = None, extra_texts: list[str] | None = None
) -> dict:
    """
    Best-effort structured field extraction from a single document's OCR/PDF text.
    Returns only the fields this piece of text yielded a confident match for —
    callers should merge results across all of an applicant's documents.

    Two independent extractor lookups run and merge: DOCUMENT_FIELD_EXTRACTORS,
    keyed by the document's matched label (e.g. "Government-issued Photo ID" —
    a general document that applies across every loan category, so it can't be
    dispatched by category); and CATEGORY_FIELD_EXTRACTORS, keyed by loan
    category (e.g. "Gold Loan" — fields specific to that loan type). A single
    attachment can match both (e.g. a Photo ID submitted alongside a Gold Loan
    application still only triggers the photo-ID extractor, since its label
    doesn't match any category-specific document name).

    extra_texts, when provided, are additional OCR readings of the SAME
    document (e.g. alternate page-segmentation passes over one image — see
    agents.documents.extract_image_text_candidates); currently unused now that
    the vehicle/dealer-quotation extractor has been removed, kept in the
    signature so callers (document_processing.py) don't need to change when a
    new document type's extractor needs it.
    """
    fields = {}

    document_extractor = DOCUMENT_FIELD_EXTRACTORS.get(label or "")
    if document_extractor:
        fields.update(document_extractor(text))

    category_extractor = CATEGORY_FIELD_EXTRACTORS.get(category)
    if category_extractor:
        result = category_extractor(text, extra_texts) if category == "Vehicle Loan" else category_extractor(text)
        fields.update(result)

    return fields
