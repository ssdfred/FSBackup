# ADR-0003 — Plan d’exécution

## Statut

Accepté.

## Contexte

Une intention de sauvegarde ne suffit pas pour exécuter une copie de manière sûre. Les opérations doivent disposer de chemins résolus et d’un ordre stable.

## Décision

Introduire un Execution Planner qui transforme le plan métier en opérations explicites et déterministes avant toute écriture.

## Conséquences

- prévisualisation possible avant exécution ;
- validation des destinations en amont ;
- tests sans copie réelle ;
- séparation entre décision et effet de bord.

## Alternatives écartées

Résoudre les chemins au fil de la copie a été écarté, car cette approche mélange planification et exécution et complique la gestion des erreurs.
