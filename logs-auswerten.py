#!/usr/bin/env python3
"""Wertet Minecraft-Server-Logs rueckwirkend aus.

Aufruf:  python logs-auswerten.py <ordner-mit-logs>

Liest *.log und *.log.gz, sucht Join-/Leave-Ereignisse und gibt aus,
wer den Server wie lange genutzt hat. Schreibt zusaetzlich
verlauf-rueckwirkend.csv im gleichen Format wie verlauf.csv.
"""
import sys, os, re, gzip, io
from datetime import datetime, timedelta
from collections import defaultdict

JOIN = re.compile(r'\[(\d\d):(\d\d):(\d\d)\].*?: (\S+) joined the game')
LEAVE = re.compile(r'\[(\d\d):(\d\d):(\d\d)\].*?: (\S+) left the game')
LOST = re.compile(r'\[(\d\d):(\d\d):(\d\d)\].*?: (\S+) \(/[\d.]+:\d+\) lost connection')
DATUM = re.compile(r'(\d{4})-(\d\d)-(\d\d)')


def oeffnen(pfad):
    if pfad.endswith('.gz'):
        return io.TextIOWrapper(gzip.open(pfad, 'rb'), encoding='utf-8', errors='replace')
    return io.open(pfad, encoding='utf-8', errors='replace')


def tag_von(pfad):
    """Datum aus dem Dateinamen, sonst Aenderungsdatum der Datei."""
    m = DATUM.search(os.path.basename(pfad))
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    ts = datetime.fromtimestamp(os.path.getmtime(pfad))
    return datetime(ts.year, ts.month, ts.day)


def main(ordner):
    dateien = sorted(
        os.path.join(ordner, f) for f in os.listdir(ordner)
        if f.endswith('.log') or f.endswith('.log.gz')
    )
    if not dateien:
        sys.exit('Keine .log/.log.gz-Dateien in %s' % ordner)

    ereignisse = []
    for pfad in dateien:
        tag = tag_von(pfad)
        vorher = None
        with oeffnen(pfad) as fh:
            for zeile in fh:
                for regex, art in ((JOIN, 'join'), (LEAVE, 'leave'), (LOST, 'lost')):
                    m = regex.search(zeile)
                    if not m:
                        continue
                    h, mi, s, name = int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4)
                    zeit = tag + timedelta(hours=h, minutes=mi, seconds=s)
                    # Log laeuft ueber Mitternacht weiter -> Tag hochzaehlen
                    if vorher and zeit < vorher:
                        tag += timedelta(days=1)
                        zeit += timedelta(days=1)
                    vorher = zeit
                    ereignisse.append((zeit, art, name))

    ereignisse.sort(key=lambda e: e[0])
    if not ereignisse:
        sys.exit('Keine Join-/Leave-Zeilen gefunden. Anderes Log-Format?')

    offen, sitzungen = {}, []
    for zeit, art, name in ereignisse:
        if art == 'join':
            if name in offen:  # Join ohne vorheriges Leave (Absturz/Neustart)
                sitzungen.append((name, offen.pop(name), None))
            offen[name] = zeit
        elif art == 'leave' and name in offen:
            sitzungen.append((name, offen.pop(name), zeit))
    for name, start in offen.items():
        sitzungen.append((name, start, None))  # noch online / Log endet

    # Zusammenfassung
    dauer = defaultdict(timedelta)
    anzahl = defaultdict(int)
    for name, start, ende in sitzungen:
        anzahl[name] += 1
        if ende:
            dauer[name] += ende - start

    logtage = sorted({tag_von(p).date() for p in dateien})
    a, b = logtage[0], logtage[-1]
    tage = (b - a).days + 1
    print('Log-Abdeckung: %s bis %s  (%d Kalendertage, %d mit Logdatei)'
          % (a, b, tage, len(logtage)))
    print('Sitzungen:  %d insgesamt' % len(sitzungen))
    print()
    print('%-20s %8s %14s %12s' % ('Spieler', 'Logins', 'Spielzeit', 'pro Tag'))
    for name in sorted(dauer, key=lambda n: -dauer[n]):
        std = dauer[name].total_seconds() / 3600
        print('%-20s %8d %11.1f h %9.1f min' % (name, anzahl[name], std, std * 60 / tage))

    ohne_login = sorted({(z, n) for z, art, n in ereignisse
                         if art == 'lost' and n not in dauer and n not in anzahl})
    if ohne_login:
        print()
        print('Verbindungen OHNE Betreten der Welt (Scan/Abbruch/Whitelist):')
        for z, n in ohne_login:
            print('  %s  %s' % (z.strftime('%Y-%m-%d %H:%M:%S'), n))

    aktiv = len({s[1].date() for s in sitzungen})
    print()
    print('Tage mit mindestens einem Login: %d von %d (%.0f %%)' % (aktiv, tage, 100.0 * aktiv / tage))

    with io.open('verlauf-rueckwirkend.csv', 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('zeitpunkt;ereignis;spieler\n')
        for zeit, art, name in ereignisse:
            fh.write('%s;%s;%s\n' % (zeit.strftime('%Y-%m-%dT%H:%M:%S'), art, name))
    print('Rohdaten geschrieben: verlauf-rueckwirkend.csv (%d Ereignisse)' % len(ereignisse))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
