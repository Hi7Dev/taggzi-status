<p align="center">
  <a href="https://status.taggzi.com"><img src="banner.svg" alt="Taggzi Status" width="100%"></a>
</p>

<p align="center">
  <a href="https://status.taggzi.com"><img alt="Taggzi status" src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2FHi7Dev%2Ftaggzi-status%2Fdata%2Fbadges%2Foverall.json&style=for-the-badge"></a>
  <a href="https://status.taggzi.com"><img alt="Uptime (90 days)" src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2FHi7Dev%2Ftaggzi-status%2Fdata%2Fbadges%2Fuptime.json&style=for-the-badge"></a>
  <a href="https://github.com/Hi7Dev/taggzi-status/actions/workflows/check.yml"><img alt="Checks" src="https://img.shields.io/github/actions/workflow/status/Hi7Dev/taggzi-status/check.yml?label=checks&style=for-the-badge&labelColor=0C0A09"></a>
</p>

<p align="center">
  <b><a href="https://status.taggzi.com">status.taggzi.com</a></b> · <a href="https://taggzi.com">taggzi.com</a> · <a href="https://taggzi.com/help/">Help centre</a> · <a href="mailto:support@taggzi.com">support@taggzi.com</a>
</p>

---

## Live status

<p align="center">
  <a href="https://status.taggzi.com"><img src="https://raw.githubusercontent.com/Hi7Dev/taggzi-status/data/status.svg" alt="Live status of every Taggzi system" width="820"></a>
</p>

<sub>This card and the badges above are regenerated every few minutes by the checker, so this page always shows the current state. The full page with 90-day history and incidents is at <a href="https://status.taggzi.com">status.taggzi.com</a>.</sub>

## What we monitor

| | System | What it means for you |
|---|---|---|
| <img src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2FHi7Dev%2Ftaggzi-status%2Fdata%2Fbadges%2Ftag_scans.json&label=&labelColor=0C0A09"> | **Tag scans** | Tapping or scanning a Taggzi tag opens the pet's profile |
| <img src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2FHi7Dev%2Ftaggzi-status%2Fdata%2Fbadges%2Fmanual_lookup.json&label=&labelColor=0C0A09"> | **Manual tag lookup** | Typing a tag's ID at taggzi.com/find-pet |
| <img src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2FHi7Dev%2Ftaggzi-status%2Fdata%2Fbadges%2Fcalling.json&label=&labelColor=0C0A09"> | **Private calling** | Finders can call owners from the pet page without sharing numbers |
| <img src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2FHi7Dev%2Ftaggzi-status%2Fdata%2Fbadges%2Fcommunity_alerts.json&label=&labelColor=0C0A09"> | **Community alerts** | Lost-pet alerts reach people nearby |
| <img src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2FHi7Dev%2Ftaggzi-status%2Fdata%2Fbadges%2Fapp_login.json&label=&labelColor=0C0A09"> | **App & login** | The Taggzi app and signing in |
| <img src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2FHi7Dev%2Ftaggzi-status%2Fdata%2Fbadges%2Fwebsite.json&label=&labelColor=0C0A09"> | **Website** | taggzi.com, the shop and order pages |
| <img src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2FHi7Dev%2Ftaggzi-status%2Fdata%2Fbadges%2Fpayments.json&label=&labelColor=0C0A09"> | **Payments** | Ordering tags and Taggzi Pro |
| <img src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2FHi7Dev%2Ftaggzi-status%2Fdata%2Fbadges%2Femail.json&label=&labelColor=0C0A09"> | **Email & support** | Account emails, alerts and support replies |
| <img src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2FHi7Dev%2Ftaggzi-status%2Fdata%2Fbadges%2Fssl.json&label=&labelColor=0C0A09"> | **Secure connection** | The padlock (SSL) certificates are valid and not about to expire |

## Is it just me?

If everything above is **operational**, Taggzi is working normally and the problem is most likely on your device or connection. Try refreshing, switching between Wi-Fi and mobile data, or updating the app. If you're still stuck, email **support@taggzi.com** and we'll help.

If something is **degraded** or has an **outage**, we already know about it and are working on it, so there's no need to report it.

## How it works

```mermaid
flowchart LR
    A["⏱ GitHub Actions<br/>every 5 minutes"] --> B["check.py<br/>9 systems · 20+ probes"]
    B -->|HTTPS, TCP, SSL| C["taggzi.com<br/>+ health report"]
    B --> D["data branch<br/>status · uptime · incidents"]
    D --> E["status.taggzi.com<br/>(GitHub Pages)"]
    D --> F["Live card + badges<br/>(this page)"]
    B -.->|outage / recovery| G["📱 WhatsApp alert<br/>to the team"]
```

- **Independent:** it runs on GitHub, not on Taggzi's own hosting, so it keeps working if taggzi.com is down. If even the status.taggzi.com address won't load, use the backup at **[hi7dev.github.io/taggzi-status-backup](https://hi7dev.github.io/taggzi-status-backup/)**, which doesn't rely on taggzi.com's DNS.
- **Honest:** a single failed check shows as *degraded*. It counts as an *outage* only when it fails twice in a row, and only confirmed outages count against uptime.
- **Safe:** the checks use side-effect-free lookups, so they never log fake tag scans or notify pet owners.
- **Private:** no customer data is checked, stored or published here.

<sub>Taggzi · smart NFC & QR pet ID tags · UK-based · <a href="https://taggzi.com">taggzi.com</a></sub>
