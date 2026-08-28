# mc-watch

Pollt alle 5 Minuten einen Minecraft-Server und schickt eine ntfy-Push-Nachricht,
sobald der Server von "leer" auf "besetzt" wechselt.

- `state.txt` — zuletzt gesehene Spielerzahl
- `verlauf.csv` — Protokoll aller Zustandsänderungen (`zeitpunkt;spieler_online;namen`)
- `.github/workflows/mc-watch.yml` — der Workflow

Serveradresse und ntfy-Topic liegen in den Repo-Secrets `MC_SERVER` und `NTFY_TOPIC`.
