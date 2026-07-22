# Conception du module `backup_inventory`

## Responsabilité

Le module `backup_inventory` construit un inventaire explicable et strictement en lecture seule des éléments susceptibles d’être sauvegardés. Il ne copie, ne déplace, ne supprime et ne sauvegarde aucun fichier.

L’inventaire part de sources bornées et connues (profils utilisateurs, résultats des inspecteurs existants et emplacements configurés). Il ne parcourt jamais aveuglément l’intégralité d’un disque.

## Architecture proposée

```text
API (router.py)
↓
InventoryService (service.py)
↓
Detectors + ClassificationPolicy + MetadataProbe
↓
Repository / Models
```

- `router.py` expose uniquement la consultation et le déclenchement contrôlé d’un inventaire.
- `service.py` orchestre les détecteurs, isole leurs erreurs et applique la politique de classification.
- `detectors/` contient des détecteurs spécialisés et indépendants : navigateurs, dossiers utilisateur, projets de développement et applications connues.
- `classification.py` centralise les règles ordonnées d’inclusion et d’exclusion ainsi que leur justification.
- `metadata.py` collecte uniquement les métadonnées nécessaires : existence, type, accessibilité et taille estimée.
- `repository.py` persiste éventuellement les instantanés d’inventaire via les helpers partagés du projet, sans accès direct depuis l’API.
- `models.py` porte les modèles métier internes.
- `schemas.py` porte les contrats Pydantic de l’API.

Les détecteurs proposent des candidats ; ils ne décident pas du mécanisme de sauvegarde. Le service ne dépend que de leurs contrats, pas de leurs détails d’implémentation.

## Arborescence cible

```text
backend/app/modules/backup_inventory/
├── __init__.py
├── api.py
├── schemas.py
├── models.py
├── service.py
├── repository.py
├── classification.py
├── metadata.py
└── detectors/
    ├── __init__.py
    ├── base.py
    ├── browser.py
    ├── user_directories.py
    ├── development.py
    └── applications.py
```

Cette arborescence est une cible de conception. Aucun de ces modules n’est créé à cette étape.

## Modèle de données proposé

```python
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class InventoryCategory(StrEnum):
    MUST_BACKUP = "must_backup"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"
    EXCLUDED = "excluded"
    NEEDS_REVIEW = "needs_review"


class InventoryEntryType(StrEnum):
    FILE = "file"
    DIRECTORY = "directory"


@dataclass(frozen=True, slots=True)
class InventoryItem:
    path: Path
    entry_type: InventoryEntryType
    category: InventoryCategory
    reason: str
    estimated_size_bytes: int | None
    exists: bool
    accessible: bool
    detection_source: str
    exclusion_rule: str | None = None
    warning: str | None = None
```

Les schémas Pydantic exposeraient les mêmes champs, avec le chemin sérialisé en chaîne. Une taille inconnue reste `null` plutôt que `0`. Un élément inaccessible reste présent dans l’inventaire avec `accessible=false`, une catégorie `needs_review` et un avertissement exploitable.

## Politique initiale de classification

Les règles sont ordonnées. La première exclusion spécifique applicable l’emporte sur une règle d’inclusion générique. Chaque décision conserve un identifiant de règle stable et une raison lisible.

### `must_backup`

- documents utilisateur explicitement sélectionnés ;
- bases ou fichiers applicatifs irremplaçables identifiés par un détecteur fiable ;
- profils et données personnelles configurés comme indispensables par l’utilisateur.

### `recommended`

- favoris et profils de navigateurs utiles ;
- paramètres applicatifs difficiles à reconstituer ;
- dossiers personnels standards détectés dans les emplacements utilisateur connus.

### `optional`

- téléchargements ;
- médias volumineux ou données facilement récupérables ;
- données applicatives non essentielles mais potentiellement utiles.

### `excluded`

- caches génériques et caches applicatifs connus ;
- caches de navigateurs (`Cache`, `Code Cache`, `GPUCache`, `ShaderCache`) ;
- fichiers et dossiers temporaires ;
- corbeilles ;
- dépendances reproductibles (`node_modules`) ;
- environnements Python reproductibles (`.venv`, `venv`) ;
- artefacts de compilation (`__pycache__`, `dist`, `build`, fichiers objets) ;
- fichiers système non pertinents et fichiers d’échange ;
- éléments correspondant à une règle d’exclusion configurée explicitement.

### `needs_review`

- chemins inaccessibles ou dont le type ne peut pas être déterminé ;
- liens ou points de jonction sortant du périmètre autorisé ;
- données sensibles ou volumineuses dont la valeur ne peut pas être déduite des métadonnées ;
- conflits entre règles de même priorité ;
- formats ou applications inconnus.

## Règles de parcours et de sécurité

- Utiliser uniquement des racines configurées ou fournies par des détecteurs existants.
- Ne jamais suivre par défaut les liens symboliques, jonctions ou points de montage.
- Inspecter les noms, types, tailles et dates ; ne pas lire le contenu personnel lorsque ces métadonnées suffisent.
- Encadrer chaque accès au système de fichiers afin qu’une erreur locale produise un avertissement sans interrompre l’inventaire.
- Prévoir des limites configurables de profondeur, de nombre d’éléments et de durée.
- Estimer progressivement la taille des dossiers et signaler une estimation partielle.
- Dédupliquer les chemins après normalisation, sans résoudre un lien qui sortirait du périmètre.
- Conserver la provenance de chaque candidat et l’identifiant de la règle appliquée.
- Garantir l’absence de primitive d’écriture, de suppression, de copie ou de déplacement dans ce module.

## API envisagée

Une première version peut exposer un endpoint de consultation sous le préfixe propre au module, sans modifier `GET /api/v1/browser`. Le contrat devra permettre de fournir des racines bornées et des options de limite, puis retourner l’inventaire, les avertissements et un indicateur de résultat partiel.

Le choix entre un scan synchrone borné et un traitement asynchrone persistant doit être validé avant de figer les endpoints. Aucun endpoint n’est ajouté à cette étape.

## Tests à prévoir

- classification de chaque catégorie ;
- priorité des exclusions sur les inclusions ;
- chemin absent, inaccessible ou de type inconnu ;
- taille partielle et erreur de métadonnées ;
- isolation d’un détecteur en erreur ;
- refus de suivre un lien hors périmètre ;
- limites de profondeur, de volume et de durée ;
- déduplication de candidats issus de plusieurs détecteurs ;
- absence d’opération d’écriture sur les éléments inspectés.

## Décisions nécessitant une validation humaine

- racines utilisateur parcourues par défaut et mécanisme de consentement ;
- catégories par défaut pour Téléchargements, médias et profils applicatifs ;
- seuils de taille, profondeur, nombre d’éléments et durée ;
- traitement des liens symboliques et jonctions explicitement autorisés ;
- persistance ou non des instantanés et durée de conservation ;
- niveau de détail des chemins exposés par l’API ;
- priorité des règles personnalisées sur les règles intégrées ;
- stratégie synchrone ou asynchrone pour les inventaires importants.
