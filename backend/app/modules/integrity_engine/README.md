# Integrity Engine

Le module Integrity Engine controle une archive `.fsb` sans l'extraire.

## API

```text
POST /api/v1/integrity/verify
```

Exemple de requete :

```json
{
  "archive_path": "C:/Backups/backup.fsb"
}
```

## Controles realises

- presence de `metadata.json`, `manifest.json` et `data/` ;
- validite du conteneur ZIP utilise par le format FSB ;
- controle CRC fourni par `zipfile` ;
- validation Pydantic des metadonnees et du manifeste ;
- validation du format `FSB` et de sa version ;
- comparaison des fichiers de `data/` avec le manifeste ;
- detection des fichiers manquants, inattendus ou de taille differente.

Les fichiers inattendus produisent un avertissement. Les erreurs de structure, CRC,
manifestation ou taille rendent le rapport invalide.
