# ADR-0007 — Integrity Engine

## Statut

Accepté.

## Contexte

Une sauvegarde réussie techniquement n’est exploitable que si les artefacts produits correspondent aux informations attendues.

## Décision

Confier à un Integrity Engine séparé la vérification des fichiers et archives à partir des données persistées. Le moteur retourne un résultat structuré sans modifier les artefacts contrôlés.

## Conséquences

- vérification réutilisable après la sauvegarde et avant la restauration ;
- séparation entre production et validation ;
- résultats d’erreur exploitables par l’API ;
- possibilité d’ajouter ultérieurement des algorithmes d’empreinte sans modifier la copie.

## Alternatives écartées

Effectuer uniquement les contrôles dans le Copy Engine a été écarté, car cela empêcherait les vérifications différées et augmenterait son périmètre de responsabilité.
