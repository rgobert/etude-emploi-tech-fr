"""Pour les entreprises sans board détecté : devine le domaine et la page carrières,
puis cherche dans le HTML la signature d'un ATS (et l'identifiant du board)."""
import json, re, sys, unicodedata, concurrent.futures as cf
import requests

S = requests.Session()
S.headers["User-Agent"] = "Mozilla/5.0 (etude-emploi-tech-fr research)"
PATHS = ["", "/careers", "/jobs", "/carrieres", "/fr/carrieres", "/en/careers", "/recrutement", "/join-us", "/fr/recrutement", "/careers/", "/company/careers", "/jobs/"]
TLDS = ["com", "fr", "io", "ai", "eu", "co", "tech"]
SIG = {
    "welcomekit": r"welcomekit\.co|welcometothejungle\.com/(?:fr|en)/companies/([a-z0-9\-]+)",
    "teamtailor": r"([a-z0-9\-]+)\.teamtailor\.com",
    "lever": r"jobs\.(?:eu\.)?lever\.co/([a-zA-Z0-9\-]+)",
    "greenhouse": r"(?:boards|job-boards)(?:\.eu)?\.greenhouse\.io/(?:embed/job_board\?for=)?([a-zA-Z0-9\-]+)",
    "ashby": r"jobs\.ashbyhq\.com/([a-zA-Z0-9\-\.]+)",
    "smartrecruiters": r"(?:jobs|careers)\.smartrecruiters\.com/([a-zA-Z0-9\-]+)",
    "workable": r"apply\.workable\.com/([a-zA-Z0-9\-]+)",
    "recruitee": r"([a-z0-9\-]+)\.recruitee\.com",
    "personio": r"([a-z0-9\-]+)\.jobs\.personio\.(?:de|com)",
    "taleez": r"taleez\.com",
    "flatchr": r"flatchr\.io",
    "jobaffinity": r"jobaffinity\.fr",
    "workday": r"myworkdayjobs\.com",
    "successfactors": r"successfactors|jobs\.sap\.com",
    "hellowork_ats": r"hellowork\.com/.+?/entreprises|talentdetection|digitalrecruiters",
    "breezy": r"breezy\.hr",
    "join": r"join\.com/companies/([a-z0-9\-]+)",
    "jobteaser": r"jobteaser\.com/.+?/companies",
}


def base(name):
    n = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower().replace("’", "")
    w = re.findall(r"[a-z0-9]+", n)
    return list(dict.fromkeys(["".join(w), "-".join(w)] + (["".join(w[:-1])] if len(w) > 1 and w[-1] in {"group", "ai", "bio"} else [])))


def get(url):
    try:
        r = S.get(url, timeout=10, allow_redirects=True)
        if r.status_code == 200 and "html" in r.headers.get("content-type", ""):
            return r.url, r.text
    except Exception:
        pass
    return None, None


def scan(name):
    found, tried_home = {}, None
    for b in base(name):
        for tld in TLDS:
            home, h = get(f"https://{b}.{tld}")
            if not h:
                continue
            tried_home = tried_home or home
            # liens vers une page carrières dans la home
            links = set(re.findall(r'href="([^"]*(?:career|carriere|job|recrut|join)[^"]*)"', h, re.I))
            pages = [(home, h)]
            for p in list(links)[:6]:
                u = p if p.startswith("http") else home.rstrip("/") + "/" + p.lstrip("/")
                pages.append(get(u))
            for p in PATHS[1:5]:
                pages.append(get(home.rstrip("/") + p))
            for u, t in pages:
                if not t:
                    continue
                for k, rx in SIG.items():
                    m = re.search(rx, t, re.I)
                    if m:
                        found.setdefault(k, set()).add((m.group(1) if m.groups() and m.group(1) else "") + "@" + (u or ""))
            if found:
                return name, tried_home, {k: sorted(v)[:3] for k, v in found.items()}
    return name, tried_home, {}


def main():
    names = json.load(open(sys.argv[1]))
    with cf.ThreadPoolExecutor(max_workers=16) as ex:
        res = list(ex.map(scan, names))
    json.dump(res, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
    for r in res:
        print(r[0], "|", r[1], "|", r[2])


if __name__ == "__main__":
    main()
