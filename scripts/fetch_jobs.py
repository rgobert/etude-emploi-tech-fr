"""Télécharge et normalise les offres des boards ATS détectés.

Sortie : une ligne JSON par offre avec les champs communs
company, ats, slug, title, department, location, country_hint, remote_hint,
description (texte brut), url, published.
"""
import json, re, sys, html, concurrent.futures as cf
import xml.etree.ElementTree as ET
import requests

S = requests.Session()
S.headers["User-Agent"] = "etude-emploi-tech-fr/0.1 (research)"
T = 30


def strip(h):
    if not h:
        return ""
    h = html.unescape(h)
    h = re.sub(r"<(br|/p|/li|/h\d)[^>]*>", "\n", h, flags=re.I)
    h = re.sub(r"<[^>]+>", " ", h)
    return re.sub(r"[ \t\xa0]+", " ", html.unescape(h)).strip()


def greenhouse(slug):
    d = S.get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true", timeout=T).json()
    for x in d.get("jobs", []):
        yield dict(title=x.get("title"), department=", ".join(dd["name"] for dd in x.get("departments", [])),
                   location=(x.get("location") or {}).get("name", ""), description=strip(x.get("content")),
                   url=x.get("absolute_url"), published=x.get("updated_at"), remote_hint=None)


def lever(slug, host="api.lever.co"):
    d = S.get(f"https://{host}/v0/postings/{slug}?mode=json", timeout=T).json()
    for x in d:
        cat = x.get("categories") or {}
        locs = cat.get("allLocations") or [cat.get("location", "")]
        desc = strip(x.get("description")) + "\n" + "\n".join(
            strip(l.get("text")) + "\n" + strip(l.get("content")) for l in x.get("lists", [])) + "\n" + strip(x.get("additional"))
        yield dict(title=x.get("text"), department=cat.get("team") or cat.get("department") or "",
                   location=" | ".join([l for l in locs if l]), description=desc, url=x.get("hostedUrl"),
                   published=x.get("createdAt"), remote_hint=x.get("workplaceType"))


def ashby(slug):
    d = S.get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true", timeout=T).json()
    for x in d.get("jobs", []):
        locs = [x.get("location") or ""] + [s.get("location", "") for s in x.get("secondaryLocations", []) or []]
        addr = ((x.get("address") or {}).get("postalAddress") or {})
        yield dict(title=x.get("title"), department=x.get("department") or x.get("team") or "",
                   location=" | ".join([l for l in locs if l]), country_hint=addr.get("addressCountry"),
                   description=x.get("descriptionPlain") or strip(x.get("descriptionHtml")), url=x.get("jobUrl"),
                   published=x.get("publishedAt"), remote_hint=x.get("workplaceType") or ("Remote" if x.get("isRemote") else None))


def smartrecruiters(slug):
    off = 0
    while True:
        d = S.get(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100&offset={off}", timeout=T).json()
        for x in d.get("content", []):
            det = S.get(x["ref"], timeout=T).json() if x.get("ref") else {}
            sec = ((det.get("jobAd") or {}).get("sections") or {})
            desc = "\n".join(strip((sec.get(k) or {}).get("text")) for k in ("companyDescription", "jobDescription", "qualifications", "additionalInformation"))
            loc = x.get("location") or {}
            yield dict(title=x.get("name"), department=(x.get("department") or {}).get("label", ""),
                       location=", ".join(v for v in [loc.get("city"), loc.get("country")] if v), country_hint=loc.get("country"),
                       description=desc, url=f"https://jobs.smartrecruiters.com/{slug}/{x.get('id')}",
                       published=x.get("releasedDate"), remote_hint="Remote" if loc.get("remote") else None)
        off += 100
        if off >= d.get("totalFound", 0):
            break


def workable(slug):
    r = S.get(f"https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true", timeout=T)
    try:
        d = r.json()
    except Exception:
        d = {"jobs": []}
        token = None
        while True:
            body = {"query": "", "location": [], "department": [], "worktype": [], "remote": []}
            if token: body["token"] = token
            x = S.post(f"https://apply.workable.com/api/v3/accounts/{slug}/jobs", json=body, timeout=T).json()
            for jb in x.get("results", []):
                loc = jb.get("location") or {}
                det = S.get(f"https://apply.workable.com/api/v2/accounts/{slug}/jobs/{jb['shortcode']}", timeout=T).json()
                d["jobs"].append(dict(title=jb.get("title"), department=", ".join(jb.get("department") or []), city=loc.get("city"),
                    country=loc.get("country"), description=(det.get("description") or "") + (det.get("requirements") or ""),
                    url=f"https://apply.workable.com/{slug}/j/{jb['shortcode']}/", published_on=jb.get("published"),
                    telecommuting=jb.get("remote")))
            token = x.get("nextPage")
            if not token: break
    for x in d.get("jobs", []):
        yield dict(title=x.get("title"), department=x.get("department") or "",
                   location=", ".join(v for v in [x.get("city"), x.get("country")] if v), country_hint=x.get("country"),
                   description=strip(x.get("description")), url=x.get("url") or x.get("shortlink"),
                   published=x.get("published_on"), remote_hint="Remote" if x.get("telecommuting") else None)


def recruitee(slug):
    d = S.get(f"https://{slug}.recruitee.com/api/offers/", timeout=T).json()
    for x in d.get("offers", []):
        yield dict(title=x.get("title"), department=x.get("department") or "",
                   location=x.get("location") or "", country_hint=x.get("country_code"),
                   description=strip(x.get("description")) + "\n" + strip(x.get("requirements")),
                   url=x.get("careers_url"), published=x.get("published_at"),
                   remote_hint="Remote" if x.get("remote") else ("Hybrid" if x.get("hybrid") else None))


def teamtailor(slug):
    host = slug if "." in slug else f"{slug}.teamtailor.com"
    r = S.get(f"https://{host}/jobs.rss", timeout=T)
    root = ET.fromstring(r.content)
    ns = {"tt": "https://teamtailor.com/locations"}
    for it in root.iter("item"):
        locs = []
        for l in it.iter():
            if l.tag.endswith("city") and l.text:
                locs.append(l.text)
        country = [l.text for l in it.iter() if l.tag.endswith("country") and l.text]
        remote = [l.text for l in it.iter() if l.tag.lower().endswith("remotestatus") and l.text]
        dept = [l.text for l in it.iter() if l.tag.endswith("department") and l.text]
        yield dict(title=it.findtext("title"), department=", ".join(dept), location=" | ".join(locs),
                   country_hint=country[0] if country else None, description=strip(it.findtext("description")),
                   url=it.findtext("link"), published=it.findtext("pubDate"), remote_hint=remote[0] if remote else None)


def personio(slug, tld):
    r = S.get(f"https://{slug}.jobs.personio.{tld}/xml", timeout=T)
    root = ET.fromstring(r.content)
    for p in root.iter("position"):
        desc = "\n".join(strip(v.findtext("value")) for v in p.iter("jobDescription"))
        yield dict(title=p.findtext("name"), department=p.findtext("department") or "",
                   location=p.findtext("office") or "", description=desc,
                   url=f"https://{slug}.jobs.personio.{tld}/job/{p.findtext('id')}", published=p.findtext("createdAt"),
                   remote_hint=None)


FETCH = {"greenhouse": greenhouse, "lever": lever, "lever_eu": lambda s: lever(s, "api.eu.lever.co"),
         "ashby": ashby, "smartrecruiters": smartrecruiters, "workable": workable, "recruitee": recruitee,
         "teamtailor": teamtailor, "personio_de": lambda s: personio(s, "de"), "personio_com": lambda s: personio(s, "com")}


def run(board):
    company, ats, slug = board
    out = []
    try:
        for job in FETCH[ats](slug):
            job.update(company=company, ats=ats, slug=slug)
            job.setdefault("country_hint", None)
            out.append(job)
    except Exception as e:
        print("ERR", company, ats, slug, e, file=sys.stderr)
    return out


def main():
    boards = json.load(open(sys.argv[1]))  # [[company, ats, slug], ...]
    with cf.ThreadPoolExecutor(max_workers=12) as ex, open(sys.argv[2], "w") as f:
        n = 0
        for jobs in ex.map(run, boards):
            for jb in jobs:
                f.write(json.dumps(jb, ensure_ascii=False) + "\n")
                n += 1
    print(n, "offres écrites")


if __name__ == "__main__":
    main()
