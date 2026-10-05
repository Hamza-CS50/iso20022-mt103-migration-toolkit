"""CLI:  python -m mt2iso <command>

  convert FILE.txt [-o OUT.xml]      convert one MT103 to pacs.008 and print findings
  batch   [--data data --out output] run the full pipeline on the dataset
  generate [--data data]             (re)generate the synthetic dataset
"""
import argparse
import os
import sys
from .pipeline import process_text, run
from .dataset import generate


def main(argv=None):
    ap = argparse.ArgumentParser(prog="mt2iso", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("convert"); c.add_argument("file"); c.add_argument("-o", "--out"); c.add_argument("--xsd")
    b = sub.add_parser("batch"); b.add_argument("--data", default="data"); b.add_argument("--out", default="output"); b.add_argument("--xsd")
    g = sub.add_parser("generate"); g.add_argument("--data", default="data")
    a = ap.parse_args(argv)
    if a.cmd == "generate":
        rows = generate(a.data); print(f"generated {len(rows)} messages in {a.data}/")
    elif a.cmd == "batch":
        _, f, _, ev, s = run(a.data, a.out, a.xsd)
        print(f"{s['messages']} messages | STP {s['stp_rate']:.0%} | repair {s['repair_rate']:.0%} | "
              f"defects detected {s['defects_detected']}/{s['defects_injected']} | false alarms {len(s['false_alarm_messages'])}")
    else:
        text = open(a.file).read()
        mid = os.path.splitext(os.path.basename(a.file))[0]
        mt, conv, findings, rejected = process_text(mid, text, a.xsd)
        if conv.xml:
            if a.out:
                open(a.out, "wb").write(conv.xml)
            else:
                sys.stdout.write(conv.xml.decode())
        for f in findings:
            print(f"[{f.severity:7}] {f.rule_id:24} {f.path}: {f.message}", file=sys.stderr)
        return 1 if rejected or any(f.severity == "ERROR" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
