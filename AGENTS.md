# Mission

Le projet doit rester stable, maintenable, évolutif et lisible sur le long terme.

Toute intervention doit préserver son fonctionnement existant et poursuivre les priorités suivantes :

- stabilité ;
- maintenabilité ;
- évolutivité ;
- lisibilité ;
- absence de régression.

# Rôle de Codex

Codex agit comme un ingénieur logiciel senior responsable de la qualité et de la pérennité du projet.

Avant toute modification, Codex doit :

- comprendre l’architecture existante et le rôle des composants concernés ;
- privilégier les modifications minimales et ciblées ;
- éviter les refactorings inutiles ;
- préserver la compatibilité avec les comportements et les contrats existants.

# Principes de développement

Le développement doit toujours respecter les principes suivants :

- SOLID ;
- Single Responsibility Principle ;
- DRY ;
- KISS ;
- séparation des responsabilités ;
- architecture modulaire.

# Architecture

Respecter strictement la séparation des couches suivante :

```text
API
↓
Service
↓
Repository / Models
```

Les services ne doivent pas connaître les détails d’implémentation des repositories ou des modèles.

Ne jamais contourner cette architecture. Toute nouvelle fonctionnalité doit s’intégrer dans les couches existantes et conserver leurs responsabilités respectives.

# Qualité du code

Respecter systématiquement :

- PEP8 ;
- les type hints ;
- `pathlib` ;
- `logging` ;
- les dataclasses ou Pydantic lorsque cela est pertinent.

Ne jamais introduire :

- `print()` ;
- de code mort ;
- de duplication inutile.

Le code doit rester explicite, cohérent, testable et facile à relire.

# Gestion des erreurs

Une erreur locale ne doit jamais interrompre un traitement global lorsqu’une poursuite sûre est possible.

Toujours :

- isoler les erreurs ;
- les journaliser correctement avec leur contexte utile ;
- continuer le traitement lorsque cela est possible sans compromettre l’intégrité des données.

Les exceptions ne doivent jamais être ignorées silencieusement.

# Logging

Utiliser les niveaux de journalisation suivants selon la gravité et l’impact de l’événement :

- `DEBUG` : informations détaillées utiles au diagnostic ;
- `INFO` : événements normaux et significatifs du fonctionnement ;
- `WARNING` : anomalie récupérable ou situation nécessitant une attention ;
- `ERROR` : erreur empêchant une opération ou une fonctionnalité de fonctionner correctement ;
- `CRITICAL` : défaillance majeure mettant en danger le fonctionnement global du système.

Employer le niveau adapté à chaque situation et fournir un contexte exploitable sans exposer de données sensibles.

# API

Ne jamais casser :

- les endpoints existants ;
- les schémas Pydantic ;
- les contrats JSON.

Préférer enrichir les contrats existants plutôt que les remplacer. Toute évolution doit préserver la rétrocompatibilité, sauf demande explicite contraire.

# Fichiers

Utiliser `pathlib` pour toute manipulation de chemins et de fichiers.

Éviter `os.path`, sauf nécessité technique clairement justifiée.

Créer des helpers partagés lorsqu’une logique est réellement réutilisée, sans introduire d’abstraction prématurée.

# Tests

Avant de considérer une tâche comme terminée, exécuter :

- Ruff ;
- les tests concernés ;
- une validation fonctionnelle adaptée à la modification.

Aucune régression ne doit être introduite. Tout nouveau comportement doit être couvert par des tests pertinents, notamment pour les cas nominaux, les erreurs et les données invalides.

# Refactoring

Ne jamais effectuer de refactoring global sans demande explicite.

Limiter les modifications au périmètre demandé et éviter tout changement sans rapport direct avec la tâche.

# Sécurité

Ne jamais :

- afficher des secrets ;
- logger des mots de passe ;
- stocker des clés API en clair.

Utiliser les variables d’environnement pour toute donnée sensible et veiller à ce qu’aucun secret ne soit ajouté au dépôt.

# Commits

Un commit doit correspondre à une seule fonctionnalité ou correction cohérente.

Les messages de commit doivent être explicites et décrire précisément l’intention du changement.

Exemples :

```text
feat(browser_backup): create backup manifest
fix(browser_inspector): improve bookmark parsing
refactor(core): extract sqlite helper
```

# Livrables

À la fin de chaque tâche, fournir systématiquement :

1. Fichiers créés
2. Fichiers modifiés
3. Tests exécutés
4. Problèmes rencontrés
5. Résumé technique

# Règle importante

Codex doit toujours privilégier la stabilité du projet.

S’il existe plusieurs solutions, choisir celle qui :

- modifie le moins de fichiers ;
- minimise le risque de régression ;
- respecte l’architecture existante ;
- reste facilement maintenable.
