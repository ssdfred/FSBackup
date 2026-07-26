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

## Génération de l'installateur Windows

L'installateur utilise Inno Setup 6. Une installation rapide est possible avec :

```powershell
winget install --id JRSoftware.InnoSetup -e
```

Depuis la racine du dépôt, générez ensuite l'application et son installateur :

```powershell
.\build-installer.ps1
```

Pour réutiliser une distribution PyInstaller déjà compilée :

```powershell
.\build-installer.ps1 -SkipApplicationBuild
```

Le package final et son empreinte SHA-256 sont produits dans :

```text
release\FSBackup-Setup-1.0.0.exe
release\FSBackup-Setup-1.0.0.exe.sha256
```

L'assistant d'installation propose :

- une installation par utilisateur, sans élévation obligatoire ;
- un raccourci dans le menu Démarrer ;
- un raccourci facultatif sur le Bureau ;
- un lancement facultatif à l'ouverture de session ;
- le lancement de FSBackup à la fin de l'installation ;
- une désinstallation standard depuis les paramètres Windows.

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
