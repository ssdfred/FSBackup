# Vue d’ensemble de l’architecture

FSBackup est organisé en modules spécialisés reliés par des contrats explicites. Chaque module conserve une responsabilité unique et expose ses fonctionnalités par la couche API lorsque nécessaire.

```mermaid
flowchart TD
    BI[Browser Inspector]
    SD[Source Discovery]
    BP[Backup Planner]
    EP[Execution Planner]
    MB[Manifest Builder]
    CE[Copy Engine]
    AE[Archive Engine]
    IE[Integrity Engine]
    RE[Restore Engine]

    BI --> SD
    SD --> BP
    BP --> EP
    EP --> MB
    MB --> CE
    CE --> AE
    MB --> IE
    AE --> IE
    MB --> RE
    AE --> RE
```

## Règles structurantes

- La couche API valide les entrées et délègue au service.
- Le service porte l’orchestration métier du module.
- Les modèles et schémas décrivent les données manipulées.
- Un module aval ne redécouvre pas les données déjà produites par un module amont.
- Les opérations de lecture, de planification, de copie, d’archivage, de contrôle et de restauration restent séparées.
- Les contrats existants sont enrichis de manière rétrocompatible plutôt que remplacés.

## Objectifs

Cette architecture vise la testabilité, la déterminisme des plans, la traçabilité des sauvegardes, la limitation des effets de bord et l’ajout progressif de nouvelles cibles de sauvegarde.
