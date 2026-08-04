# Roadmap

## v0.2

- Core Engine

## v0.3

- Archive Engine

## v0.4

- Restore Engine

## v0.5

- Compression

## v0.6

- Encryption

## v0.7

- Incremental Backup

## v0.8

- CLI

## v0.9

- GUI

## v1.0

- Stable Release
- Lanceur Windows
- Installateur Windows
- Publication GitHub avec installateur et empreinte SHA-256

## Sprints à faire

### Sprint 11.1 — Jeux de sauvegarde fractionnés

**Statut : implémenté, en validation fonctionnelle Windows.**

- Introduire un jeu de sauvegarde composé de plusieurs archives `.fsb` autonomes.
- Générer un manifeste `backup-set.json` décrivant les lots, leur contenu, leur état et leur empreinte cryptographique.
- Fractionner automatiquement une sauvegarde volumineuse en lots cohérents, avec une taille maximale configurable.
- Conserver le mode de sauvegarde actuel et la compatibilité avec les archives existantes.
- Permettre la restauration indépendante de chaque archive d'un jeu.
- Couvrir les cas nominaux, les données invalides et l'échec isolé d'un lot par des tests.

### Sprint 11.2 — Reprise après interruption

**Statut : implémenté, en validation fonctionnelle Windows.**

- Persister la progression après la validation de chaque lot.
- Permettre de reprendre un jeu interrompu sans recréer les lots déjà vérifiés.
- Vérifier l'existence et l'intégrité des lots terminés avant toute reprise.
- Afficher clairement les lots sauvegardés, en attente, en échec et à reprendre.
- Garantir qu'un jeu partiel n'est jamais présenté comme une sauvegarde complète.
- Tester les reprises après arrêt utilisateur, erreur de copie, erreur d'archivage et échec de vérification.

### Sprint 11.3 — Résilience et accompagnement utilisateur

**Statut : en cours.**

- Détecter rapidement une répétition d'erreurs indiquant que le disque source est devenu indisponible.
- Interrompre uniquement le lot courant et préserver les lots autonomes déjà validés.
- Fournir un message compréhensible indiquant le lot atteint, les données sécurisées et les actions recommandées.
- Proposer dans l'interface un mode « Sauvegarde fractionnée et reprenable » avec réglages automatiques par défaut.
- Réserver les options de taille avancées aux utilisateurs qui souhaitent les personnaliser.
- Ajouter une validation fonctionnelle Windows de la reprise après déconnexion puis reconnexion du disque source.
