# Taggzi Status

Live status page for [Taggzi](https://taggzi.com): **https://status.taggzi.com**

It is hosted on GitHub Pages and checked every 5 minutes by GitHub Actions, so it keeps working even when taggzi.com or its hosting is down.

- `check.py` runs the checks in `config.json` and writes the results to the `data` branch (`status.json`, `uptime.json`, `incidents.json`).
- `index.html` reads those files live, so the site never needs rebuilding.
- Tag checks use side-effect-free lookups, so no scans are logged and no owners are notified.
- WhatsApp alerts go out on confirmed outages and recoveries, if the `CALLMEBOT_PHONE` / `CALLMEBOT_APIKEY` secrets are set.
