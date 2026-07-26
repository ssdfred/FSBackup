# Checklist de publication FSBackup 1.0.0

## Qualité

- [ ] `python -m pytest` est vert depuis `backend`.
- [ ] `ruff check .` est vert depuis `backend`.
- [ ] La version FastAPI affichée est `1.0.0`.
- [ ] Le lanceur ouvre l’interface locale sans erreur.
- [ ] Un second lancement ouvre l’instance existante.

## Sauvegarde et restauration

- [ ] Une sauvegarde réelle est créée avec succès.
- [ ] Le catalogue retrouve l’archive créée.
- [ ] La restauration restitue les fichiers attendus.
- [ ] Le contrôle d’intégrité est valide.
- [ ] La simulation de rétention ne supprime aucun fichier.
- [ ] L’exécution de rétention respecte le plan simulé.

## Distribution Windows

- [ ] `build-windows.ps1` génère `backend\dist\FSBackup\FSBackup.exe`.
- [ ] `build-installer.ps1` génère `release\FSBackup-Setup-1.0.0.exe`.
- [ ] L’empreinte `.sha256` correspond à l’installateur.
- [ ] L’installation fonctionne sur une session Windows standard.
- [ ] Le raccourci du menu Démarrer fonctionne.
- [ ] La désinstallation supprime le dossier d’installation.

## Publication GitHub

- [ ] La PR de stabilisation est fusionnée dans `main`.
- [ ] Le tag `v1.0.0` pointe sur le commit validé.
- [ ] Une GitHub Release `FSBackup 1.0.0` est créée.
- [ ] L’installateur et son empreinte SHA-256 sont joints à la release.
- [ ] Les notes de version reprennent `CHANGELOG.md`.

## Validation recommandée

Avant une diffusion large, installer et tester FSBackup sur un second PC Windows ne disposant ni de Python, ni de l’environnement de développement, ni d’Inno Setup.
