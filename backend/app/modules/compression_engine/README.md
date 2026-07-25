# Compression Engine

Le module `compression_engine` centralise la configuration et les métriques de compression des archives FSBackup.

## Méthodes disponibles

- `deflated` : compression ZIP standard, utilisée par défaut ;
- `stored` : stockage sans compression.

Le niveau `deflated` est configurable de `0` à `9` et vaut `6` par défaut.

## Intégration

`ArchiveRequest` accepte désormais une configuration optionnelle :

```python
from app.modules.compression_engine.schemas import CompressionSettings

request = ArchiveRequest(
    source_directory="copied",
    destination_directory="archives",
    archive_name="backup.fsb",
    manifest=manifest,
    compression=CompressionSettings(level=9),
)
```

L'absence de configuration conserve le comportement historique : une archive `.fsb` utilisant `deflated` au niveau `6`.

## Rapport

`ArchiveReport` expose :

- la taille réelle du fichier archive ;
- la taille originale des entrées ZIP ;
- le nombre d'octets économisés ;
- le ratio `taille compressée / taille originale` ;
- la méthode et le niveau utilisés.

Les métriques portent sur les entrées ZIP. La taille du conteneur `.fsb` inclut également les en-têtes et l'index ZIP.

## Limites

Ce premier incrément ne prend pas encore en charge :

- Zstandard, LZMA ou BZIP2 ;
- les profils automatiques selon le type de fichier ;
- la compression parallèle ;
- la limitation de ressources ;
- le chiffrement, prévu dans l'étape suivante de la roadmap.
