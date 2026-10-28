# APKGuard

Static APK analyzer for non-experts: lists threats by severity in plain language, in Italian and English, entirely on the local machine.

## Status

- **M0** – Python engine: ingest (hashes, ZIP validation, XAPK), manifest, signing certificate, line-delimited JSON CLI, IT/EN message catalogs.
- **M1** – Code analysis: sensitive APIs in the DEX, packers and obfuscation, anti-analysis hints, indicators of compromise (URLs, IPs, Telegram/Discord exfiltration), hidden payloads inside the archive, generic YARA behaviour rules.

- **M2** – Scoring: app-category permission profiles, signal combinations (SMS stealer, banking trojan, dropper, spyware...), 0-100 risk score and a three-state verdict (no known threats / caution / do not install). Weights are provisional until calibrated on real corpora.
- **M3** – Authenticity: compares the signing certificate with a database of known fingerprints per package name. A different key against a *developer* key is a strong sign of tampering; against a *store* key (e.g. F-Droid re-signs most apps) it only means the APK came from another channel. The bundled database is currently **empty**: the F-Droid import is pending (see below).

Extra YARA rules (`.yar`) can be loaded from a directory set in `APKGUARD_RULES_DIR`.

## Development

```bash
cd engine
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
PYTHONPATH=tests pytest
apkguard analyze file.apk --lang en [--category flashlight]
```

Tests need `keytool` and `jarsigner` (from a JDK) to build harmless fixture APKs.

## Signature database

`engine/src/apkguard/data/fingerprints.json` (generated from public sources) and `curated_fingerprints.json` (added by hand) share one format, documented in `data/fingerprints.py`. To add a verified entry, read the fingerprint from an official APK:

```bash
apkguard fingerprint official.apk
```

and add it to `curated_fingerprints.json` under the package name. A custom file can also be merged at runtime with `APKGUARD_FINGERPRINTS_FILE`.
