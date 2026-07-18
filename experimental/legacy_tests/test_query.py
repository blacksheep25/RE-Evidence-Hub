from experimental.ai_tools.query import BinarySearch


db = BinarySearch(
    r"%USERPROFILE%\ghidra_ai_exports\sample_program.exe"
)


results = db.search(
    "socket connect network packet",
    10
)


for r in results:

    fn = r["function"]

    print("=" * 60)

    print("Score:", r["score"])
    print("Name:", fn.get("name"))
    print("Address:", fn.get("address"))

    print("\n--- TEXT SAMPLE ---")

    print(
        str(fn)[:1000]
    )
