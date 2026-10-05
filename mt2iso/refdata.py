"""Reference data: ISO 3166 countries, ISO 4217 currencies, IBAN lengths, small gazetteer."""

COUNTRIES = set("""AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV BW BY BZ
CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK FM FO FR
GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP
KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ
NA NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW
SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ
UA UG UM US UY UZ VA VC VE VG VI VN VU WF WS YE YT ZA ZM ZW""".split())

# ISO 4217 subset: code -> minor units
CURRENCIES = {
    "USD": 2, "EUR": 2, "GBP": 2, "AED": 2, "SAR": 2, "PKR": 2, "CNY": 2, "JPY": 0, "CHF": 2, "CAD": 2,
    "AUD": 2, "SGD": 2, "HKD": 2, "KWD": 3, "BHD": 3, "OMR": 3, "QAR": 2, "INR": 2, "TRY": 2, "SEK": 2,
    "NOK": 2, "DKK": 2, "NZD": 2, "ZAR": 2, "MYR": 2, "THB": 2, "KRW": 0, "IDR": 2, "EGP": 2, "BDT": 2,
}

# IBAN total length per country (registry values for the countries used by this toolkit)
IBAN_LENGTHS = {
    "AE": 23, "AT": 20, "BE": 16, "BG": 22, "BH": 22, "CH": 21, "CY": 28, "CZ": 24, "DE": 22, "DK": 18,
    "EE": 20, "ES": 24, "FI": 18, "FR": 27, "GB": 22, "GR": 27, "HR": 21, "HU": 28, "IE": 22, "IS": 26,
    "IT": 27, "JO": 30, "KW": 30, "LB": 28, "LI": 21, "LT": 20, "LU": 20, "LV": 21, "MT": 31, "NL": 18,
    "NO": 15, "PK": 24, "PL": 28, "PT": 25, "QA": 29, "RO": 24, "SA": 24, "SE": 24, "SI": 19, "SK": 24,
    "TR": 26,
}

COUNTRY_NAMES = {
    "PAKISTAN": "PK", "UNITED ARAB EMIRATES": "AE", "UAE": "AE", "UNITED KINGDOM": "GB", "UK": "GB",
    "GREAT BRITAIN": "GB", "UNITED STATES": "US", "USA": "US", "UNITED STATES OF AMERICA": "US",
    "SAUDI ARABIA": "SA", "GERMANY": "DE", "CHINA": "CN", "SINGAPORE": "SG", "FRANCE": "FR",
    "NETHERLANDS": "NL", "TURKEY": "TR", "CANADA": "CA", "QATAR": "QA", "KUWAIT": "KW", "OMAN": "OM",
    "BAHRAIN": "BH", "JAPAN": "JP", "HONG KONG": "HK", "AUSTRALIA": "AU",
}

# Tiny gazetteer: town -> country. Used ONLY to infer a missing country (flagged as INFERENCE).
GAZETTEER = {
    "KARACHI": "PK", "LAHORE": "PK", "ISLAMABAD": "PK", "RAWALPINDI": "PK", "FAISALABAD": "PK",
    "PESHAWAR": "PK", "MULTAN": "PK", "QUETTA": "PK", "SIALKOT": "PK",
    "DUBAI": "AE", "ABU DHABI": "AE", "SHARJAH": "AE",
    "RIYADH": "SA", "JEDDAH": "SA", "DAMMAM": "SA",
    "LONDON": "GB", "MANCHESTER": "GB", "BIRMINGHAM": "GB",
    "NEW YORK": "US", "HOUSTON": "US", "CHICAGO": "US",
    "FRANKFURT": "DE", "BERLIN": "DE", "MUNICH": "DE", "HAMBURG": "DE",
    "SHANGHAI": "CN", "SHENZHEN": "CN", "GUANGZHOU": "CN", "BEIJING": "CN",
    "SINGAPORE": "SG", "PARIS": "FR", "TORONTO": "CA", "DOHA": "QA",
}
