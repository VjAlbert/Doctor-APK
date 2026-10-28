# APKGuard

Static APK analyzer for non-experts: lists threats by severity in plain language, in Italian and English, entirely on the local machine.

## Status

- **M0** – Python engine: ingest (hashes, ZIP validation, XAPK), manifest, signing certificate, line-delimited JSON CLI, IT/EN message catalogs.
- **M1** – Code analysis: sensitive APIs in the DEX, packers and obfuscation, anti-analysis hints, indicators of compromise (URLs, IPs, Telegram/Discord exfiltration), hidden payloads inside the archive, generic YARA behaviour rules.

Extra YARA rules (`.yar`) can be loaded from a directory set in `APKGUARD_RULES_DIR`.

## Development

```bash
cd engine
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
PYTHONPATH=tests pytest
apkguard analyze file.apk --lang en
```

Tests need `keytool` and `jarsigner` (from a JDK) to build harmless fixture APKs.
