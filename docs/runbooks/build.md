# Runbook — Construction et installation

## Prérequis

- Python 3.13 ;
- Git ;
- un environnement virtuel isolé.

## Installation locale

Depuis la racine du dépôt :

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Sous Linux :

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Démarrage de l’API

```bash
python -m uvicorn app.main:app --reload
```

## Validation minimale

```bash
python -m ruff check .
python -m pytest
```

Ne pas considérer l’environnement prêt tant que les dépendances ne sont pas installées depuis le fichier versionné et que la suite de tests ne passe pas.
