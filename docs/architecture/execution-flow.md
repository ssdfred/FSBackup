# Flux d’exécution

## Sauvegarde

```mermaid
sequenceDiagram
    participant Client
    participant Inspector as Browser Inspector
    participant Discovery as Source Discovery
    participant Planner as Backup / Execution Planner
    participant Manifest as Manifest Builder
    participant Copy as Copy Engine
    participant Archive as Archive Engine
    participant Integrity as Integrity Engine

    Client->>Inspector: inspecter les navigateurs
    Inspector-->>Client: profils et métadonnées
    Client->>Discovery: découvrir les sources
    Discovery-->>Planner: sources normalisées
    Planner-->>Manifest: plan d’exécution
    Manifest-->>Copy: manifeste déterministe
    Copy-->>Archive: fichiers copiés
    Archive-->>Integrity: archive produite
    Integrity-->>Client: résultat de vérification
```

## Restauration

```mermaid
sequenceDiagram
    participant Client
    participant Manifest
    participant Integrity
    participant Restore as Restore Engine
    participant Filesystem

    Client->>Integrity: vérifier la sauvegarde
    Integrity-->>Client: résultat
    Client->>Restore: demander la restauration
    Restore->>Manifest: lire les entrées attendues
    Restore->>Filesystem: restaurer les fichiers
    Restore-->>Client: bilan détaillé
```

## Invariants

- La découverte ne copie aucun fichier.
- La planification ne modifie aucune source.
- Le Manifest Builder ne réalise aucune copie.
- Le Copy Engine applique un plan déjà validé.
- La restauration ne dépend pas d’une nouvelle inspection du navigateur source.
- Une erreur locale est isolée et reportée lorsque la poursuite reste sûre.
