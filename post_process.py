import argparse

from exporters.ai_summary_exporter import AISummaryExporter
from exporters.ai_context_exporter import AIContextExporter
from exporters.search_index_exporter import SearchIndexExporter
from exporters.function_summary_exporter import FunctionSummaryExporter

def run(export_path):
    failures = []

    print("==============================")
    print(" Ghidra AI Post Processor")
    print("==============================")


    jobs = [

        (
            "AI context",
            AIContextExporter
        ),

        (
            "AI summaries",
            AISummaryExporter
        ),

        (
            "Search index",
            SearchIndexExporter
        ),

        (
            "Function summaries",
            FunctionSummaryExporter
        )

    ]


    for name, exporter in jobs:

        print("")
        print("[+] " + name)

        try:

            instance = exporter(
                program=None,
                monitor=None,
                output=export_path,
                config=None
            )

            instance.export()

            print("[+] Complete")

        except Exception as e:

            print("[!] Failed")
            print(e)
            failures.append((name, str(e)))

    if failures:
        raise RuntimeError(
            "Post-processing failed: {}".format(
                "; ".join("{}: {}".format(name, error) for name, error in failures)
            )
        )



def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Rebuild host-derived context, summaries, and the search index."
    )
    parser.add_argument("export_path", help="Path to a completed Ghidra export")
    args = parser.parse_args(argv)
    run(args.export_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
