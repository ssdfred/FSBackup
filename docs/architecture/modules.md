# Responsabilités des modules

## Browser Inspector

Détecte les navigateurs, leurs profils et des métadonnées utiles. Il tolère les fichiers absents, verrouillés ou invalides sans modifier les profils.

## Source Discovery

Transforme les éléments détectés en sources de sauvegarde normalisées. Il applique les règles de découverte et ne réalise aucune copie.

## Backup Planner

Construit une intention de sauvegarde cohérente à partir des sources sélectionnées et des options demandées.

## Execution Planner

Résout l’intention en opérations exécutables, avec des chemins et destinations explicites. Son résultat doit être stable pour une même entrée.

## Manifest Builder

Transforme le plan d’exécution en manifeste déterministe consommable par les moteurs aval. Il ne lit pas le contenu des fichiers et ne réalise aucun effet de bord.

## Copy Engine

Copie les éléments décrits par le plan ou le manifeste, crée les répertoires nécessaires et retourne un bilan détaillé sans masquer les erreurs.

## Archive Engine

Produit une archive à partir des fichiers préparés. Il reste indépendant de la découverte des navigateurs.

## Integrity Engine

Vérifie l’existence, la taille et les informations d’intégrité attendues selon les contrats disponibles. Il rend un résultat exploitable par l’API et la restauration.

## Restore Engine

Restaure une sauvegarde vers une destination contrôlée, à partir des informations persistées. Il protège les chemins de destination et rapporte les éléments restaurés, ignorés ou en erreur.

## Dépendances autorisées

Les dépendances suivent le flux métier. Un moteur aval peut consommer les schémas d’un module amont, mais ne doit pas appeler une couche API interne ni reproduire sa logique de découverte.
