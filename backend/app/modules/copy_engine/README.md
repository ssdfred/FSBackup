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
- produire un rapport détaillé par fichier et un résumé agrégé.

## Limites actuelles

La version actuelle reste volontairement locale et séquentielle. Elle ne prend pas encore en charge :

- la reprise après interruption ;
- les copies parallèles ;
- les nouvelles tentatives automatiques ;
- la vérification cryptographique pendant la copie ;
- la limitation du débit ;
- l'annulation d'une exécution en cours.

## Contrat API

```http
POST /api/v1/copy/execute
```

La requête contient un `ExecutionPlan` et un `destination_root`. La réponse est un `CopyReport` composé d'un résumé et du résultat de chaque fichier.

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

## Évolutions prévues

Les prochains incréments enrichiront le rapport avec des horodatages, des erreurs structurées et des événements internes réutilisables par l'observabilité et l'interface utilisateur.
