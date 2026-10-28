# APKGuard

Static APK analyzer for non-experts: lists threats by severity in plain language, in Italian and English, entirely on the local machine.

## Status

- **M0** – Python engine: ingest (hashes, ZIP validation, XAPK), manifest, signing certificate, line-delimited JSON CLI, IT/EN message catalogs.
- **M1** – Code analysis: sensitive APIs in the DEX, packers and obfuscation, anti-analysis hints, indicators of compromise (URLs, IPs, Telegram/Discord exfiltration), hidden payloads inside the archive, generic YARA behaviour rules.

- **M2** – Scoring: app-category permission profiles, signal combinations (SMS stealer, banking trojan, dropper, spyware...), 0-100 risk score and a three-state verdict (no known threats / caution / do not install). Weights are provisional until calibrated on real corpora.
- **M3** – Authenticity: compares the signing certificate with a database of known fingerprints per package name. A different key against a *developer* key is a strong sign of tampering; against a *store* key (e.g. F-Droid re-signs most apps) it only means the APK came from another channel. The bundled database is currently **empty**: the F-Droid import is pending (see below).
- **M4** – Desktop UI (React + Tailwind + Framer Motion): home with drag and drop and recent analyses, animated scan, verdict with risk gauge, detailed findings with severity filters and a technical-details switch. IT/EN interface. Talks to the engine through a local loopback bridge (`apkguard serve`); the Tauri shell and installers come with packaging.
- **M5** – Signature and permission views, HTML report with print-to-PDF, settings drawer (optional VirusTotal hash lookup, history), engine reputation module, standalone engine executable (PyInstaller) and the Tauri desktop shell with CI builds for Windows and Linux.
- **AI explanations (experimental)** – A "Connect Claude" button in Settings detects the user's own, already signed-in Claude Code and uses it to explain a report in plain language. APKGuard never touches credentials: it only asks the program for its status and runs it with every tool disabled, in an empty throw-away directory, one request at a time. Only an analysis summary is sent (never the file or its code), and the UI can show exactly what.
- **How it works (code understanding)** – Reads the APK's code (cross-references and the bundled decompiler; no Java needed) to show what the app can do, where, and what starts it (launcher, boot, incoming SMS...). Read-only, with an approximate decompiled view per feature and optional plain-language explanations through the user's own Claude Code. Code and strings are treated as untrusted data in every prompt.
- **Projects (ideas to reviewed changes)** – From an analysed app the owner (or someone with permission or a permissive licence) can create a project that holds a *specification* of what the app does, never its decompiled code. Anyone can add ideas in plain language and share them as a small file; Claude turns an idea into a proposed change; a person reviews the exact differences (with warnings for new web addresses, permissions and sensitive APIs) and approves or rejects it. Every approval can be undone. Apps judged harmful cannot be turned into projects. An experimental button asks Claude for a starter Android project (unbuilt, unverified).

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

## Running the UI (development)

```bash
# terminal 1: engine bridge (loopback only)
cd engine && apkguard serve --port 8765
# terminal 2: UI
cd app && npm install && npm run dev      # http://127.0.0.1:5173
npm test                                  # UI logic tests
```

## Desktop packaging

`packaging/build_engine.py` freezes the engine into a single executable, copied to `app/src-tauri/binaries/` under the name Tauri expects. The Tauri shell (`app/src-tauri`) starts it as a sidecar on a random loopback port and tells the UI which one. `.github/workflows/build.yml` runs the test suites and builds the Windows installer (NSIS). Linux packaging (deb, AppImage) is paused for now.

The optional VirusTotal check sends only the file's SHA-256, using a key you provide in Settings.


## Using Claude from APKGuard

The explanations run through the unmodified Claude Code the user installed and signed in to. This follows Anthropic's published rules for products that run Claude Code (see "Can customers offer Claude Code in their products?" and "Authentication and credential use" in Anthropic's Claude Code legal and compliance page): users sign in through Anthropic's own flow, usage is billed to the user's own plan, and APKGuard neither collects nor relays credentials. Before distributing the app publicly, confirm the arrangement with Anthropic, as that page recommends.

See [docs/TESTING.md](docs/TESTING.md) for how to get a build and what to try.
