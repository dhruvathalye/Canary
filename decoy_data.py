"""Generates believable, company-specific decoy contents.

Given a company name + city, this builds fake files (payroll, customer list,
passwords, bank statements, tax returns) with:
  - emails on the company's own domain
  - phone numbers using the REAL local area code for that city
so the stolen "data" looks legit to an attacker. Everything is fabricated.
"""

import io
import random
import re

# City -> local area codes (from us_city_area_codes.txt research).
AREA_CODES = {
    "New York, NY": ["212", "646", "718", "917"],
    "Tel Aviv, Israel": ["03"],
    "Boston, MA": ["617", "857"],
    "Philadelphia, PA": ["215", "267"],
    "Washington, DC": ["202"],
    "Baltimore, MD": ["410", "443"],
    "Providence, RI": ["401"],
    "Hartford, CT": ["860", "203"],
    "Buffalo, NY": ["716", "585"],
    "Pittsburgh, PA": ["412"],
    "Miami, FL": ["305", "786", "954"],
    "Atlanta, GA": ["404", "770", "678"],
    "Charlotte, NC": ["704", "980"],
    "Nashville, TN": ["615", "931"],
    "New Orleans, LA": ["504", "985"],
    "Memphis, TN": ["901", "662"],
    "Richmond, VA": ["804"],
    "Jacksonville, FL": ["904"],
    "Raleigh, NC": ["919", "984"],
    "Austin, TX": ["512", "737"],
    "Chicago, IL": ["312", "773", "708", "630"],
    "Detroit, MI": ["313", "586"],
    "Minneapolis, MN": ["612", "651"],
    "St. Louis, MO": ["314", "636"],
    "Cleveland, OH": ["216", "330"],
    "Cincinnati, OH": ["513", "937"],
    "Kansas City, MO": ["816", "913"],
    "Milwaukee, WI": ["414", "262"],
    "Indianapolis, IN": ["317", "765"],
    "Columbus, OH": ["614", "740"],
    "Dallas, TX": ["214", "469", "972"],
    "Houston, TX": ["713", "281", "832"],
    "Phoenix, AZ": ["602", "480", "623"],
    "Denver, CO": ["303", "720", "719"],
    "El Paso, TX": ["915"],
    "Albuquerque, NM": ["505"],
    "Tucson, AZ": ["520"],
    "Las Vegas, NV": ["702", "725"],
    "Los Angeles, CA": ["213", "310", "424", "626", "818"],
    "San Francisco, CA": ["415", "628"],
    "San Diego, CA": ["619", "858"],
    "Seattle, WA": ["206", "425"],
    "Portland, OR": ["503", "971"],
    "San Jose, CA": ["408", "669"],
    "Sacramento, CA": ["916"],
    "Honolulu, HI": ["808"],
    "Anchorage, AK": ["907"],
}

CITY_LIST = sorted(AREA_CODES.keys())

_FIRST = ["Sarah", "Mike", "Priya", "James", "Linda", "David", "Emma",
          "Carlos", "Aisha", "Tom", "Nina", "Raj", "Grace", "Leo", "Maria", "Muhammad"]
_LAST = ["Chen", "Torres", "Patel", "Okoro", "Vasquez", "Nguyen", "Smith",
         "Kim", "Johnson", "Rossi", "Ali", "Brooks", "Diaz", "Webb", "Cole", "Shaik"]
_ROLES = ["Office Manager", "Owner", "Lead Technician", "Receptionist",
          "Billing Lead", "Accountant", "Operations", "Sales Lead", "Senior Director, B2B SAAS Operations"]


def company_domain(company):
    """'Bright Smile Dental' -> 'brightsmiledental.com'."""
    slug = re.sub(r"[^a-z0-9]", "", (company or "company").lower())
    return (slug or "company") + ".com"


def local_phone(location):
    """A realistic phone number using the area code for the given city."""
    codes = AREA_CODES.get(location, ["555"])
    area = random.choice(codes)
    return f"({area}) {random.randint(200,999)}-{random.randint(1000,9999)}"


# ---------------------------------------------------------------------------
# The files an attacker sees in the fake portal. Each "gen" builds its rows.
# ---------------------------------------------------------------------------

# Size is computed live from the real file (see file_size); don't hardcode it.
PORTAL_MANIFEST = [
    {"file": "Payroll_2025.xlsx",      "label": "Employee Payroll 2025",      "modified": "2025-12-02", "gen": "payroll"},
    {"file": "Customer_Database.csv",  "label": "Customer Database (export)", "modified": "2026-01-14", "gen": "customers"},
    {"file": "System_Logins.xlsx",     "label": "System Logins & Passwords",  "modified": "2025-11-20", "gen": "creds"},
    {"file": "Bank_Statements_Q4.csv", "label": "Bank Statements Q4",         "modified": "2026-01-05", "gen": "bank"},
    {"file": "Tax_Return_2024.csv",    "label": "Tax Return 2024",            "modified": "2025-04-11", "gen": "tax"},
]


def _payroll_rows(company, location):
    domain = company_domain(company)
    rows = [["Employee", "Role", "Annual Salary", "Email", "Phone", "Bank Account"]]
    names = random.sample([(f, l) for f in _FIRST for l in _LAST], 6)
    roles = random.sample(_ROLES, 6)
    for i, (first, last) in enumerate(names):
        rows.append([
            f"{first} {last}", roles[i % len(roles)],
            random.randint(42, 155) * 1000,
            f"{first[0].lower()}.{last.lower()}@{domain}",
            local_phone(location), str(random.randint(1000000000, 9999999999)),
        ])
    return rows


def _customer_rows(company, location):
    rows = [["Customer Name", "Email", "Phone", "Last Visit", "Balance Due"]]
    for _ in range(85):  # a believable customer export, not a 10-row stub
        first, last = random.choice(_FIRST), random.choice(_LAST)
        rows.append([
            f"{first} {last}",
            f"{first.lower()}{last.lower()}{random.randint(1,99)}@gmail.com",
            local_phone(location),
            f"2026-0{random.randint(1,6)}-{random.randint(10,28)}",
            f"${random.randint(0,4000)}.00",
        ])
    return rows


def _cred_rows(company, location):
    domain = company_domain(company)
    pwords = ["Summer2025!", "Admin@123", f"{company_domain(company)[:4].title()}2024",
              "Welcome1!", "P@ssw0rd2025", "Office365!"]
    return [
        ["System", "Username", "Password", "URL"],
        ["Email Admin", f"admin@{domain}", random.choice(pwords), f"mail.{domain}"],
        ["VPN", "it.admin", random.choice(pwords), f"vpn.{domain}"],
        ["Banking Portal", "finance", random.choice(pwords), "online.chasebank.com"],
        ["Server (root)", "root", random.choice(pwords), "192.168.1.10"],
        ["WiFi", "office-wifi", random.choice(pwords), "-"],
    ]


def _bank_rows(company, location):
    rows = [["Date", "Description", "Amount", "Balance"]]
    bal = 84210.55
    descs = ["Card Payment - Supplies", "Payroll Run", "Customer Deposit",
             "Utility Bill", "Insurance Premium", "Vendor Payment", "Tax Payment"]
    # A full quarter of statements, in chronological order.
    txns = sorted((f"2025-{random.randint(10,12):02d}-{random.randint(1,28):02d}"
                   for _ in range(40)))
    for day in txns:
        amt = round(random.uniform(-9000, 12000), 2)
        bal += amt
        rows.append([day, random.choice(descs), f"{amt:,.2f}", f"{bal:,.2f}"])
    return rows


def _tax_rows(company, location):
    return [
        ["Field", "Value"],
        ["Business Name", company or "Company LLC"],
        ["EIN", f"{random.randint(10,99)}-{random.randint(1000000,9999999)}"],
        ["Gross Receipts", f"${random.randint(400,1800)*1000:,}"],
        ["Net Profit", f"${random.randint(80,400)*1000:,}"],
        ["Total Tax", f"${random.randint(20,120)*1000:,}"],
    ]


_GENERATORS = {
    "payroll": _payroll_rows, "customers": _customer_rows, "creds": _cred_rows,
    "bank": _bank_rows, "tax": _tax_rows,
}


def employee_rows(company, location, count=6):
    """Kept for backwards compatibility with the plain 'file' decoy type."""
    return _payroll_rows(company, location)


# File formats the user can choose from (extension -> friendly label).
FILE_FORMATS = [
    {"ext": "xlsx", "label": "Excel spreadsheet (.xlsx)"},
    {"ext": "csv",  "label": "CSV data file (.csv)"},
    {"ext": "pdf",  "label": "PDF document (.pdf)"},
    {"ext": "docx", "label": "Word document (.docx)"},
    {"ext": "txt",  "label": "Text file (.txt)"},
]


def _as_csv(rows):
    text = "\r\n".join(",".join(str(c) for c in r) for r in rows)
    return (text.encode("utf-8"), "text/csv")


def _as_xlsx(rows):
    from openpyxl import Workbook
    wb = Workbook(); ws = wb.active; ws.title = "Sheet1"
    for r in rows:
        ws.append(r)
    buf = io.BytesIO(); wb.save(buf)
    return (buf.getvalue(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def _as_txt(rows):
    text = "\r\n".join("\t".join(str(c) for c in r) for r in rows)
    return (text.encode("utf-8"), "text/plain")


def _as_pdf(rows):
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    for i, r in enumerate(rows):
        if i == 0:
            pdf.set_font("Helvetica", "B", 10)
        line = "   ".join(str(c) for c in r)
        pdf.cell(0, 7, line[:120], new_x="LMARGIN", new_y="NEXT")
        if i == 0:
            pdf.set_font("Helvetica", size=10)
    return (bytes(pdf.output()), "application/pdf")


def _as_docx(rows):
    from docx import Document
    doc = Document()
    table = doc.add_table(rows=0, cols=len(rows[0]))
    table.style = "Light Grid Accent 1"
    for r in rows:
        cells = table.add_row().cells
        for i, c in enumerate(r):
            cells[i].text = str(c)
    buf = io.BytesIO(); doc.save(buf)
    return (buf.getvalue(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document")


_SERIALIZERS = {
    "xlsx": _as_xlsx, "csv": _as_csv, "pdf": _as_pdf, "docx": _as_docx, "txt": _as_txt,
}


def _serialize(filename, rows):
    """Turn rows into a real downloadable file based on the extension.

    Falls back to CSV text if the matching library isn't installed, so a
    download always succeeds even on a bare machine.
    """
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "csv").lower()
    fn = _SERIALIZERS.get(ext, _as_csv)
    try:
        return fn(rows)
    except Exception:
        return _as_csv(rows)


def build_download(filename, company, location):
    """Return (bytes, mimetype) for any file the attacker clicks."""
    gen = "payroll"
    for m in PORTAL_MANIFEST:
        if m["file"].lower() == (filename or "").lower():
            gen = m["gen"]; break
    rows = _GENERATORS.get(gen, _payroll_rows)(company, location)
    return _serialize(filename or "document.csv", rows)


def human_size(nbytes):
    """Format a byte count like a file manager: '742 B', '12.4 KB', '1.2 MB'."""
    if nbytes < 1024:
        return f"{nbytes} B"
    if nbytes < 1024 * 1024:
        return f"{nbytes / 1024:.1f} KB"
    return f"{nbytes / (1024 * 1024):.1f} MB"


def file_size(filename, company, location):
    """Real on-disk size of the file the portal will hand out (for the listing)."""
    try:
        data, _ = build_download(filename, company, location)
        return human_size(len(data))
    except Exception:
        return "--"
