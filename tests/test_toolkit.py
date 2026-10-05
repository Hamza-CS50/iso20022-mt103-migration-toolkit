import os, sys, unittest, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lxml import etree
from mt2iso.ibanutil import iban_mod97_ok, make_iban, iban_length_ok, BIC_RE
from mt2iso.addrparse import parse_address
from mt2iso.mt103 import parse_mt103
from mt2iso.mapper import convert, NS
from mt2iso.pipeline import process_text, run
from mt2iso.dataset import generate

SAMPLE = """{1:F01LNDNGB2LAXXX0000000000}{2:I103KRDBPKKAAXXXN}{3:{108:REF1}{121:3f2a6c1e-8d4b-4c3a-9a55-0d6f1b2c3d4e}}{4:
:20:TRN000000001
:23B:CRED
:32A:261005USD1250,00
:50K:/123456789012
JOHN SMITH
123 MAIN STREET
NEW YORK NY 10001 US
:59:/PK36SCBL0000001123456702
AYESHA KHAN
HOUSE 12 STREET 5 DHA PHASE 6
KARACHI PK
:70:/INV/2026-0042
PAYMENT FOR GOODS
:71A:SHA
-}"""


def rules(text):
    _, conv, f, rej = process_text("T", text)
    return {x.rule_id for x in f}, conv, rej


class IbanBic(unittest.TestCase):
    def test_known_valid_ibans(self):
        self.assertTrue(iban_mod97_ok("GB82WEST12345698765432"))     # standard documentation example
        self.assertTrue(iban_mod97_ok("DE89370400440532013000"))
    def test_generated_roundtrip(self):
        self.assertTrue(iban_mod97_ok(make_iban("PK", "ABCD0123456789012345")))
        self.assertEqual(len(make_iban("PK", "ABCD0123456789012345")), 24)
    def test_bad_checksum(self):
        self.assertFalse(iban_mod97_ok("GB83WEST12345698765432"))
    def test_length(self):
        self.assertIs(iban_length_ok("GB82WEST12345698765432"), True)
        self.assertIs(iban_length_ok("GB82WEST123456987654321"), False)
        self.assertIsNone(iban_length_ok("US1234"))
    def test_bic(self):
        for ok in ("KRDBPKKA", "KRDBPKKAXXX"):
            self.assertTrue(BIC_RE.match(ok))
        for bad in ("KRDBPKK", "KRDBPKKAXX", "krdbpkka"):
            self.assertFalse(BIC_RE.match(bad))


class Address(unittest.TestCase):
    def test_us(self):
        r = parse_address(["123 MAIN STREET", "NEW YORK NY 10001 US"])
        self.assertEqual((r.town, r.ctry, r.pstcd, r.subdiv, r.street, r.bldg), ("NEW YORK", "US", "10001", "NY", "MAIN STREET", "123"))
    def test_german_postcode_first(self):
        r = parse_address(["HAUPTSTRASSE 1", "60311 FRANKFURT DE"])
        self.assertEqual((r.town, r.ctry, r.street, r.bldg), ("FRANKFURT", "DE", "HAUPTSTRASSE", "1"))
    def test_pakistani_house_style_stays_free_text(self):
        r = parse_address(["HOUSE 12 STREET 5 DHA PHASE 6", "KARACHI PK"])
        self.assertEqual((r.town, r.ctry, r.street), ("KARACHI", "PK", None))
        self.assertEqual(r.lines, ["HOUSE 12 STREET 5 DHA PHASE 6"])
    def test_country_name(self):
        self.assertEqual(parse_address(["1 ROAD", "KARACHI PAKISTAN"]).ctry, "PK")
    def test_country_inferred_from_gazetteer_is_flagged(self):
        r = parse_address(["PLOT 4", "KARACHI"])
        self.assertTrue(r.ctry_inferred)
    def test_unknown_town_gives_no_structure(self):
        r = parse_address(["SOME ROAD", "WAZIRABAD"])
        self.assertIsNone(r.town); self.assertIsNone(r.ctry)


class Mapping(unittest.TestCase):
    def test_sample_converts_and_validates(self):
        r, conv, rej = rules(SAMPLE)
        self.assertFalse(rej)
        self.assertNotIn("XSD_001", r)
        self.assertFalse({x for x in r if x.startswith(("BR_IBAN", "BR_ADDR_TWN", "SX_"))})
    def test_values(self):
        _, conv, _ = rules(SAMPLE)
        x = etree.fromstring(conv.xml); ns = {"p": NS}
        self.assertEqual(x.xpath("//p:IntrBkSttlmAmt/@Ccy", namespaces=ns), ["USD"])
        self.assertEqual(x.xpath("//p:IntrBkSttlmAmt/text()", namespaces=ns), ["1250.00"])
        self.assertEqual(x.xpath("//p:ChrgBr/text()", namespaces=ns), ["SHAR"])
        self.assertEqual(x.xpath("//p:RfrdDocInf/p:Nb/text()", namespaces=ns), ["2026-0042"])
        self.assertEqual(x.xpath("//p:UETR/text()", namespaces=ns), ["3f2a6c1e-8d4b-4c3a-9a55-0d6f1b2c3d4e"])
    def test_charge_code_mapping(self):
        for mt, mx in (("OUR", "DEBT"), ("BEN", "CRED"), ("SHA", "SHAR")):
            text = SAMPLE.replace(":71A:SHA", f":71A:{mt}" + ("\n:71F:USD5,00" if mt == "BEN" else ""))
            _, conv, _ = rules(text)
            self.assertIn(f"<ChrgBr>{mx}</ChrgBr>".encode(), conv.xml)
    def test_missing_uetr_is_generated_and_flagged(self):
        r, conv, _ = rules(SAMPLE.replace("{121:3f2a6c1e-8d4b-4c3a-9a55-0d6f1b2c3d4e}", ""))
        self.assertIn("INF_UETR_GENERATED", r)
    def test_deterministic(self):
        a = process_text("T", SAMPLE)[1].xml; b = process_text("T", SAMPLE)[1].xml
        self.assertEqual(a, b)


class Rules(unittest.TestCase):
    def test_bad_iban(self):
        r, _, _ = rules(SAMPLE.replace("PK36SCBL0000001123456702", "PK37SCBL0000001123456702"))
        self.assertIn("BR_IBAN_CHK", r)
    def test_jpy_decimals(self):
        r, _, _ = rules(SAMPLE.replace("USD1250,00", "JPY1250,50"))
        self.assertIn("BR_AMT_DECIMALS", r)
    def test_bad_date_rejected(self):
        r, conv, rej = rules(SAMPLE.replace("261005", "260231"))
        self.assertTrue(rej); self.assertIn("SX_DATE_INVALID", r); self.assertIsNone(conv.xml)
    def test_missing_comma(self):
        r, _, rej = rules(SAMPLE.replace("USD1250,00", "USD1250"))
        self.assertTrue(rej); self.assertIn("SX_AMOUNT_FORMAT", r)
    def test_address_without_country_flagged(self):
        r, _, _ = rules(SAMPLE.replace("KARACHI PK", "WAZIRABAD"))
        self.assertIn("BR_ADDR_TWN_CTRY", r)
    def test_weekend(self):
        r, _, _ = rules(SAMPLE.replace("261005", "261003"))     # Saturday
        self.assertIn("BR_VALUE_DATE_WEEKEND", r)
    def test_charge_rule(self):
        r, _, _ = rules(SAMPLE.replace(":71A:SHA", ":71A:OUR\n:71F:USD5,00"))
        self.assertIn("BR_CHRG_RULE", r)
    def test_xsd_catches_bad_structure(self):
        from mt2iso.validator import validate_mx
        _, conv, _ = rules(SAMPLE)
        broken = conv.xml.replace(b"<ChrgBr>SHAR</ChrgBr>", b"<ChrgBr>XXXX</ChrgBr>")
        self.assertTrue(any(f.rule_id == "XSD_001" for f in validate_mx("T", broken)))


class Pipeline(unittest.TestCase):
    def test_dataset_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            generate(os.path.join(d, "data"))
            res, find, lin, ev, s = run(os.path.join(d, "data"), os.path.join(d, "out"))
            self.assertEqual(s["messages"], 100)
            self.assertEqual(s["defects_injected"], 46)
            self.assertEqual(s["defects_detected"], 46)
            self.assertEqual(s["false_alarm_messages"], [])


if __name__ == "__main__":
    unittest.main()
