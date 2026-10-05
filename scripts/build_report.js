const fs = require("fs");
const D = require("../docs/report_data.json");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell, WidthType, BorderStyle,
  ShadingType, ImageRun, PageBreak, TableOfContents, Footer, PageNumber, LevelFormat, Header,
} = require("docx");

const S = D.summary, SC = D.scenarios;
const W = 9026; // A4 content width in DXA with 1" margins
const FONT = "Calibri", NAVY = "1F3A5F";
const pct = (x, d = 0) => (x * 100).toFixed(d) + "%";
const usd = (x) => (x < 0 ? "-$" : "$") + Math.round(Math.abs(x)).toLocaleString("en-US");

const run = (t, o = {}) => new TextRun({ text: t, font: FONT, size: 22, ...o });
const P = (t, o = {}) => new Paragraph({ spacing: { after: 140, line: 300 }, alignment: AlignmentType.JUSTIFIED, ...o, children: Array.isArray(t) ? t : [run(t)] });
const B = (t) => new Paragraph({ numbering: { reference: "bul", level: 0 }, spacing: { after: 80, line: 290 }, children: Array.isArray(t) ? t : [run(t)] });
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: true, children: [new TextRun({ text: t, font: FONT })] });
const H1n = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: t, font: FONT })] });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: t, font: FONT })] });
const bold = (t) => run(t, { bold: true });
const code = (t) => new Paragraph({ spacing: { after: 0, line: 240 }, shading: { type: ShadingType.CLEAR, fill: "F2F2F2" }, children: [new TextRun({ text: t, font: "Courier New", size: 16 })] });
const caption = (t) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [run(t, { italics: true, size: 18, color: "555555" })] });
const img = (path, w, h) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 60 }, children: [new ImageRun({ type: "png", data: fs.readFileSync(path), transformation: { width: w, height: h }, altText: { title: path, description: path, name: path } })] });

const border = { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" };
const borders = { top: border, bottom: border, left: border, right: border };
function table(headers, rows, widths, opts = {}) {
  const total = widths.reduce((a, b) => a + b, 0);
  const cell = (t, w, hdr, i) => new TableCell({
    width: { size: w, type: WidthType.DXA }, borders,
    shading: hdr ? { type: ShadingType.CLEAR, fill: NAVY } : (opts.zebra && i % 2 ? { type: ShadingType.CLEAR, fill: "F3F6FA" } : undefined),
    margins: { top: 50, bottom: 50, left: 90, right: 90 },
    children: [new Paragraph({ alignment: hdr ? AlignmentType.LEFT : (opts.right && opts.right.includes(widths.indexOf(w)) ? AlignmentType.RIGHT : AlignmentType.LEFT), children: [new TextRun({ text: String(t), font: FONT, size: opts.size || 18, bold: hdr, color: hdr ? "FFFFFF" : "000000" })] })],
  });
  return new Table({
    width: { size: total, type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, children: headers.map((h, i) => cell(h, widths[i], true, 0)) }),
      ...rows.map((r, ri) => new TableRow({ children: r.map((c, i) => cell(c, widths[i], false, ri)) }))],
  });
}
const gap = () => new Paragraph({ spacing: { after: 120 }, children: [] });

// ------------------------------------------------------------------ numbers
const n = S.messages, st = S.status;
const fail = st.FAILED_VALIDATION || 0, rej = st.REJECTED || 0, clean = st.PASS_CLEAN || 0, warn = st.PASS_WITH_WARNINGS || 0;
const addrTC = S.address_town_country, addrN = S.address_parties, addrSt = S.address_street;
const pk = S.address_by_country.PK, de = S.address_by_country.DE, us = S.address_by_country.US;
const R = S.rules;
const content = [];

// ------------------------------------------------------------------ title page
content.push(new Paragraph({ spacing: { before: 2200 }, children: [] }));
content.push(new Paragraph({ alignment: AlignmentType.LEFT, spacing: { after: 120 }, children: [new TextRun({ text: "ISO 20022 Legacy-to-MX Payment Migration Toolkit", font: FONT, size: 52, bold: true, color: NAVY })] }));
content.push(new Paragraph({ spacing: { after: 400 }, children: [new TextRun({ text: "Converting SWIFT MT103 to pacs.008.001.08, validating the result, and measuring what the migration gains, loses or guesses", font: FONT, size: 28, color: "555555" })] }));
content.push(new Paragraph({ spacing: { after: 60 }, border: { top: { style: BorderStyle.SINGLE, size: 12, color: NAVY, space: 8 } }, children: [run("Project report", { bold: true })] }));
content.push(P("Muhammad Hamza  |  BS FinTech, FAST-NUCES Karachi", { alignment: AlignmentType.LEFT }));
content.push(P("October 2026  |  Version 1.0", { alignment: AlignmentType.LEFT }));
content.push(new Paragraph({ spacing: { before: 1800 }, children: [run("Deliverables accompanying this report: Python package (mt2iso), 100-message synthetic dataset with ground-truth labels, subset XSD, unit tests, and an Excel dashboard with a five-year business case. All figures in this report are generated from the code's own output.", { italics: true, size: 20, color: "555555" })] }));

content.push(new Paragraph({ children: [new PageBreak()] }));
content.push(new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: "Contents", font: FONT })] }));
content.push(new TableOfContents("Contents", { hyperlink: true, headingStyleRange: "1-2" }));

// ------------------------------------------------------------------ exec summary
content.push(H1("Executive summary"));
content.push(P(`ISO 20022 replaces the field-based MT messages that banks have used for decades with rich, structured XML. For cross-border payments the migration has a hard edge: Swift has stated that from 14 November 2026 payments carrying fully unstructured postal addresses will be rejected on the CBPR+ network, and that only structured or hybrid addresses (with at least town and country) will be accepted. At the time of writing that is about six weeks away. Swift's own adoption statistics for July 2026 still show roughly 58% of debtor and 59% of creditor addresses in unstructured form.`));
content.push(P("This project builds and evaluates a working migration toolkit around that problem. It converts an MT103 customer credit transfer to a pacs.008.001.08 message, validates the output at three levels, records for every populated XML element where its value came from, and flags what the old format forced the translator to lose or guess."));
content.push(P([bold("Main results on the synthetic stress test (100 messages, 46 carrying one injected defect each):")]));
content.push(B(`${clean + warn} of ${n} messages (${pct((clean + warn) / n)}) converted and passed validation (${clean} clean, ${warn} with warnings); ${fail} converted but failed validation and ${rej} could not be translated at all, giving a repair rate of ${pct((fail + rej) / n)}.`));
content.push(B(`All ${S.defects_injected} injected defects were caught by the rule designed to catch them, with no false alarms on the ${S.clean_messages} defect-free messages. This shows the rules are implemented correctly; it does not show they would catch everything in real traffic (see Section 8).`));
content.push(B(`Only ${pct(S.deterministic_share)} of the populated ISO 20022 elements are direct or code-table copies of MT data. ${pct(S.heuristic_share)} are parsed from free text by heuristics, ${pct(S.inferred_share)} are inferred (not present in the MT103 at all) and ${pct(S.freetext_share)} stay free text. A migration is therefore not a format conversion: roughly four in ten values involve a judgement.`));
content.push(B(`Address structuring is the crux. The parser found town and country for ${addrTC} of ${addrN} parties (${pct(addrTC / addrN)}), which is what the November 2026 rule needs, but could structure street and building number for only ${pct(addrSt / addrN)}. For Pakistani addresses that figure was ${pct(pk.street / pk.parties)} against ${pct(de.street / de.parties)} for German ones, because house/plot/block conventions do not fit the "number + street" patterns that work elsewhere.`));
content.push(B(`In the illustrative business case, operational savings alone do not repay the one-off cost (Base-scenario NPV ${usd(SC.Base.npv_ope || SC.Base.npv_ops)}). The case rests on avoiding payments that would otherwise be rejected after the deadline. With Base assumptions the NPV is ${usd(SC.Base.npv_all)}; with Conservative assumptions it is ${usd(SC.Conservative.npv_all)}. The result is dominated by an assumption that must be replaced with bank data.`));

// ------------------------------------------------------------------ 1 intro
content.push(H1("1. Introduction"));
content.push(H2("1.1 Motivation"));
content.push(P("Payment messages are the plumbing of banking. For forty years the dominant format for cross-border credit transfers was the SWIFT MT103: a tagged text message with fields such as :50K: (ordering customer) and :59: (beneficiary), each a few lines of 35 characters. The format was designed for telex-era bandwidth. It squeezes a name, a street and a town into the same four lines and cannot say which is which."));
content.push(P("ISO 20022 is the global standard that replaces this with a business-model-based XML dictionary. Where an MT103 has one free-text block, a pacs.008 has separate elements for name, street, building number, postal code, town and country, plus dedicated elements for structured remittance data, a unique end-to-end transaction reference (UETR) and identification of every agent in the chain. The promise is straight-through processing, better sanctions screening and better reconciliation."));
content.push(P("The difficulty is that real payment flows do not start out structured. Banks must translate from legacy data, and every translation involves decisions: how to split an address, what to do when a field is absent, how to treat characters that no longer need to be limited. These decisions are rarely visible. This project makes them visible and measurable."));
content.push(H2("1.2 Objectives"));
content.push(B("Build a transparent MT103 to pacs.008.001.08 translator whose every output value is traceable to its source and to the method that produced it."));
content.push(B("Validate output at three levels: XML schema, MT network rules, and ISO 20022 / CBPR+ business rules."));
content.push(B("Quantify what the migration gains (structure), loses (truncation, dropped data) and guesses (inference)."));
content.push(B("Test the toolkit against a labelled dataset so that detection performance is measured rather than asserted."));
content.push(B("Translate the technical findings into a cost-benefit model that a product or finance owner could adapt."));
content.push(H2("1.3 Scope"));
content.push(P("The toolkit covers one message pair (MT103 to pacs.008) and the fields that matter for customer credit transfers. It does not implement the business application header (head.001), cover payments (MT202 COV / pacs.009), return or status messages, or Swift's own conversion service. The dataset is synthetic. Section 8 discusses what these boundaries mean for the conclusions."));

// ------------------------------------------------------------------ 2 background
content.push(H1("2. Background"));
content.push(H2("2.1 What ISO 20022 is"));
content.push(P("ISO 20022 is not a message format but a methodology and a repository: a common data dictionary and a modelling approach from which message definitions are derived and published as XML schemas. Messages are named by a four-letter business area, a three-digit message number, and a variant and version, for example pacs.008.001.08, which is FIToFICustomerCreditTransferV08."));
content.push(table(["Business area", "Purpose", "Examples"], [
  ["pain", "Payments initiation: customer to bank", "pain.001 credit transfer initiation; pain.008 direct debit"],
  ["pacs", "Payments clearing and settlement: bank to bank", "pacs.008 customer credit transfer; pacs.009 FI transfer; pacs.002 status"],
  ["camt", "Cash management and reporting", "camt.053 statement; camt.056 recall request"],
  ["head", "Business application header", "head.001 envelope carrying sender, receiver, UETR"],
], [1600, 3400, 4026], { zebra: true }));
content.push(caption("Table 1. The main ISO 20022 message families used in payments."));
content.push(P("The key differences between the two worlds, as they affect a translator, are summarised below."));
content.push(table(["Aspect", "MT103 (FIN)", "pacs.008 (ISO 20022 XML)"], [
  ["Structure", "Tagged text fields, positional conventions", "Hierarchical XML validated by XSD"],
  ["Names and addresses", "4 x 35 characters, name and address mixed", "Name up to 140; postal address with 14+ separate elements"],
  ["Remittance", "4 x 35 characters (140) with informal code words", "Unstructured 140 plus structured document and creditor-reference blocks"],
  ["Character set", "Restricted SWIFT X set", "Unicode (subject to usage guidelines)"],
  ["Tracking", "UETR optional in header (gpi)", "UETR a defined element, mandatory in CBPR+"],
  ["Agents", "Sender and receiver implicit; others optional", "Debtor agent and creditor agent mandatory"],
  ["Amounts", "Decimal comma, text", "Decimal point, typed, currency attribute"],
], [1800, 3400, 3826], { zebra: true }));
content.push(caption("Table 2. MT103 compared with pacs.008."));
content.push(H2("2.2 CBPR+ and the November 2026 address deadline"));
content.push(P("Swift's Cross-Border Payments and Reporting Plus (CBPR+) usage guidelines define how ISO 20022 is used on the Swift network. During a coexistence period institutions could send either format and the network translated between them. Swift's published guidance on the Standards Release 2026 sets 14 November 2026 as the date after which fully unstructured postal addresses are no longer accepted. A hybrid address must contain town name and country and may add up to two unstructured address lines of 70 characters; a fully structured address uses the individual elements. Swift states that payments containing unstructured addresses will be rejected at network level from that date, and that BIC-only identification remains valid for agents."));
content.push(P("This rule drives the central design choice of the toolkit. Whatever else a translated message contains, each debtor and creditor address must carry TwnNm and Ctry. Rule BR_ADDR_TWN_CTRY encodes this, and the address parser exists to recover those two values from MT free text wherever possible."));
content.push(H2("2.3 The Pakistan context"));
content.push(P("Pakistan is not a bystander in this transition. The State Bank of Pakistan launched the Raast instant payment system in 2021, built on the ISO 20022 standard, and its upgraded PRISM+ real-time gross settlement system is also ISO 20022 based. Banks that receive inbound cross-border remittances, a major flow for Pakistan, therefore sit between two ISO 20022 environments: Swift's CBPR+ on one side, domestic Raast and PRISM+ on the other. One practical consequence appears in the toolkit as rule BR_NON_IBAN_ACCT: bank guidance on Raast notes that an IBAN must be supplied for the beneficiary account when payments are routed through it, so an inbound MT103 that names a local account number needs enrichment before onward credit."));

// ------------------------------------------------------------------ 3 method
content.push(H1("3. Methodology"));
content.push(H2("3.1 Design principle: every value has provenance"));
content.push(P("A conventional converter produces output and a pass or fail. This toolkit also produces a lineage record for every populated leaf element of the output: the ISO 20022 path, the MT source and one of five methods."));
content.push(table(["Method", "Meaning", "Example"], [
  ["DIRECT", "Value copied or format-converted from one MT field", "IntrBkSttlmAmt from :32A: ; IBAN from the account line"],
  ["CODE", "Value derived through a code table or code word", ":71A: OUR to ChrgBr DEBT ; /INV/ to document type CINV"],
  ["PARSED", "Value read out of free text by heuristics", "TwnNm and Ctry from the last line of a :59: address"],
  ["INFERRED", "Value that is not in the MT103 at all", "Generated UETR; creditor agent assumed to be the receiving bank"],
  ["FREETEXT", "Free text carried into an unstructured element", "AdrLine leftovers; :72: narrative"],
], [1300, 3600, 4126], { zebra: true }));
content.push(caption("Table 3. Lineage methods."));
content.push(P("The mix of methods is itself a measurement of migration risk. DIRECT and CODE values are deterministic and can be audited by rule. PARSED and INFERRED values are judgements that can be wrong, and a bank adopting a translator should know how much of each outgoing message rests on them."));
content.push(H2("3.2 Field mapping"));
content.push(P("The mapping covers twenty-odd MT fields. The complete matrix, including the MT constraint, the ISO capability and an assessment of whether each mapping is a gain, a guess or a loss, is in the Excel workbook (sheet Mapping Matrix). The principal decisions are:"));
content.push(B([bold("Identifiers. "), run(":20: becomes MsgId, InstrId and TxId. EndToEndId is taken from a /ROC/ code word in :70: when present, otherwise set to NOTPROVIDED and flagged, because the MT103 has no dedicated field for the originator's reference.")]));
content.push(B([bold("UETR. "), run("Taken from header tag 121 when present. When absent a UETR is generated, which keeps the message schema-valid but breaks end-to-end tracking, so INF_UETR_GENERATED is raised as a warning.")]));
content.push(B([bold("Charges. "), run("OUR, BEN and SHA map to DEBT, CRED and SHAR. Fields 71F and 71G do not name the bank that levied the charge but the ISO element requires an agent, so the header BIC is assumed and the guess is recorded.")]));
content.push(B([bold("Agents. "), run("Absent :52a: and :57a: fields are filled from the sending and receiving bank BICs. In the common case this is correct, since the receiving bank is often the creditor agent, but it cannot be verified from the message, so it is recorded as an inference.")]));
content.push(B([bold("Remittance. "), run("Code words are lifted into structure: /INV/ to a referred-document block of type CINV and /RFB/ to the creditor reference. Remaining text is joined into Unstructured remittance, split across two elements only if it exceeds 140 characters.")]));
content.push(B([bold("Settlement method. "), run("Simplified: INDA by default, INGA when only a sender's correspondent is present. Real settlement-method selection depends on bilateral arrangements and is out of scope.")]));
content.push(H2("3.3 Address structuring"));
content.push(P("The address parser works on the lines that follow the name in :50K: or :59:. It first reads the last line for town, postal code, state and country, using ordered patterns: US (town, state, ZIP), UK postcode, postcode-first (continental European) and town-postcode. It accepts a country as a two-letter ISO code or as a full name. Then it tries to split one remaining line into street and building number using two conservative patterns, number-first (123 MAIN STREET) and number-last (HAUPTSTRASSE 1). The street pattern deliberately refuses lines that already contain digits in the street part, to avoid inventing a street name from a line such as HOUSE 12 STREET 5 DHA PHASE 6. Anything left over becomes AdrLine."));
content.push(P("Two safeguards matter. First, a small gazetteer can supply a country when the text names only a well-known town, but that country is tagged INFERRED and raises INF_CTRY_FROM_TOWN as a warning, because namesake towns exist. Second, if no town and country can be established the address is left unstructured and the validator raises BR_ADDR_TWN_CTRY as an error, rather than letting a guess through."));
content.push(H2("3.4 Validation layers"));
content.push(table(["Layer", "What it checks", "Implementation"], [
  ["1. MT syntax and network rules", "Mandatory fields, FIN formats (dates, decimal comma), code words, 35-character lines, OUR/SHA/BEN charge combinations, exchange-rate presence", "mt103.py, validator.validate_mt"],
  ["2. XML schema", "Element order, cardinality, patterns (BIC, IBAN, UETR, country), maximum lengths, enumerations, decimal facets", "lxml XMLSchema over a subset XSD"],
  ["3. Business rules", "BIC country, IBAN mod-97 and length, ISO 4217 currency and decimals, weekend value date, IBAN-versus-address country, name presence, CBPR+ address readiness, Pakistani IBAN requirement", "validator.validate_mx"],
], [2200, 4400, 2426], { zebra: true }));
content.push(caption("Table 4. Validation layers."));
content.push(P("The XSD deserves a precise description. The official pacs.008.001.08 schema is published by ISO 20022 and distributed with CBPR+ usage guidelines; it could not be downloaded in the environment where this project was built. The toolkit therefore ships a subset schema written from the published message structure. It preserves the element names, order, cardinality and primitive-type facets for exactly the elements the mapper emits and is stricter than the official schema about which elements may appear. The validator accepts a path to the official XSD, so the same checks run against the full schema once it is supplied. Layer 2 results should be read in that light."));
content.push(H2("3.5 Analyzer and scoring"));
content.push(P("Findings are classified into seven categories (syntax, schema, business, address, data loss, inference, enrichment) and three severities. Each message receives a status and a 0-100 quality score: 30 points off per error, 6 per warning and 2 per informational inference or data-loss note, with rejected messages scoring zero. The weights are a judgement, chosen so that one error outweighs several warnings; they are exposed in analyzer.py for adjustment. The status follows from the worst finding: PASS_CLEAN, PASS_WITH_WARNINGS, FAILED_VALIDATION (at least one error) or REJECTED (no ISO message could be produced)."));

// ------------------------------------------------------------------ 4 implementation
content.push(H1("4. System design and implementation"));
content.push(img("docs/fig/arch.png", 560, 232));
content.push(caption("Figure 1. Toolkit architecture."));
content.push(table(["Module", "Responsibility"], [
  ["mt103.py", "Splits FIN blocks, parses block 4 fields, parses party fields (options A, D, F, K), applies syntax rules"],
  ["addrparse.py", "Free-text address to structured fields with inference flags"],
  ["mapper.py", "Builds the pacs.008 tree with lxml, records lineage and mapper-side findings"],
  ["validator.py", "XSD validation, MT network rules and business rules; central rule catalogue"],
  ["analyzer.py", "Truncation indicators, scoring, status assignment"],
  ["ibanutil.py, refdata.py", "mod-97 IBAN logic, BIC pattern, ISO country and currency tables, IBAN lengths, small gazetteer"],
  ["dataset.py", "Synthetic MT103 generator with ground-truth defect injection"],
  ["pipeline.py, __main__.py", "Batch run, evaluation against ground truth, CSV and JSON outputs, command-line interface"],
], [2600, 6426], { zebra: true }));
content.push(caption("Table 5. Package structure."));
content.push(P(`The package is plain Python with one third-party dependency (lxml). Output is deterministic: timestamps are fixed in batch mode and the UETR for messages lacking one is derived from a hash of the message identifier, so reruns produce byte-identical XML. Twenty-five unit tests cover the IBAN and BIC checks, the address parser (including the Pakistani house-number case), field mapping values, each injected defect type, XSD rejection of a broken message, and a full end-to-end run asserting 100 messages, 46 injected defects, 46 detected and no false alarms.`));
content.push(P("Usage is a single command per step: python -m mt2iso generate creates the dataset, python -m mt2iso batch converts and evaluates it, and python -m mt2iso convert FILE converts one message and prints findings. scripts/build_dashboard.py builds the Excel workbook from the batch output."));

// ------------------------------------------------------------------ 5 dataset
content.push(H1("5. Dataset"));
content.push(P("Because real payment messages are confidential, the evaluation uses 100 synthetic MT103 messages generated with a fixed random seed. Names, accounts and BICs are invented; the institutions are fictional although their BICs follow the valid format. IBANs are generated with correct country structure and check digits so that valid messages are valid. The mix is modelled on corridors that matter for Pakistan."));
content.push(table(["Scenario", "Description", "Messages"], [
  ["S1", "Inbound worker remittance: individual abroad (UAE, Saudi Arabia, UK, US) to individual in Pakistan", "40"],
  ["S2", "Inbound trade: foreign company (China, Germany, Singapore, US, UAE, UK) to Pakistani company", "25"],
  ["S3", "Outbound trade: Pakistani company to foreign supplier, sometimes with FX fields", "25"],
  ["S4", "Services payments to and from the UK and US", "10"],
], [1100, 6700, 1226], { zebra: true, right: [2] }));
content.push(caption("Table 6. Scenario mix."));
content.push(P("Variety is built in without being counted as defects: 25% of messages lack a UETR, 40% lack :52a:, 70% lack :57a:, about half carry /INV/ or /RFB/ code words, some use structured :50F:/:59F: parties, 71F/71G charges, :72: narrative, :77B: regulatory text and FX fields. Addresses follow national styles, including Pakistani house-and-block forms."));
content.push(P("Forty-six messages carry exactly one injected defect, each paired in a manifest with the rule that should fire."));
content.push(table(["Defect", "Injected", "Rule expected"], [
  ["IBAN checksum corrupted", "4", "BR_IBAN_CHK"], ["IBAN length wrong", "2", "BR_IBAN_LEN"], ["BIC malformed / bad country", "4", "BR_BIC_FMT or BR_BIC_CTRY"],
  ["Address without town or country", "5", "BR_ADDR_TWN_CTRY"], ["Address with town only (country must be inferred)", "3", "INF_CTRY_FROM_TOWN"],
  ["Name exactly fills 35-character line", "3", "DL_NAME_TRUNC_SUSPECT"], ["Remittance fills all four lines", "3", "DL_RMT_TRUNC_SUSPECT"],
  ["JPY amount with decimals", "2", "BR_AMT_DECIMALS"], ["Unknown currency code", "2", "BR_CCY_UNKNOWN"], ["Impossible calendar date", "2", "SX_DATE_INVALID"],
  ["Amount without decimal comma", "2", "SX_AMOUNT_FORMAT"], ["OUR with 71F present", "2", "BR_CHRG_RULE"], ["33B in another currency, no rate", "2", "BR_FX_RATE_MISSING"],
  ["Weekend value date", "2", "BR_VALUE_DATE_WEEKEND"], ["IBAN country differs from address country", "2", "BR_IBAN_ADDR_MISMATCH"], ["Mandatory field missing", "2", "SX_MISSING_FIELD"],
  ["Pakistani creditor with local account number", "4", "BR_NON_IBAN_ACCT"],
], [4300, 1100, 3626], { zebra: true, right: [1], size: 17 }));
content.push(caption("Table 7. Injected defect catalogue (46 in total)."));
content.push(P([bold("A caution about circularity. "), run("The same author wrote the defect injector and the rules. A perfect detection score therefore shows that the rules do what they were written to do; it is not evidence that the toolkit finds defects it was not designed for, or that real traffic contains defects in these proportions. 46% defective is a stress test, not an estimate of real-world error rates.")]));

// ------------------------------------------------------------------ 6 results
content.push(H1("6. Results"));
content.push(H2("6.1 Migration outcomes"));
content.push(img("docs/fig/status.png", 480, 248));
content.push(caption("Figure 2. Outcome of converting 100 MT103 messages."));
content.push(P(`${clean + warn} messages (${pct((clean + warn) / n)}) went straight through, ${clean} with nothing above informational notes. ${fail} converted but failed validation, and ${rej} could not be translated because a mandatory field was missing or unparseable (two bad dates, two amounts without a decimal comma, two missing mandatory fields). The average quality score was ${S.avg_score.toFixed(1)} out of 100. Because defects were injected into 46% of messages, the 27% repair rate means that more than half of the injected defects are repair-triggering rather than merely noted; several defect types (weekend dates, non-IBAN Pakistani accounts, missing FX rates, truncation suspicion) are warnings by design.`));
const sb = S.status_by_scenario;
content.push(table(["Scenario", "Messages", "Clean", "Warnings", "Failed", "Rejected", "Repair rate"],
  ["S1", "S2", "S3", "S4"].map((k) => { const t = Object.values(sb[k]).reduce((a, b) => a + b, 0); return [k, t, sb[k].PASS_CLEAN || 0, sb[k].PASS_WITH_WARNINGS || 0, sb[k].FAILED_VALIDATION || 0, sb[k].REJECTED || 0, pct(((sb[k].FAILED_VALIDATION || 0) + (sb[k].REJECTED || 0)) / t)]; }),
  [1300, 1200, 1100, 1300, 1100, 1300, 1726], { zebra: true, right: [1, 2, 3, 4, 5, 6] }));
content.push(caption("Table 8. Outcome by business scenario. Differences between scenarios mostly reflect where the random defect injection landed and should not be read as corridor-specific error rates."));
content.push(H2("6.2 Detection against ground truth"));
content.push(img("docs/fig/recall.png", 520, 358));
content.push(caption("Figure 3. Detection recall by injected defect type."));
content.push(P(`All ${S.defects_injected} injected defects were detected by the expected rule and none of the ${S.clean_messages} defect-free messages raised an error. Getting there required one fix that the evaluation exposed: an early version of the dataset generator produced :72: narrative lines longer than 35 characters, which the syntax rules correctly flagged as errors on 10 supposedly clean messages. That was a generator bug, not a rule bug, and it was found only because the manifest lets false alarms be counted, which is the main argument for ground-truth labelling.`));
content.push(H2("6.3 Where do the values come from?"));
content.push(img("docs/fig/lineage.png", 500, 297));
content.push(caption("Figure 4. Provenance of populated ISO 20022 elements, by element group."));
content.push(P(`Across ${Object.values(S.lineage_mix).reduce((a, b) => a + b, 0).toLocaleString("en-US")} populated leaf elements, ${pct(S.deterministic_share)} were deterministic (DIRECT or CODE), ${pct(S.heuristic_share)} PARSED, ${pct(S.inferred_share)} INFERRED and ${pct(S.freetext_share)} FREETEXT. Figure 4 shows why: the debtor and creditor groups are dominated by PARSED values, because the whole address block is recovered from free text, while agent and payment-identification groups are mostly direct or inferred. The inferred share comes mainly from constants that have to exist in ISO 20022 (message ID timestamp, number of transactions, settlement method, EndToEndId default) and from assumed agents and UETRs.`));
content.push(H2("6.4 Address structuring and the November 2026 test"));
content.push(img("docs/fig/address.png", 480, 248));
content.push(caption("Figure 5. Address structuring success by party country (heuristic parser)."));
content.push(P(`Town and country were found for ${addrTC} of ${addrN} parties (${pct(addrTC / addrN, 1)}). The five failures are exactly the five injected cases without a recognisable town or country, so on this dataset the parser met the CBPR+ minimum wherever the MT text contained the information. Street and building number are a different story: only ${addrSt} of ${addrN} parties (${pct(addrSt / addrN, 1)}) were fully structured. The US and Germany reach ${pct(us.street / us.parties)} and ${pct(de.street / de.parties)}, while Pakistan reaches ${pct(pk.street / pk.parties)}, because forms such as HOUSE 12 STREET 5 DHA PHASE 6 or PLOT 45 BLOCK 7 CLIFTON carry several numbers and a hierarchy of sub-areas that a number-plus-street pattern cannot disambiguate. These addresses are still valid hybrid addresses (town, country and one AdrLine), so they pass the November 2026 rule. The cost is that downstream screening gets less structure to work with for exactly the corridor this project cares most about.`));
content.push(H2("6.5 What the analyzer found"));
const rk = Object.entries(R).sort((a, b) => b[1] - a[1]).slice(0, 12);
const cat = Object.fromEntries(D.rules.map((r) => [r[0], [r[1], r[2]]]));
content.push(table(["Rule", "Category", "Severity", "Times fired"], rk.map(([k, v]) => [k, cat[k][0], cat[k][1], v]), [3600, 1800, 1700, 1926], { zebra: true, right: [3] }));
content.push(caption("Table 9. The twelve most frequent findings."));
content.push(B(`BR_E2E_NOTPROVIDED (${R.BR_E2E_NOTPROVIDED} messages): the originator's reference is usually lost. Only about one in five messages carried a /ROC/ code word, which is a genuine information gap that no translator can fill.`));
content.push(B(`INF_CDTRAGT_INFERRED (${R.INF_CDTRAGT_INFERRED}) and INF_DBTRAGT_INFERRED (${R.INF_DBTRAGT_INFERRED}): agents assumed from the message envelope.`));
content.push(B(`INF_UETR_GENERATED (${R.INF_UETR_GENERATED}): a quarter of the messages had no UETR. A generated UETR is valid but unknown to the rest of the chain.`));
content.push(B(`GAIN_STRUCT_ADDR (${R.GAIN_STRUCT_ADDR}) and GAIN_STRUCT_RMT (${R.GAIN_STRUCT_RMT}): the positive side of the ledger, structure that the MT format held implicitly and the translation made explicit.`));
content.push(H2("6.6 Worked example"));
content.push(P("MSG002 is a UK-to-Pakistan remittance of GBP 319.92. The relevant MT103 lines are:"));
const exLines = D.example_mt.split("\n").filter((l) => /^:(32A|50K|59|70|71A)|^[A-Z0-9 \/]|^\{/.test(l) && !l.startsWith(":20") && !l.startsWith(":23"));
content.push(...D.example_mt.split("\n").slice(3, 15).map(code));
content.push(gap());
content.push(P("The creditor in the generated pacs.008 is:"));
const x = D.example_xml;
const cs = x.indexOf("<Cdtr>"), ce = x.indexOf("</CdtrAcct>") + 11;
content.push(...x.slice(cs, ce).split("\n").map((l) => code(l.replace(/^ {6}/, ""))));
content.push(gap());
content.push(P(`Name, town and country moved into dedicated elements (PARSED), the house line stayed as one AdrLine because it did not match a safe street pattern, and the account became a typed IBAN (DIRECT) which then passed the mod-97 and length checks. The analyzer raised five findings: two structuring gains, two informational agent inferences (no :52a: or :57a:) and the missing end-to-end reference. The message passed validation with a quality score of 96.`));

// ------------------------------------------------------------------ 7 business case
content.push(H1("7. Business case"));
content.push(H2("7.1 Structure"));
content.push(P("The Excel workbook contains a five-year cash-flow model for a hypothetical mid-size bank. Benefits come from three sources: fewer manual repairs (volume x repair rate x relative reduction x cost per repair), fewer false-positive sanctions alerts, and avoided cost for payments that would otherwise be rejected after the November 2026 deadline. Costs are a one-off migration cost in year 0 and an annual run cost. A scenario selector switches between Conservative, Base and Optimistic input sets, and two sensitivity grids show how the answer moves."));
content.push(P([bold("All inputs are illustrative. "), run("They are placeholders chosen to show the mechanics and are not derived from the toolkit's synthetic data, which says nothing about real repair rates or costs. The one input with an external anchor is the share of payments with unstructured addresses (Base 58%), which echoes Swift's published July 2026 network-wide level.")]));
const I = SC.Base.inputs;
content.push(table(["Input", "Conservative", "Base", "Optimistic"], [
  ["Payments per year", "400,000", "600,000", "800,000"], ["Repair rate today", "2.5%", "4.0%", "5.5%"], ["Relative cut in repairs", "15%", "30%", "45%"], ["Cost per repair", "$8", "$12", "$16"],
  ["Alert rate / FP cut / cost per alert", "2% / 5% / $6", "3% / 12% / $10", "4% / 20% / $14"], ["One-off cost", "$900,000", "$650,000", "$500,000"], ["Annual run cost", "$150,000", "$110,000", "$80,000"],
  ["Discount rate / volume growth", "12% / 2%", "10% / 5%", "8% / 8%"], ["Unstructured share / NAK'd if unremediated / cost per NAK", "40% / 2% / $20", "58% / 5% / $30", "60% / 10% / $45"],
], [3500, 1800, 1800, 1926], { zebra: true, right: [1, 2, 3], size: 17 }));
content.push(caption("Table 10. Scenario inputs (illustrative)."));
content.push(H2("7.2 Results"));
content.push(table(["Result", "Conservative", "Base", "Optimistic"], [
  ["NPV, all benefits", usd(SC.Conservative.npv_all), usd(SC.Base.npv_all), usd(SC.Optimistic.npv_all)],
  ["NPV, operational savings only", usd(SC.Conservative.npv_ops), usd(SC.Base.npv_ops), usd(SC.Optimistic.npv_ops)],
  ["Payback year", SC.Conservative.payback || "beyond 5", SC.Base.payback || "beyond 5", SC.Optimistic.payback || "beyond 5"],
], [3500, 1800, 1800, 1926], { zebra: true, right: [1, 2, 3] }));
content.push(caption("Table 11. Business case results by scenario (USD, five years)."));
content.push(P(`Two findings matter more than the headline numbers. First, operational savings alone do not repay the migration in the Conservative or Base scenario; they do so only in the Optimistic one. Second, in the Base scenario about 83% of five-year benefits come from avoiding rejected payments. That is the one assumption least grounded in data and the one the workbook isolates in Sensitivity B. With Base volume and costs, the migration breaks even at roughly a 2% rejection rate at $30 per rejected payment, and is deeply negative if no payments would have been rejected. The honest summary is that for a bank facing a hard network deadline the question is not whether the migration pays back on efficiency grounds, but how to meet the mandate at the lowest cost, and that data-quality tooling reduces that cost by shrinking the number of messages that need manual repair or risk rejection.`));
content.push(P("Benefits that are real but not quantified: improved screening accuracy beyond false-positive volume, faster reconciliation, ability to use Raast and other ISO 20022 domestic rails without re-keying data, and reduced operational risk from truncated names."));

// ------------------------------------------------------------------ 8 limitations
content.push(H1("8. Limitations and threats to validity"));
content.push(B([bold("Synthetic data. "), run("Real traffic has an unknown, probably messier distribution of formats and errors. Parsing success on generated addresses is an upper bound; real free-text addresses contain abbreviations, local-language transliterations, missing separators and typographical errors the generator does not produce.")]));
content.push(B([bold("Circular evaluation. "), run("Detection recall of 100% is measured against defects the same author designed rules for. It validates the implementation, not the coverage.")]));
content.push(B([bold("Subset XSD. "), run("Schema validation uses a stricter subset written for this project, not the official schema or the CBPR+ usage-guideline restrictions (for example, CBPR+ permits only a single Ustrd and restricts several elements further). A production deployment must validate against the official files.")]));
content.push(B([bold("Mapping decisions. "), run("Several mappings are defensible choices rather than normative translations: the use of Prtry for :23B: codes, the simplified settlement method, the single-agent assumption for charges. Swift's own MT-to-MX translation rules should be treated as authoritative where they differ.")]));
content.push(B([bold("Gazetteer and country rules. "), run("The gazetteer holds 33 towns. The IBAN length table covers 41 countries. Both are sufficient for the test data, not for production.")]));
content.push(B([bold("Scope. "), run("One message pair; no head.001 wrapper, cover payments, status or return messages; no XML signing; no performance testing.")]));
content.push(B([bold("Business case. "), run("Inputs are placeholders, the model ignores tax, FX, staff redeployment and the cost of an alternative (buying a conversion service), and one assumption dominates the result.")]));

// ------------------------------------------------------------------ 9 future
content.push(H1("9. Future work"));
content.push(B("Replace the subset XSD with the official pacs.008.001.08 schema and the CBPR+ usage-guideline rules, and add head.001 generation."));
content.push(B("Add the reverse direction (pacs.008 to MT103) to measure round-trip information loss directly rather than through proxies."));
content.push(B("Extend to pacs.009 and cover payments, pacs.002 status reports and camt.053 statements."));
content.push(B("Improve the address parser for South Asian formats with a larger gazetteer and a sequence model, and evaluate it on a labelled real-world corpus under suitable data-protection terms."));
content.push(B("Add a Raast-oriented output profile: a pacs.008 shaped for domestic instant payment, with IBAN enrichment from an account directory."));
content.push(B("Replace illustrative business-case inputs with a bank's actual repair logs, alert statistics and vendor quotes."));

// ------------------------------------------------------------------ 10 conclusion
content.push(H1("10. Conclusion"));
content.push(P(`The project set out to treat ISO 20022 migration as a measurement problem rather than a format-conversion problem, and the measurements support that framing. On a labelled stress test of 100 messages, ${pct((clean + warn) / n)} converted without needing repair, but only ${pct(S.deterministic_share)} of the populated output values were deterministic copies of legacy data. The rest rested on parsing, inference or free text. The November 2026 address rule is satisfiable for ${pct(addrTC / addrN)} of parties on this data, but street-level structure is much weaker for Pakistani addresses than for US or German ones, and that gap matters for screening quality. And in the illustrative business case, efficiency savings alone do not carry the investment: the deadline does.`));
content.push(P("For a fintech product role the transferable lesson is that a standard is a data contract, and the value of migrating to it depends on how much of the contract the source data can honestly fill. Making that visible, element by element, is what this toolkit is for."));

// ------------------------------------------------------------------ references
content.push(H1("References"));
const refs = [
  "Swift. ISO 20022: the removal of unstructured address. swift.com (Standards Release 2026; unstructured addresses rejected under CBPR+ from 14 November 2026; adoption statistics for pacs.008, June and July 2026).",
  "Swift. ISO 20022 CBPR+ compliance for partners: removal of unstructured postal addresses. swift.com.",
  "J.P. Morgan Payments. November 2026 Swift CBPR+ mandate: hybrid or fully structured addresses required. jpmorgan.com client resource center.",
  "State Bank of Pakistan Governor, keynote at the 13th Bank of the Future Forum, October 2024, as reported by ProPakistani and Pakistan Observer (Raast launched 2021 on ISO 20022; about 850 million transactions in under three years).",
  "The Paypers. SBP rolls out PRISM+ to improve its payment infrastructure (ISO 20022 based RTGS).",
  "Citibank Pakistan. Raast instant payments (guidance that an IBAN is required for the beneficiary account).",
  "ISO 20022 message definitions, pacs.008.001.08 FIToFICustomerCreditTransferV08. iso20022.org.",
  "ISO 13616 (IBAN) and ISO 9362 (BIC); ISO 4217 (currency codes); ISO 3166-1 (country codes).",
];
refs.forEach((r, i) => content.push(P(`[${i + 1}] ${r}`, { alignment: AlignmentType.LEFT })));

// ------------------------------------------------------------------ appendices
content.push(H1("Appendix A. Rule catalogue"));
content.push(table(["Rule", "Category", "Sev.", "What it checks"], D.rules.map((r) => [r[0], r[1], r[2], r[3]]), [2300, 1200, 800, 4726], { zebra: true, size: 15 }));
content.push(H1("Appendix B. Reproducing the results"));
["python -m unittest discover -s tests          # 25 tests", "python -m mt2iso generate --data data          # 100 synthetic MT103 + manifest", "python -m mt2iso batch --data data --out output  # convert, validate, analyze, evaluate",
  "python scripts/build_dashboard.py              # Excel workbook (then recalc)", "python -m mt2iso convert data/mt103/MSG002.txt # one message, findings on stderr"].forEach((l) => content.push(code(l)));
content.push(gap());
content.push(P("Outputs: output/pacs008/*.xml (one per converted message), results.csv, findings.csv, lineage.csv, evaluation.csv, summary.json, and the Excel dashboard. To validate against the official schema, pass its path as the xsd argument of validate_mx or the --xsd option of the command line."));

// ------------------------------------------------------------------ document
const doc = new Document({
  creator: "Muhammad Hamza", title: "ISO 20022 Migration Toolkit Report", features: { updateFields: true },
  styles: {
    default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 34, bold: true, font: FONT, color: NAVY }, paragraph: { spacing: { before: 240, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 26, bold: true, font: FONT, color: "2F5597" }, paragraph: { spacing: { before: 220, after: 120 }, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [{ reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, right: 1440, bottom: 1300, left: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "ISO 20022 Migration Toolkit  |  Page ", font: FONT, size: 18, color: "777777" }), new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 18, color: "777777" })] })] }) },
    children: content,
  }],
});
Packer.toBuffer(doc).then((b) => { fs.writeFileSync("output/ISO20022_Project_Report.docx", b); console.log("report saved"); });
