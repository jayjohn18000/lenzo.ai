# pocketflow/flow.py
import argparse
from pocketflow.store import SharedStore
from pocketflow.nodes.plan_ticket import PlanTicket
from pocketflow.nodes.apply_edits import ApplyEdits
from pocketflow.nodes.run_tests import RunTests
from pocketflow.nodes.format_code import FormatCode
from pocketflow.nodes.smoke_check import SmokeCheck


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticket", required=True, help="path to YAML ticket")
    args = ap.parse_args()

    store = SharedStore()

    steps = [
        PlanTicket(args.ticket),
        ApplyEdits(),
        RunTests(),
        FormatCode(),
        SmokeCheck(),
    ]

    for step in steps:
        print(f"→ Running node: {step.name}")
        step.run(store)
        store.save()

    print("\nDone. Summary:")
    for k, v in store.context.items():
        print(f"- {k}: {v}")


if __name__ == "__main__":
    main()
