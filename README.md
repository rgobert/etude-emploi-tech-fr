# etude-emploi-tech-fr

Baromètre trimestriel de l'emploi tech en France (Romain Gobert).
Méthode : voir `METHODE.md`. Résultats de l'édition pilote : `RESULTATS_PILOTE_2026-11.md`.

Relancer une édition :
    pip install requests
    python3 scripts/probe_ats.py data/<edition>/companies.json data/<edition>/ats_probe.json
    # valider les homonymes, puis construire boards.json
    python3 scripts/fetch_jobs.py data/<edition>/boards.json data/<edition>/jobs_raw.jsonl
    python3 scripts/classify.py data/<edition>/jobs_raw.jsonl data/<edition>/jobs_classified.json
Séries Indeed : git clone https://github.com/hiring-lab/job_postings_tracker

Données publiées par édition (`data/AAAA-MM/`) : liste des entreprises, boards ATS validés, offres classées (métadonnées uniquement : entreprise, titre, lieu, rôle, compétences détectées, lien), séries Indeed mensuelles.
Le texte brut des offres n'est pas republié (il se régénère avec `fetch_jobs.py`).

Sources : Indeed Hiring Lab (CC BY 4.0), flux publics des ATS des entreprises, dossier de presse French Tech Next40/120 (15/06/2026).
