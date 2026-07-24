# FSBackup

FSBackup est une solution open source de sauvegarde, restauration et migration de postes de travail.

## Objectifs

- Audit des navigateurs
- Sauvegarde intelligente
- Vérification d'intégrité
- Restauration
- Analyse des disques
- Rapports

Développé avec Python et FastAPI.

## Architecture

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
Restore Engine
```