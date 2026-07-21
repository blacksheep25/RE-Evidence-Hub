# Security Policy

## Scope

RE-Evidence-Hub is a local evidence workflow. It is designed to keep target
binaries, exports, extracted assets, runtime captures, and model-run artifacts
out of the repository.

The HTTP API binds to loopback by default. A non-loopback bind requires both
`--allow-remote` and `GHIDRA_AI_REMOTE_TOKEN`; a token is intentionally not
accepted on the command line. Place any remote deployment behind TLS and
network access controls; the bundled Flask server is not an Internet-facing
deployment service.

## Reporting a vulnerability

Report vulnerabilities privately through a GitHub private security advisory for
this repository. Do not attach a target binary, decompiler export, credentials,
runtime capture, or other proprietary material to an issue or advisory.

If private reporting is unavailable, open a minimal issue requesting a private
contact channel and include only the affected source path, impact, and a safe
reproduction description.

## Supported versions

Security fixes are applied to the current `main` branch. Please update before
reporting an issue.
