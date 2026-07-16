import os


EXPORT_PATH = r"%USERPROFILE%\ghidra_ai_exports\sample_program.exe"

FUNCTION_PATH = os.path.join(
    EXPORT_PATH,
    "functions"
)


OUTPUT_PATH = os.path.join(
    EXPORT_PATH,
    "ai"
)
