from ai_tools.hybrid import HybridSearch


db = HybridSearch(
    r"%USERPROFILE%\ghidra_ai_exports\sample_program.exe"
)


print(
    db.context(
        "network packet encryption"
    )
)
