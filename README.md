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

## Lancement en développement

Depuis le dossier `backend` :

```powershell
python -m uvicorn app.main:app --reload
```

L'interface est ensuite disponible sur `http://127.0.0.1:8000/app/`.

## Lanceur Windows

Le lanceur démarre le moteur local puis ouvre automatiquement FSBackup dans le navigateur :

```powershell
cd backend
python -m app.launcher
```

Par défaut, l'application utilise `127.0.0.1:8765`. Les variables `FSBACKUP_HOST` et `FSBACKUP_PORT` permettent de modifier cette adresse.

## Génération de l'exécutable Windows

Depuis la racine du dépôt :

```powershell
.\build-windows.ps1
```

Le script crée un environnement de compilation isolé, installe les dépendances d'exécution et PyInstaller, puis produit :

```text
backend\dist\FSBackup\FSBackup.exe
```

Cette première distribution est au format dossier autonome. Le futur installateur Windows s'appuiera sur ce résultat validé.

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
