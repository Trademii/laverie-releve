#!/usr/bin/env python3
"""Releve des machines TouchNPay -> CSV. Lit l'URL dans DATA_DIR/url.txt, ecrit dans DATA_DIR."""
import csv, json, os, sys, time, urllib.request
from datetime import datetime, timezone

D = os.environ.get("DATA_DIR", ".")
CSV, ETAT, JOURNAL = (os.path.join(D, n) for n in ("comptage_speedqueen.csv", "comptage_etat.json", "comptage_journal.txt"))
now = datetime.now(timezone.utc)
now_s = now.strftime("%Y-%m-%dT%H:%M:%SZ")

def journal(msg):
    with open(JOURNAL, "a", encoding="utf-8") as f:
        f.write(f"{now_s} {msg}\n")

def norm(s):
    d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + f"{d.microsecond // 1000:03d}Z"

url = open(os.path.join(D, "url.txt"), encoding="utf-8").read().strip()
data = None
for essai in range(3):
    try:
        req = urllib.request.Request(url, headers={"Origin": "https://gad.touchnpay.fr", "Cache-Control": "no-cache"})
        data = json.load(urllib.request.urlopen(req, timeout=30))
        break
    except Exception as e:
        err = e
        time.sleep(5)
if data is None:
    journal(f"ERREUR {err}")
    sys.exit(0)

etat = {}
if os.path.exists(ETAT):
    etat = json.load(open(ETAT, encoding="utf-8"))
premier = not etat
dernier = etat.pop("_releve", None)
# trou = pas de releve depuis plus de 25 min (ou tout premier releve)
trou = True if dernier is None else (now - datetime.fromisoformat(dernier.replace("Z", "+00:00"))).total_seconds() > 25 * 60

neuf = not os.path.exists(CSV)
n = 0
with open(CSV, "a", encoding="utf-8", newline="") as f:
    if neuf:
        f.write("machine;type;prix_eur;demarrage_utc;releve_utc;statut\n")
    for m in data:
        k, st = str(m["machine_name"]), m.get("started_at")
        if not st:
            continue
        st = norm(st)
        if etat.get(k) != st:
            if premier and k not in etat and m["machine_type"] != "sec":
                statut = "base"
            else:
                statut = "trou" if trou else "ok"
            prix = ("%.2f" % (float(m["machine_price"]) / 100)).rstrip("0").rstrip(".")
            f.write(f"{k};{m['machine_type']};{prix};{st};{now_s};{statut}\n")
            etat[k] = st
            n += 1
etat["_releve"] = now_s
json.dump(etat, open(ETAT, "w", encoding="utf-8"), indent=1)
journal(f"OK {n}")
