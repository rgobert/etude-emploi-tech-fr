"""Normalise, dédoublonne et classe les offres (rôle, contrat, géo, remote, compétences)."""
import json, re, sys, hashlib, collections, unicodedata

def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", s).strip()

# ---------- contrat ----------
INTERN = re.compile(r"\b(intern|internship|stage|stagiaire|apprenti|apprentice|apprenticeship|alternance|alternant|work[- ]study|working student|v\.?i\.?e\.?|graduate program|thesis|these|cifre|phd)\b")
FREELANCE = re.compile(r"\b(freelance|contractor)\b")

# ---------- rôles (ordre = priorité) ----------
ROLES = [
    ("Recrutement tech", r"\b(recruit|recruteu|recrutement|talent acquisition|sourcer|sourcing)"),
    ("Product design", r"\b(product design|design manager|design ops|design director|product designer|ux|ui designer|ui/ux|ux/ui|design lead|head of design|designer produit|design system|user research|ux research)"),
    ("Product management", r"\b(product builder|product manager|product owner|head of product|vp product|chief product|cpo|product lead|group product|product director|directeur produit|chef de produit|\bpm\b|\bpo\b|product management|product ops)"),
    ("FDE / déploiement IA", r"\b(forward[- ]deployed|deployment strategist|deployment engineer|solutions? engineer|solutions? architect|sales engineer|presales|pre-sales|avant[- ]vente|customer engineer|implementation engineer|integration engineer|technical account|ai architect|ai deployment)"),
    ("Sécurité", r"\b(security|securite|cyber|soc analyst|pentest|rssi|ciso|appsec|detection engineer|threat)"),
    ("Data / IA / ML", r"\b(product analyst|data scien|data engineer|data analyst|analytics engineer|machine learning|\bml\b|mlops|\bai\b|\bia\b|research scientist|research engineer|llm|nlp|computer vision|deep learning|applied scientist|data architect|bi |business intelligence|data platform|data lead|head of data|data manager|statistician|actuar)"),
    ("DevOps / Cloud / SRE", r"\b(devops|sre|site reliability|cloud|platform engineer|infrastructure|infra |systems? engineer|network engineer|ingenieur systeme|sysadmin|administrat(eur|or) syst|it ops|it engineer)"),
    ("QA / Test", r"\b(qa|quality assurance|test automation|testeur|tester|test engineer|sdet|software quality)"),
    ("Mobile", r"\b(ios|android|mobile|react native|flutter|kotlin multiplatform)"),
    ("Front-end", r"\b(front[- ]?end|frontend|react developer|vue|angular|web developer|integrateur web)"),
    ("Back-end", r"\b(back[- ]?end|backend|api engineer|java developer|python developer|golang|php|ruby|elixir|node)"),
    ("Fullstack", r"\b(full[- ]?stack|fullstack)"),
    ("Management engineering", r"\b(ctpo|technical lead|engineering manager|head of engineering|vp engineering|vp of engineering|cto|tech lead|lead developer|lead dev|staff engineer|principal engineer|directeur technique|chief technology|engineering director|director of engineering)"),
    ("Software (générique)", r"\b(software|developpeur|developer|developpement|engineer.*(software|backend|product)|ingenieur (logiciel|developpement|informatique)|programmer|game developer|gameplay|unity developer|c\+\+|embedded software|logiciel embarque|firmware|scientific software|engineer\b(?!.*(mechanic|electr|process|hardware|manufactur|battery|chemi|civil|structur|gnc|propulsion|thermal|optic|photon|rf |test bench|industrial|quality|maintenance|automation|materials|cell|pack)))"),
    ("Ingénierie hors logiciel", r"\b(engineer|ingenieur|technicien|technician|scientist|chercheur|r&d|physicist|chemist|biolog|electroni|mecani|mechanical|hardware|process|manufactur|battery|propulsion|gnc|photon|optic|quantum|cleanroom|fab|clinical|pharma)"),
]
ROLES = [(n, re.compile(r)) for n, r in ROLES]
TECH = {"Chef de projet tech / TPM", "Recrutement tech", "Product design", "Product management", "FDE / déploiement IA", "Sécurité", "Data / IA / ML",
        "DevOps / Cloud / SRE", "QA / Test", "Mobile", "Front-end", "Back-end", "Fullstack", "Management engineering", "Software (générique)"}
ENG = {"Sécurité", "DevOps / Cloud / SRE", "QA / Test", "Mobile", "Front-end", "Back-end", "Fullstack", "Management engineering", "Software (générique)", "FDE / déploiement IA"}

NONTECH_HINT = re.compile(r"\b(revops|sales|account executive|business develop|sdr|bdr|marketing|growth marketing|content|community|brand|communication|finance|comptab|accountant|controller|legal|juriste|lawyer|counsel|hr |people|rh |payroll|paie|office|customer success|customer support|support specialist|care|charge de clientele|relation client|operations manager|ops |logisti|supply|procurement|achat|aide a domicile|auxiliaire|assistant|commercial|vendeu|chef de projet commercial|general application|candidature spontanee)")

HARDWARE = re.compile(r"\b(mechanic|mecani|electroni|electrical|hardware|process|manufactur|battery|batterie|cell\b|pack|chemi|civil|structur|gnc|propulsion|thermal|thermique|optic|photon|rf\b|test bench|industrial|industriali|maintenance|materials|materiaux|cleanroom|lithograph|nanofab|superconduct|yield|characteri|wafer|3d integration|integration & yield|qara|regulatory|clinical|biolog|pharma|mission|orbital|satellite|spacecraft|avionic|aero|hse|hygiene|safety|methodes|methods|gigafactory|production line|electrode|mes\b|deposition|etch|equipment|failure analysis|coating|mixing|quality engineer)")
TECHWORD = re.compile(r"\b(engineer|ingenieur|developer|developpeur|dev\b|architect|analyst|scientist|sre|devops)")
BIZDEV = re.compile(r"business develop|developpeur commercial|developpeur d.affaires|developer relations|devrel|sdr\b|bdr\b")

def role_of(title, dept):
    t = norm(title)
    hw = bool(HARDWARE.search(t))
    if re.search(r"game designer|level designer|game artist|\\b3d artist|2d artist|motion designer|animator|vfx|technical artist|brand designer|graphic designer", t):
        return "Créa / game design"
    if re.search(r"technical project manager|chef de projet (technique|it|informatique|digital|si)|program manager|delivery manager|scrum master|agile coach|technical program", t):
        return "Chef de projet tech / TPM"
    if re.search(r"general application|candidature spontanee|spontaneous application|open application", t):
        return "Candidature spontanée"
    # le recrutement n'est 'tech' que s'il cible des profils tech (sinon : RH)
    for name, rx in ROLES:
        if rx.search(t):
            if name == "Recrutement tech" and not re.search(r"tech|engineer|it\b|software|product|data", t):
                return "Autres (business, ops, support…)"
            if name == "Data / IA / ML" and NONTECH_HINT.search(t) and not re.search(r"engineer|scien|analyst|developer|research", t):
                continue
            if name == "Mobile" and not TECHWORD.search(t):
                continue
            if name == "Sécurité" and (NONTECH_HINT.search(t) or hw or not re.search(r"engineer|ingenieur|analyst|architect|ciso|rssi|cyber|pentest|soc|appsec|grc|director of (cyber|security)", t)):
                continue
            if name in ("Software (générique)", "FDE / déploiement IA", "DevOps / Cloud / SRE", "QA / Test") and hw:
                continue
            if name in ("Software (générique)", "Back-end", "Front-end", "Fullstack") and (BIZDEV.search(t) or "revops" in t):
                return "Autres (business, ops, support…)"
            if name == "DevOps / Cloud / SRE" and NONTECH_HINT.search(t) and "engineer" not in t:
                continue
            if name == "FDE / déploiement IA" and re.search(r"\b(mechanical|hardware|battery|process)\b", t):
                continue
            return name
    return "Autres (business, ops, support…)"

# ---------- géo ----------
FR_CITY = {
    "Paris / IDF": r"paris|ile[- ]de[- ]france|idf|la defense|boulogne|montrouge|saclay|palaiseau|massy|clichy|nanterre|levallois|issy|puteaux|aubervilliers|saint[- ]denis|malakoff|neuilly|vincennes|montreuil|courbevoie|rueil|velizy|orsay|saint[- ]ouen|ivry|guyancourt|versailles|cergy|evry|marne|noisy|pantin|arcueil|gentilly|bagnolet|creteil|roissy|fontenay|meudon|suresnes|chatillon|sevres|antony|rungis|villejuif|wissous|les ulis|plessis",
    "Lyon / AURA": r"lyon|villeurbanne|grenoble|annecy|clermont|saint[- ]etienne|chambery|valence|ecully|limonest|tassin|bron|meylan|auvergne|rhone",
    "Toulouse": r"toulouse|labege|blagnac",
    "Bordeaux": r"bordeaux|merignac|pessac",
    "Nantes / Rennes / Ouest": r"nantes|rennes|brest|angers|le mans|tours|saint[- ]herblain|vannes|lorient|caen|rouen",
    "Lille / Nord": r"lille|roubaix|tourcoing|villeneuve|dunkerque|bourbourg|hauts[- ]de[- ]france|amiens|arras",
    "Sud-Est (Marseille, Nice, Montpellier…)": r"marseille|aix|nice|sophia|montpellier|toulon|avignon|nimes|cannes|grasse|antibes|perpignan",
    "Autres villes France": r"strasbourg|metz|nancy|reims|dijon|besancon|orleans|poitiers|limoges|la rochelle|pau|bayonne|mulhouse|troyes|mont-de-marsan|calais|niort|chartres|montauban|beziers",
}
FR_CITY = {k: re.compile(r"\b(" + v + r")") for k, v in FR_CITY.items()}
FR_ANY = re.compile(r"\b(france|fr\b|french|all france|toute la france)")
REMOTE_TXT = re.compile(r"full[- ]?remote|fully remote|100 ?% (remote|teletravail)|remote first|remote-first|teletravail (complet|total|integral)|remote \(|\bremote\b")

def geo_of(job):
    loc = norm(job.get("location")) + " " + norm(str(job.get("country_hint") or ""))
    zones = [k for k, rx in FR_CITY.items() if rx.search(loc)]
    fr = bool(zones) or bool(FR_ANY.search(loc))
    return fr, (zones[0] if zones else ("France (non précisé / remote)" if fr else "Hors France"))

def remote_of(job):
    h = norm(str(job.get("remote_hint") or ""))
    loc = norm(job.get("location"))
    if h in ("remote", "fully", "fully_remote", "remote_ok") or "fully" in h or (h == "remote"):
        return "Full remote"
    if "hybrid" in h:
        return "Hybride"
    if re.search(r"full[- ]?remote|fully remote|\bremote\b|teletravail", loc):
        return "Full remote"
    if re.search(r"hybrid", loc):
        return "Hybride"
    if h in ("onsite", "on-site", "on_site", "none", "in office", "office"):
        return "Sur site"
    return "Non précisé"

# ---------- compétences ----------
SKILLS = {
    "LLM": r"\bllms?\b|large language model",
    "IA générative / GenAI": r"gen ?ai|generative ai|ia generative|intelligence artificielle generative",
    "Agents IA": r"\b(ai|llm|ia) agents?\b|agentic|agents? (ia|ai)\b|multi-agent",
    "RAG": r"\brag\b|retrieval[- ]augmented",
    "Evals": r"\bevals?\b|llm evaluation",
    "MCP": r"\bmcp\b|model context protocol",
    "Claude / Anthropic": r"\bclaude\b(?! (baillet|bernard|monet|debussy|chappe|guillon|regaud|vellefaux|decaen))|anthropic (api|solutions|sdk)|anthropic's",
    "OpenAI / ChatGPT / GPT": r"openai|chatgpt|\bgpt-?\d|\bgpt\b",
    "Mistral": r"\bmistral\b",
    "Cursor": r"\bcursor\b",
    "GitHub Copilot": r"\bcopilot\b",
    "Python": r"\bpython\b",
    "Java": r"\bjava\b(?!script)",
    "Kotlin": r"\bkotlin\b",
    "Swift": r"\bswift\b|swiftui",
    "TypeScript": r"typescript",
    "JavaScript": r"javascript",
    "React": r"\breact\b",
    "React Native": r"react native",
    "Flutter": r"\bflutter\b",
    "Node.js": r"node\.?js|\bnode\b",
    "Go": r"\bgolang\b|\bgo\b(?= ?(lang|,|/| and| et|\)))",
    "Rust": r"\brust\b",
    "PHP": r"\bphp\b|symfony|laravel",
    "Ruby / Rails": r"\bruby\b|ruby on rails|\brails\b",
    "Scala": r"\bscala\b",
    "C / C++": r"c\+\+|\bc/c\+\+",
    "SQL": r"\bsql\b|postgres|mysql",
    "Kubernetes": r"kubernetes|\bk8s\b",
    "Terraform": r"terraform",
    "AWS": r"\baws\b|amazon web services",
    "GCP": r"\bgcp\b|google cloud",
    "Azure": r"\bazure\b",
    "Figma": r"\bfigma\b",
    "Jira": r"\bjira\b",
    "Amplitude / Mixpanel": r"amplitude|mixpanel",
}
SKILLS = {k: re.compile(v) for k, v in SKILLS.items()}

ENGLISH_TITLE = re.compile(r"\b(engineer|developer|manager|lead|head|senior|junior|intern|designer|analyst|scientist|specialist|executive|officer|owner|staff|principal)\b")
FRENCH_TITLE = re.compile(r"\b(ingenieur|developpeur|chef|responsable|charge|stagiaire|alternant|alternance|stage|directeur|directrice|concepteur|technicien|h/f|f/h)\b")


def main():
    raw = [json.loads(l) for l in open(sys.argv[1])]
    # --- retrait du texte standard (boilerplate) répété dans les offres d'une même entreprise ---
    by_c = collections.defaultdict(list)
    for j in raw:
        by_c[j["company"]].append(j)
    for c, js in by_c.items():
        if len(js) < 4:
            continue
        cnt = collections.Counter()
        for j in js:
            parts = {p.strip() for p in re.split(r"\n+|(?<=[.!?])\s+", norm(j.get("description"))) if len(p.strip()) > 40}
            cnt.update(parts)
        bp = {p for p, n in cnt.items() if n >= max(3, 0.5 * len(js))}
        for j in js:
            parts = [p.strip() for p in re.split(r"\n+|(?<=[.!?])\s+", norm(j.get("description")))]
            j["description_clean"] = "\n".join(p for p in parts if p not in bp)
    seen, out = set(), []
    for j in raw:
        key = (j["company"], norm(j.get("title")), norm(j.get("location")))
        if key in seen:
            continue
        seen.add(key)
        t = norm(j.get("title"))
        fr, zone = geo_of(j)
        role = role_of(j.get("title"), j.get("department"))
        desc = j.get("description_clean") if j.get("description_clean") is not None else norm(j.get("description"))
        skills = [k for k, rx in SKILLS.items() if rx.search(desc) or rx.search(t)]
        if j["company"] == "Mistral AI" and "Mistral" in skills:
            skills.remove("Mistral")
        out.append(dict(
            company=j["company"], ats=j["ats"], title=j.get("title"), location=j.get("location"), url=j.get("url"),
            published=j.get("published"), france=fr, zone=zone, role=role, tech=role in TECH, eng=role in ENG,
            contract="Stage / alternance" if INTERN.search(t) else ("Freelance" if FREELANCE.search(t) else "CDI / CDD"),
            remote=remote_of(j), skills=skills, desc_len=len(desc),
            title_lang="FR" if FRENCH_TITLE.search(t) else ("EN" if ENGLISH_TITLE.search(t) else "?"),
        ))
    json.dump(out, open(sys.argv[2], "w"), ensure_ascii=False)
    print(len(raw), "brutes ->", len(out), "après dédoublonnage")


if __name__ == "__main__":
    main()
