"""Generates believable, company-specific decoy contents.

Given a company name + city, this builds a fake employee roster with:
  - emails on the company's own domain
  - phone numbers using the REAL local area code for that city
so the stolen "data" looks legit to an attacker. Everything is fabricated.
"""

import random
import re

# City -> local area codes (from us_city_area_codes.txt research).
AREA_CODES = {
    "New York, NY": ["212", "646", "718", "917"],
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

# Sorted list of city names for the dropdown on the dashboard.
CITY_LIST = sorted(AREA_CODES.keys())

_FIRST = ["Sarah", "Mike", "Priya", "James", "Linda", "David", "Emma",
          "Carlos", "Aisha", "Tom", "Nina", "Raj", "Grace", "Leo", "Maria"]
_LAST = ["Chen", "Torres", "Patel", "Okoro", "Vasquez", "Nguyen", "Smith",
         "Kim", "Johnson", "Rossi", "Ali", "Brooks", "Diaz", "Webb", "Cole"]
_ROLES = ["Office Manager", "Owner", "Lead Technician", "Receptionist",
          "Billing Lead", "Accountant", "Operations", "Sales Lead"]


def company_domain(company):
    """'Bright Smile Dental' -> 'brightsmiledental.com'."""
    slug = re.sub(r"[^a-z0-9]", "", (company or "company").lower())
    return (slug or "company") + ".com"


def local_phone(location):
    """A realistic phone number using the area code for the given city."""
    codes = AREA_CODES.get(location, ["555"])
    area = random.choice(codes)
    return f"({area}) {random.randint(200,999)}-{random.randint(1000,9999)}"


def employee_rows(company, location, count=6):
    """Header row + fabricated employees with local phones and company emails."""
    domain = company_domain(company)
    rows = [["Employee", "Role", "Annual Salary", "Email", "Phone", "Bank Account"]]
    names = random.sample([(f, l) for f in _FIRST for l in _LAST], count)
    roles = random.sample(_ROLES, min(count, len(_ROLES)))
    for i, (first, last) in enumerate(names):
        role = roles[i % len(roles)]
        email = f"{first[0].lower()}.{last.lower()}@{domain}"
        rows.append([
            f"{first} {last}",
            role,
            random.randint(42, 155) * 1000,
            email,
            local_phone(location),
            str(random.randint(1000000000, 9999999999)),
        ])
    return rows
