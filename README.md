# FSBackup

[![Backend CI](https://github.com/ssdfred/FSBackup/actions/workflows/backend.yml/badge.svg)](https://github.com/ssdfred/FSBackup/actions/workflows/backend.yml)
![Python](https://img.shields.io/badge/Python-3.13-blue)
![Licence](https://img.shields.io/badge/licence-MIT-green)

FSBackup est une solution open source de sauvegarde, restauration et migration de postes de travail.

## Objectifs

- Audit des navigateurs
- Sauvegarde intelligente
- Création d'archives `.fsb`
- Vérification d'intégrité
- Restauration sécurisée
- Analyse des disques
- Rapports

## Qualité

Le backend est contrôlé automatiquement à chaque push et pull request.

Validation rapide :

```powershell
cd backend
python -m ruff check .
python -m pytest
```

Validation avec couverture :

```powershell
cd backend
python -m pytest --cov=app --cov-branch --cov-report=term-missing --cov-report=html --cov-report=xml
```

Cette commande produit :

- un rapport détaillé dans le terminal ;
- un rapport HTML dans `backend/htmlcov/` ;
- un rapport XML dans `backend/coverage.xml`.

GitHub Actions publie les rapports HTML et XML comme artefacts téléchargeables pendant 14 jours. Le taux observé pendant ce sprint servira de référence avant l'activation progressive d'un seuil minimal bloquant.

## Architecture du moteur

```text
Source Discovery
        ↓
Backup Planner
        ↓
Execution Planner
        ↓
Manifest Builder
        ↓
Copy Engine
        ↓
Archive Engine
        ↓
Integrity Engine
        ↓
Restore Engine
```

Développé avec Python et FastAPI.
