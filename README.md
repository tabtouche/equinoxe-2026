# Hausse de loyer 2026 - Collection Équinoxe (CodeML 2026, défi JADCO)

## Résultat

**Hausse 2026 estimée : 3,6 %** (fourchette de 2,5 % à 4,6 %).

**Définition :** croissance annualisée du **loyer effectif** (`sRentEffective`) **à unité constante**. C'est la médiane, sur
tous les baux qui débutent en 2026 (renouvellements et relocations, six immeubles), de la hausse de chaque bail par rapport
au bail précédent du même appartement (clé `sPropCode` + `sUnitCode`).

**Méthode :** un gradient boosting (scikit-learn) entraîné sur environ 3 000 paires de baux. Il prédit la hausse de chaque bail
de 2026 à partir de ce qui est connu avant ce bail, puis on prend la médiane.

**Validation :** backtest 2023-2025, avec une erreur absolue moyenne de 1,1 point. La meilleure extrapolation de tendance fait 1,4 point.

Le détail, les hypothèses et les limites sont dans le notebook `equinoxe-2026.ipynb`.

## Contenu

| Fichier | Rôle |
|---|---|
| `equinoxe-2026.ipynb` | **notebook principal évalué** : analyse, `estimate_2026()`, `backtest()`, prévision 2026 |
| `models/modele_d_gbm.joblib` | modèle entraîné (régénéré à chaque exécution du notebook) |
| `private_data/` | les quatre fichiers CRM fournis par JADCO, inchangés |
| `public_data/regulatory_rates.csv` | taux du TAL et ligne directrice de l'Ontario, 2019-2026, avec la source de chaque valeur |
| `public_data/extract_cmhc.py` | extraction reproductible des fichiers Excel de la SCHL |
| `raw_public_data/` | données publiques brutes (voir plus bas) |
| `requirements.txt` | librairies et versions |

**Confidentialité :** les données CRM d'Équinoxe sont remises seulement à JADCO. Elles ne sont publiées nulle part : le dépôt git
du projet est privé, `private_data/` est exclu du suivi git, et les sorties des notebooks sont retirées à chaque commit (`nbstripout`).

## Exécuter le notebook

1. Vérifier que les quatre fichiers CRM sont dans `private_data/`, à la racine du projet :

   ```
   private_data/
   ├── equinoxe_listings.csv
   ├── equinoxe_lease_history.csv
   ├── equinoxe_concessions.csv
   └── equinoxe_asking_history.csv
   ```

2. Créer l'environnement et installer les librairies (Python 3.13) :

   ```bash
   python -m venv .venv
   .venv\Scripts\activate          # Windows ; sous macOS / Linux : source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Ouvrir le notebook et exécuter toutes les cellules dans l'ordre :

   ```bash
   jupyter lab equinoxe-2026.ipynb
   ```

   Ou bien, sans interface :

   ```bash
   jupyter nbconvert --to notebook --execute --inplace equinoxe-2026.ipynb
   ```

L'exécution complète prend environ deux minutes. Elle ne modifie aucun fichier source et réécrit seulement
`models/modele_d_gbm.joblib`. Le résultat est déterministe (`random_state = 0`).

### Utiliser le modèle entraîné

```python
import joblib
saved = joblib.load("models/modele_d_gbm.joblib")
model = saved["model"]          # HistGradientBoostingRegressor
saved["features"]               # colonnes attendues, dans l'ordre
saved["options"]                # variables retenues
```

Les variables se construisent avec `model_features()` (section 7c du notebook). Pour reproduire la prévision, il est plus simple
d'appeler `estimate_2026(leases, asking)` dans le notebook.

## Versions

Les versions ont été testées sous Windows 11.

| Librairie | Version |
|---|---|
| Python | 3.13.3 |
| pandas | 3.0.6 |
| NumPy | 2.5.3 |
| matplotlib | 3.11.2 |
| scikit-learn | 1.9.1 |
| joblib | 1.6.0 |
| JupyterLab | 4.6.4 |

## Sources publiques

Les données ont été téléchargées en octobre 2026 et vont jusqu'en décembre 2025, comme les données CRM.

| Fichier (`raw_public_data/`) | Source | Contenu |
|---|---|---|
| `rmr-canada-2021-fr.xlsx` à `rmr-canada-2025-fr.xlsx` | SCHL, *Enquête sur les logements locatifs*, tableaux du Rapport sur le marché locatif ([cmhc-schl.gc.ca](https://www.cmhc-schl.gc.ca)) | inoccupation, rotation, loyer moyen, univers locatif, variation du loyer à échantillon fixe ; RMR de Montréal et d'Ottawa (partie Ontario) |
| `schl-inoccupation.csv` | Statistique Canada, tableau 34-10-0127-01 (données SCHL) | taux d'inoccupation, Montréal et Ottawa (partie Ontario), 2014-2025 |
| `schl-loyers.csv` | Statistique Canada, tableau 34-10-0133-01 (données SCHL) | loyer moyen des 2 chambres, 2014-2025 ; recoupe les fichiers Excel, non utilisé dans le notebook |
| `ipc-loyers.csv` | Statistique Canada, tableau 18-10-0004-01 | IPC mensuel, composante loyer, Canada, Québec, Ontario, 2015-2025 |
| `IPC.csv` | Statistique Canada, tableau 18-10-0004-01 | IPC mensuel, Canada, par groupe de produits, 2015-2025 ; non utilisé dans le notebook final |
| `msrche-du-travail.csv` | Statistique Canada, tableau 14-10-0460-01 | population active par RMR (Montréal, Toronto, Vancouver), 2015-2025 |
| `evolution-demographique.csv` | Statistique Canada, tableau 17-10-0149-01 | composantes de l'accroissement démographique par RMR, 2015/2016 à 2024/2025 |
| `mise-en-marche.csv` | Statistique Canada, tableau 34-10-0156-01 | mises en chantier, Canada, 2015-2025 ; non utilisé dans le notebook final |

Taux réglementaires (`public_data/regulatory_rates.csv`) :

- **Québec** : taux du TAL pour un logement non chauffé. Sources : communiqués du TAL ([tal.gouv.qc.ca](https://www.tal.gouv.qc.ca)), Radio-Canada, Le Devoir.
- **Ontario** : ligne directrice provinciale ([ontario.ca/page/rent-increase-guideline](https://www.ontario.ca/page/rent-increase-guideline)), compilée par leaseplain.com et keystead.ca.

La source de chaque valeur est indiquée dans le fichier. The Met est traité comme vraisemblablement **exempté** de la ligne
directrice : selon la règle ontarienne, les logements occupés pour la première fois après le 15 novembre 2018 en sont exemptés.

## Références et outils d'IA

- JADCO, *Clés en main* (consignes CodeML 2026) et `starter.ipynb`.
- scikit-learn, `HistGradientBoostingRegressor` : https://scikit-learn.org
- **Claude Code (Anthropic)** a été utilisé pour :
  - aider à écrire le code et les textes ;
  - télécharger les séries publiques de Statistique Canada ;
  - tester les variables publiques ;
  - mettre en forme le notebook et ce README.

  Les choix de méthode, les vérifications et les conclusions ont été revus par l'équipe.
