# Archive Engine

L'Archive Engine transforme un dossier de sauvegarde copié en une archive portable au format `.fsb`.

## Responsabilité

Le module :

- lit un dossier source déjà préparé par le Copy Engine ;
- ajoute `metadata.json` ;
- ajoute le manifeste fourni sans le reconstruire ;
- place les fichiers sauvegardés sous `data/` ;
- crée une archive ZIP portant l'extension publique `.fsb`.

Il ne réalise ni restauration, ni chiffrement, ni vérification d'intégrité avancée.

## Structure interne

```text
backup.fsb
├── metadata.json
├── manifest.json
└── data/
```

## API

```text
POST /api/v1/archive/create
```

## Exemple de requête

```json
{
  "source_directory": "C:/FSBackup/work/backup",
  "destination_directory": "C:/FSBackup/archives",
  "archive_name": "backup-2026-07-24.fsb",
  "manifest": {
    "format_version": 1,
    "created_at": "2026-07-24T08:00:00Z",
    "source_root": "C:/Users/Fred",
    "summary": {
      "logical_items": 1,
      "physical_files": 1,
      "missing_files": 0,
      "encrypted_items": 0,
      "deduplicated_files": 0,
      "estimated_size_bytes": 8,
      "warnings": 0
    },
    "files": []
  }
}
```
