"""Probe public ATS job-board endpoints for each French Tech 120 company.

Pour chaque entreprise, génère des slugs candidats et teste les API publiques
des principaux ATS. Ne garde un match que si le board contient au moins une offre.
"""
import json, re, sys, unicodedata, concurrent.futures as cf
import requests

S = requests.Session()
S.headers["User-Agent"] = "etude-emploi-tech-fr/0.1 (research)"
TIMEOUT = 12


def slugs(name):
    n = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    n = n.replace("&", "and").replace("’", "").replace("'", "")
    words = re.findall(r"[a-z0-9]+", n)
    cands = {"".join(words), "-".join(words)}
    if words and words[-1] in {"group", "ai", "technology", "labs"} and len(words) > 1:
        cands |= {"".join(words[:-1]), "-".join(words[:-1])}
    if "and" in words:
        w2 = [w for w in words if w != "and"]
        cands |= {"".join(w2), "-".join(w2)}
    return [c for c in cands if c]


def j(url):
    try:
        r = S.get(url, timeout=TIMEOUT)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


def txt(url):
    try:
        r = S.get(url, timeout=TIMEOUT)
        return r.text if r.status_code == 200 else None
    except Exception:
        return None


def probe(slug):
    hits = []
    d = j(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs")
    if d and d.get("jobs"):
        hits.append(("greenhouse", slug, len(d["jobs"])))
    for host in ("api.lever.co", "api.eu.lever.co"):
        d = j(f"https://{host}/v0/postings/{slug}?mode=json")
        if isinstance(d, list) and d:
            hits.append(("lever" if host == "api.lever.co" else "lever_eu", slug, len(d)))
    d = j(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
    if d and d.get("jobs"):
        hits.append(("ashby", slug, len(d["jobs"])))
    d = j(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=1")
    if d and d.get("totalFound"):
        hits.append(("smartrecruiters", slug, d["totalFound"]))
    d = j(f"https://apply.workable.com/api/v1/widget/accounts/{slug}")
    if d and d.get("jobs"):
        hits.append(("workable", slug, len(d["jobs"])))
    d = j(f"https://{slug}.recruitee.com/api/offers/")
    if d and d.get("offers"):
        hits.append(("recruitee", slug, len(d["offers"])))
    t = txt(f"https://{slug}.teamtailor.com/jobs.rss")
    if t and "<item>" in t:
        hits.append(("teamtailor", slug, t.count("<item>")))
    for tld in ("de", "com"):
        t = txt(f"https://{slug}.jobs.personio.{tld}/xml")
        if t and "<position>" in t:
            hits.append((f"personio_{tld}", slug, t.count("<position>")))
    return hits


def main():
    comps = json.load(open(sys.argv[1]))
    tasks = {}
    with cf.ThreadPoolExecutor(max_workers=24) as ex:
        for c in comps:
            for s in slugs(c["name"]):
                tasks[ex.submit(probe, s)] = c["name"]
        res = {}
        for f in cf.as_completed(tasks):
            res.setdefault(tasks[f], []).extend(f.result())
    for c in comps:
        c["ats_hits"] = res.get(c["name"], [])
    json.dump(comps, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
    found = sum(1 for c in comps if c["ats_hits"])
    print(f"{found}/{len(comps)} entreprises avec au moins un board détecté")
    for c in comps:
        print(c["name"], c["ats_hits"])


if __name__ == "__main__":
    main()
