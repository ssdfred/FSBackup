# Restore Engine

Le Restore Engine restaure les fichiers contenus dans une archive FSBackup `.fsb` vers un dossier cible.

## Responsabilités

- vérifier que l'archive existe et qu'elle est lisible ;
- valider `metadata.json`, `manifest.json` et `data/` ;
- refuser les chemins dangereux pouvant sortir du dossier cible ;
- restaurer les fichiers sous `data/` ;
- ignorer les fichiers existants par défaut ;
- permettre leur remplacement avec `overwrite=true` ;
- retourner un rapport sans lever d'erreur vers l'API.

## API

```text
POST /api/v1/restore/execute
```

Exemple :

```json
{
  "archive_path": "C:/Backups/backup.fsb",
  "destination_directory": "C:/Restore",
  "overwrite": false
}
```

## Limites de la version 1

- aucune restauration sélective ;
- aucune vérification de checksum ;
- aucune gestion du chiffrement ;
- aucune restauration vers les emplacements d'origine.
