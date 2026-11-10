# Baromètre emploi tech France : méthode

Étude trimestrielle du marché de l'emploi tech en France, inspirée du
« State of the tech job market » de Lenny's Newsletter (TrueUp + Live Data Technologies).
Auteur : Romain Gobert. Édition pilote : 10 novembre 2026.

## 1. Ce que fait Lenny (référence)

- Deux sources croisées : les **offres** (TrueUp, plus de 9 000 entreprises tech
  et startups, conseil et entreprises non tech exclus) et les **embauches réelles**
  (Live Data Technologies, changements de poste aux US). L'écart entre les deux est
  lui-même un enseignement.
- Une taxonomie fixe d'une dizaine de rôles (PM, eng, design, UXR, data, growth,
  recruteurs, FDE…) et des indicateurs stables : volumes, évolution vs points de
  repère (creux 2023, pic 2022), parts, ratios (PM:design), part de la Bay Area,
  part de remote, top des compétences citées dans les offres.
- 7 enseignements, chacun avec un titre en une phrase, 1 ou 2 graphiques et son
  interprétation. Les théories sont présentées comme telles et les partenaires
  data sont remerciés.
- Limites connues : il compte des offres et non des embauches, la méthode de
  dédoublonnage est opaque, et on lui reproche les « offres fantômes ».

## 2. Nos sources (3 couches)

| Couche | Source | Usage | Licence / accès |
|---|---|---|---|
| Tendance longue | Indeed Hiring Lab, `github.com/hiring-lab/job_postings_tracker` | Indice quotidien des offres par secteur (base 100 = 1er février 2020, corrigé des variations saisonnières, moyenne mobile 7 jours), FR vs US / DE / GB | CC BY 4.0, citer « Indeed Hiring Lab » |
| Haut du marché tech (l'équivalent de TrueUp) | Flux publics des ATS des entreprises de la **French Tech 120** (promotion 2026, dossier de presse du 15/06/2026) | Photo des offres : rôles, compétences, géographie, remote, contrats | API publiques de job board (Greenhouse, Lever, Ashby, SmartRecruiters, Workable, Recruitee, Teamtailor RSS, Personio XML) |
| Marché large | API France Travail « Offres d'emploi v2 » | Volumes, ESN vs éditeurs, offres ouvertes aux débutants, régions, salaires | Compte francetravail.io (À FAIRE). Seules les offres partenaires consenties sont exposées |
| Vérification | Chiffres publiés Apec, HelloWork, Numeum, Insee, Banque de France | Cohérence des ordres de grandeur | Citation |

**Règles éthiques et juridiques** : pas de scraping de LinkedIn, ni de Welcome to the
Jungle sans partenariat, ni d'exploitation de clés d'API embarquées dans les pages
(par exemple l'Algolia des sites Welcome Kit). On n'utilise que des API publiques
prévues pour la diffusion des offres. User-Agent identifié.

## 3. Pipeline (dossier `scripts/`)

1. `companies.json` : les 120 lauréats, extraits de l'annexe 2 du dossier de presse.
2. `probe_ats.py` : génère des identifiants candidats et interroge les API publiques
   des ATS. Un board n'est retenu que s'il contient au moins une offre.
3. **Validation manuelle des homonymes.** Écartés en novembre 2026 : Latitude et
   Metron (boards américains), Homa (magasin portugais), Shift/ashby, Swan/ashby,
   Sweep/ashby, Alice & Bob/personio.
4. `detect_careers.py` : pour les entreprises restantes, lecture de la page
   carrières et détection de la signature de l'ATS (domaines corrigés à la main
   si besoin).
5. `fetch_jobs.py` : téléchargement et normalisation (titre, service, lieu, pays,
   remote, description, URL, date).
6. `classify.py` :
   - dédoublonnage (entreprise, titre, lieu) ;
   - **retrait du texte standard** : une phrase présente dans au moins 50 % des
     offres d'une entreprise (avec un minimum de 3 offres) est exclue avant de
     chercher les compétences ;
   - rôle (règles sur l'intitulé, par ordre de priorité, avec exclusion du matériel
     et du hors-logiciel), contrat, zone géographique, remote, compétences, langue
     de l'intitulé.

## 4. Taxonomie

- **Ingénierie** : Software (générique), Back-end, Front-end, Fullstack, Mobile,
  DevOps/Cloud/SRE, Sécurité, QA/Test, Management engineering, FDE / déploiement IA.
- **Product management** (PM, PO, Head of Product, Product Builder).
- **Product design** (product designer, UX/UI, user research, design ops).
- **Data / IA / ML**.
- Recrutement tech, Chef de projet tech / TPM.
- Hors tech : Ingénierie hors logiciel (matériel, R&D physique), Créa / game design,
  Autres (business, ops, support), Candidature spontanée (exclue des comptes).

Précision mesurée sur un échantillon aléatoire de 60 offres : environ 95 %.
**Prochaine amélioration : classification par IA, offre par offre, avec justification.**

## 5. Couverture et limites (édition pilote)

- 62 entreprises sur 120 avec un flux exploitable, dont 53 avec au moins une offre
  tech en France.
- Non couvertes : environ 15 sur Welcome Kit (pas d'API publique), Exotec, Homa et
  CorWave (Workable bloqué temporairement par Cloudflare), et plusieurs boîtes
  deeptech ou industrielles (sites non lisibles automatiquement).
- Photo à date et non tendance. La tendance vient d'Indeed, sur un périmètre bien
  plus large que la French Tech.
- Concentration : Mistral AI = 84 des 448 offres tech FR. Les parts sont toujours
  vérifiées sans Mistral.
- Les compétences « IA » sont comptées en part d'offres **et** en part
  d'entreprises (plus robuste face à une entreprise qui publie beaucoup).
- Mistral AI est exclue du comptage de la mention « Mistral ».

## 6. Indicateurs à reproduire à chaque édition

1. Indice Indeed Software Development : FR vs US, niveau, évolution sur 1 an, écart au pic.
2. Volume d'offres (total, FR, tech FR, part hors France).
3. Répartition par groupe de rôles et ratios ingénierie/PM et PM/design (avec et sans Mistral).
4. Sous-spécialités d'ingénierie (mobile + front, FDE, sécurité, DevOps).
5. Compétences : top, puis termes IA (LLM, agents, Claude, OpenAI, Mistral, Cursor, MCP…), en part d'offres et d'entreprises.
6. Géographie (Île-de-France, Lyon/AURA…), mode de travail, contrats, langue des intitulés.
7. Comparaison avec l'édition précédente (à partir de février 2027).
