# ADR-0008 — Copy Engine

- Statut : accepté
- Date : 2026-07-25

## Contexte

FSBackup sait découvrir les données, construire un plan d'exécution et produire un manifeste. Le système doit également exécuter la copie physique des fichiers sans mélanger cette responsabilité avec la découverte, la planification, l'archivage ou le contrôle d'intégrité.

## Décision

Créer et maintenir un module autonome `copy_engine` chargé exclusivement de la copie locale des fichiers décrits par un manifeste vers une destination donnée.

Le moteur :

- traite le manifeste comme une donnée d'entrée immuable ;
- reconstruit l'arborescence relative dans la destination ;
- utilise `shutil.copy2` pour préserver les métadonnées disponibles ;
- isole les erreurs au niveau du fichier afin de poursuivre l'exécution ;
- retourne un rapport détaillé et des statistiques agrégées.

Le moteur ne doit pas :

- découvrir de nouvelles sources ;
- recalculer le plan d'exécution ;
- modifier le manifeste reçu ;
- créer une archive ;
- effectuer la validation cryptographique complète de la sauvegarde.

## Relation avec les autres modules

L'Execution Planner détermine les fichiers physiques nécessaires. Le Manifest Builder transforme ce plan en contrat versionné. Le Copy Engine consomme ce contrat et produit le résultat de l'exécution. Les moteurs Archive et Integrity peuvent ensuite travailler sur les fichiers copiés et sur le rapport généré.

## Conséquences

### Positives

- responsabilité unique et moteur testable indépendamment ;
- erreurs de copie contenues sans interrompre toute la sauvegarde ;
- évolution possible vers la reprise, le parallélisme et l'observabilité ;
- séparation nette entre ce qui est prévu et ce qui est réellement exécuté.

### Négatives

- un contrat d'adaptation est nécessaire pendant la coexistence des Manifest V1 et V2 ;
- la copie séquentielle initiale peut être lente sur de gros volumes ;
- la comparaison par taille ne garantit pas à elle seule l'identité du contenu.

## Évolutions prévues

- consommation native du Manifest V2 ;
- erreurs structurées et horodatages d'exécution ;
- vérification de hash optionnelle ;
- reprise après interruption ;
- copie parallèle contrôlée ;
- événements d'observabilité et possibilité d'annulation.
