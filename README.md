# ISO 20022 Legacy-to-MX Payment Migration Toolkit

Converts a SWIFT **MT103** customer credit transfer into an ISO 20022 **pacs.008.001.08** message, validates it at three
levels, records where every output value came from, and measures what the migration **gains, loses or guesses**.

Why now: Swift has stated that from **14 November 2026** payments with fully unstructured postal addresses are rejected on
CBPR+. Only structured or hybrid addresses (town name and country at minimum) are accepted. This toolkit shows how much of a
real MT103 can be turned into compliant structure automatically, and how much rests on guesswork.

## Quick start
```bash
pip install lxml openpyxl matplotlib            # lxml is the only runtime dependency
python -m unittest discover -s tests            # 25 tests
python -m mt2iso generate --data data           # 100 synthetic MT103 + ground-truth manifest
python -m mt2iso batch --data data --out output # convert, validate, analyze, evaluate
python -m mt2iso convert data/mt103/MSG002.txt  # one message: XML on stdout, findings on stderr
python scripts/build_dashboard.py               # Excel dashboard + business case (then recalc in Excel/LibreOffice)
python scripts/make_figures.py && python scripts/prep_report_data.py && node scripts/build_report.js   # report
```

## What is in the box
| Path | Contents |
|---|---|
| `mt2iso/mt103.py` | FIN block parser, field/party parsing, MT syntax rules |
| `mt2iso/addrparse.py` | Free-text address -> structured/hybrid address with inference flags |
| `mt2iso/mapper.py` | pacs.008 builder with per-element **lineage** (DIRECT, CODE, PARSED, INFERRED, FREETEXT) |
| `mt2iso/validator.py` | XSD validation + MT network rules + ISO 20022/CBPR+ business rules (rule catalogue `RULES`) |
| `mt2iso/analyzer.py` | Truncation indicators, 0-100 quality score, status |
| `mt2iso/dataset.py` | Synthetic generator: 100 messages, 46 with one injected defect and the rule expected to catch it |
| `mt2iso/pipeline.py` | Batch run and evaluation against ground truth |
| `schemas/pacs.008.001.08.subset.xsd` | **Subset** schema authored from the published structure (see limits) |
| `tests/` | 25 unit and end-to-end tests |
| `output/` | Generated XML, CSVs, `summary.json`, Excel dashboard, Word report |

## Key results (synthetic stress test)
* 73 of 100 messages converted and passed validation; repair rate 27% (21 failed validation, 6 rejected at parse).
* 46/46 injected defects detected by the intended rule; 0 false alarms on the 54 defect-free messages.
* Only 52% of populated ISO 20022 elements are deterministic copies of MT data; 21% parsed from free text, 18% inferred, 9% free text.
* Town and country found for 97% of parties (the CBPR+ minimum), but street/building structured for only 43% (Pakistan 18%, US/Germany 100%).

## Limits you should know about
1. **Synthetic data.** A stress test, not a sample of real traffic. Parsing success is an upper bound.
2. **Circular evaluation.** The rules and the defect injector share an author. 100% recall validates the implementation, not coverage.
3. **Subset XSD.** The official pacs.008.001.08 XSD and CBPR+ usage-guideline restrictions were not available offline. Validate against the official files before any production use: `validate_mx(msg_id, xml, xsd_path="official.xsd")`.
4. **Mapping decisions** (e.g. `:23B:` to `SvcLvl/Prtry`, simplified settlement method) are documented choices, not normative Swift translation rules.
5. **Business case inputs are illustrative placeholders.** One assumption (avoided rejected payments) dominates the result and is isolated in a sensitivity table.

All names, accounts and BICs in the dataset are invented.
