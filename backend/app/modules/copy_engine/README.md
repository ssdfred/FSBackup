# Copy Engine

Le module `copy_engine` exécute la copie physique des fichiers décrits par un `ExecutionPlan` vers un répertoire de destination.

## Responsabilités

- consommer les fichiers physiques produits par l'Execution Planner ;
- utiliser `PhysicalFile.source_path` comme source officielle ;
- reproduire chaque `relative_path` dans le répertoire cible ;
- refuser tout chemin qui sortirait du répertoire de destination ;
- copier les fichiers avec `shutil.copy2` afin de conserver les métadonnées disponibles ;
- ignorer les fichiers déjà présents lorsque leur taille correspond ;
- poursuivre l'exécution lorsqu'un fichier est absent ou qu'une erreur d'entrée/sortie survient ;
- produire un rapport structuré exploitable par Reporting et Observability.

## Execution Report V2

Chaque exécution retourne un `CopyReport` contenant notamment :

- un `execution_id` unique ;
- les horodatages UTC `started_at` et `finished_at` ;
- la durée globale en millisecondes ;
- un indicateur `success` ;
- le résumé agrégé et le détail par fichier ;
- les avertissements et erreurs structurés ;
- des métadonnées techniques sur l'exécution.

Un fichier source absent produit un avertissement `source_missing`. Une erreur de copie ou un chemin cible invalide produit une erreur `copy_failed`. Une exécution est considérée comme réussie uniquement lorsqu'elle ne contient ni fichier absent ni erreur.

## Event Bus

Le Copy Engine peut publier des événements internes grâce à `CopyEventBus`. Ce bus est synchrone, local au processus et conservé uniquement en mémoire. Il n'utilise ni broker externe ni persistance en base de données.

Les événements disponibles sont :

- `copy_started` ;
- `file_started` ;
- `file_copied` ;
- `file_skipped` ;
- `file_missing` ;
- `file_error` ;
- `copy_finished`.

Chaque exécution commence par `copy_started`, publie ensuite un `file_started` et un événement terminal pour chaque fichier, puis se termine par `copy_finished`. Tous les événements partagent le même `execution_id` que le rapport final.

Exemple d'abonnement :

```python
from app.modules.copy_engine.events import CopyEvent, CopyEventBus
from app.modules.copy_engine.service import CopyEngineService

events: list[CopyEvent] = []
event_bus = CopyEventBus()
event_bus.subscribe(events.append)

report = CopyEngineService.execute(
    request,
    event_bus=event_bus,
)
```

Les listeners sont appelés dans leur ordre d'inscription. Une exception levée par un listener est isolée, mémorisée dans `listener_errors` et ne bloque ni les autres listeners ni l'exécution de la copie.

## Limites actuelles

La version actuelle reste volontairement locale et séquentielle. Elle ne prend pas encore en charge :

- la reprise après interruption ;
- les copies parallèles ;
- les nouvelles tentatives automatiques ;
- la vérification cryptographique pendant la copie ;
- la limitation du débit ;
- l'annulation d'une exécution en cours ;
- la persistance ou la diffusion distante des événements.

## Contrat API

```http
POST /api/v1/copy/execute
```

La requête contient un `ExecutionPlan` et un `destination_root`. La réponse est un `CopyReport` V2 complet.

## Position dans le pipeline

```text
Execution Planner
        |
        v
Copy Engine
        |
        v
Manifest Builder V2
        |
        v
Archive / Integrity / Restore
```

Le Copy Engine ne découvre pas les sources, ne recalcule pas le plan et ne crée pas d'archive. Il consomme un contrat préparé en amont et restitue uniquement le résultat de l'exécution physique.
