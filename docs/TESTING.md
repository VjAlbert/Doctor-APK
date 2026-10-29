# Testing APKGuard

## Getting a build

Every push to `main` runs the workflow in `.github/workflows/build.yml`, and the run summary lists the
SHA-256 of the installer. Open the latest run under **Actions**, and download the artifact for your system:

- `apkguard-windows-latest` – NSIS installer (`.exe`).

Linux installers are paused for now (the engine and the interface still run on Linux; only the packaged
build is switched off).

Builds are unsigned, so Windows SmartScreen will warn: choose "More info" then "Run anyway".
The first start can take several seconds while the bundled analysis engine unpacks.

**Upgrading:** close APKGuard first. The installer also ends any leftover `apkguard-engine.exe`, which would
otherwise keep the old engine locked. To check what you are running, open *Settings*, section *About*: the
interface and the engine must show the same build.

## Optional: AI features

"Connect Claude" in Settings uses a Claude Code that **you** installed and signed in to
(`claude` in a terminal). APKGuard never sees your credentials. Without it, everything else works.

## What to try

1. **Analysis** – drop an APK. You should see the scan animation, a verdict and a risk gauge, then the
   tabs *Findings*, *Permissions*, *Signature* and *How it works*.
2. **Languages** – switch IT/EN: all texts, including the engine's findings, change.
3. **Report** – "Save report (HTML)" and "Print / PDF". *Known risk:* in the packaged app the file
   download and the print dialog have not been verified on every system.
4. **How it works** – a list of what the code can do, what starts it, and a read-only code view per
   feature (decompiled code is approximate).
5. **Connect Claude** (optional) – explanations in plain words; "Show what is sent" displays the exact
   text before you rely on it.

## Known limits

- The signature database covers F-Droid apps only (4,901 packages). Anything else shows "Cannot be
  verified"; an F-Droid app signed by its developer shows "different signature (other source)" as a
  low signal, because F-Droid often re-signs.
- Risk weights and thresholds are provisional. They were first tuned on small synthetic apps; the first
  real app analysed (an ad-supported IPTV player) exposed several false alarms, now fixed, and more are
  likely with other real apps. Many weak signals alone never produce "Do not install". Treat the score
  as a guide, not a measurement.
- Static analysis cannot see code downloaded after installation, and a clean result is never a
  guarantee of safety.
- The online VirusTotal check needs your own API key and has only been tested against simulated
  responses.

## Running the tests

```bash
cd engine && pip install -e ".[dev]" && PYTHONPATH=tests pytest        # needs a JDK (keytool, jarsigner)
cd app && npm ci && npm run typecheck && npm test
```
