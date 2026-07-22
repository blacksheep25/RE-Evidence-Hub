"""Read-only workflow status for one isolated agent run."""

from __future__ import annotations

import argparse
import json
import sys

from tools.local_evidence import LocalEvidenceStore
from tools.naming_candidates import campaign_status


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Show the next safe phase and exact candidate-review progress for one agent run."
    )
    parser.add_argument("export_path", help="Export folder containing agent_runs/<run-id>.")
    parser.add_argument("--run-id", required=True, help="Isolated agent run to summarize.")
    parser.add_argument("--compact", action="store_true", help="Print compact JSON.")
    args = parser.parse_args(argv)

    try:
        result = campaign_status(LocalEvidenceStore(args.export_path), args.run_id)
        print(json.dumps(result, ensure_ascii=False, indent=None if args.compact else 2,
                         separators=(",", ":") if args.compact else None))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print("[ERROR] {}".format(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
