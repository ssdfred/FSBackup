# Copy Engine

Le module `copy_engine` exécute la copie physique des fichiers décrits par un manifeste de sauvegarde vers un répertoire de destination.

## Responsabilités

- résoudre chaque chemin source à partir de `Manifest.source_root` ;
- reproduire l'arborescence relative dans le répertoire cible ;
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

La requête contient un `Manifest` V1 et un `destination_root`. La réponse est un `CopyReport` composé d'un résumé et du résultat de chaque fichier.

## Position dans le pipeline

```text
Execution Planner
        |
        v
Manifest Builder
        |
        v
Copy Engine
        |
        v
Archive / Integrity / Restore
```

Le Copy Engine ne découvre pas les sources, ne modifie pas le manifeste et ne crée pas d'archive. Il consomme un contrat préparé en amont et restitue uniquement le résultat de l'exécution physique.

## Évolution prévue

La prochaine évolution fera converger le moteur vers le contrat Manifest V2 et enrichira le rapport d'exécution avec des horodatages, des erreurs structurées et des statistiques directement réutilisables par le Manifest V2.
