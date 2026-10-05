"""IBAN helpers (ISO 13616 mod-97) and BIC format check."""
import re
from .refdata import IBAN_LENGTHS

BIC_RE = re.compile(r"^[A-Z0-9]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$")


def iban_mod97_ok(iban: str) -> bool:
    s = iban.replace(" ", "").upper()
    if not re.match(r"^[A-Z]{2}\d{2}[A-Z0-9]+$", s):
        return False
    r = s[4:] + s[:4]
    num = "".join(str(int(c, 36)) for c in r)
    return int(num) % 97 == 1


def iban_check_digits(country: str, bban: str) -> str:
    r = bban + country + "00"
    num = "".join(str(int(c, 36)) for c in r)
    return f"{98 - int(num) % 97:02d}"


def make_iban(country: str, bban: str) -> str:
    return country + iban_check_digits(country, bban) + bban


def iban_length_ok(iban: str):
    """True/False, or None when the country has no registered length in our table."""
    exp = IBAN_LENGTHS.get(iban[:2])
    return None if exp is None else len(iban) == exp
