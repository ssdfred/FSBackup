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

Le backend est contrôlé automatiquement à chaque push et pull request :

```powershell
cd backend
python -m ruff check .
python -m pytest
```

La CI utilise Python 3.13 et bloque les régressions détectées par Ruff ou Pytest.

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
