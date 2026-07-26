# Journal des modifications

Toutes les évolutions importantes de FSBackup sont documentées dans ce fichier.

Le format s’inspire de Keep a Changelog.

---

## [1.0.0] - 2026-07-26

### Ajouté

- interface graphique locale pour Windows ;
- détection des lecteurs et sélection native des dossiers et archives ;
- création de sauvegardes chiffrées au format FSBackup ;
- catalogue local des sauvegardes ;
- restauration avec contrôle d’intégrité ;
- simulation et exécution sécurisée de la rétention ;
- rapports d’exécution et suivi de progression ;
- lanceur Windows ouvrant automatiquement l’interface ;
- gestion d’une instance déjà active ;
- installateur Windows avec raccourcis et désinstallation ;
- génération d’une empreinte SHA-256 du package.

### Sécurité

- chiffrement en flux des archives ;
- validation des chemins et des archives avant restauration ;
- séparation des opérations de simulation et d’exécution ;
- journal local en cas d’échec du lanceur.

### Distribution

- exécutable autonome produit avec PyInstaller ;
- installateur produit avec Inno Setup 6 ;
- version publique centralisée sur `1.0.0`.

---

## [0.2.0] - 2026-07-24

### Ajouté

- Source Discovery ;
- Backup Planner ;
- Execution Planner ;
- Manifest Builder ;
- Copy Engine.

### Tests

- Pytest ;
- Ruff ;
- validation de l’API.

### Architecture

- architecture en pipeline ;
- séparation stricte des responsabilités ;
- manifeste utilisé comme contrat d’exécution.
