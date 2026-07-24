# ADR-0004 — Manifest Builder

## Statut

Accepté.

## Contexte

Le Copy Engine et les moteurs aval ne doivent pas dépendre directement de Browser Inspector ni reconstruire le plan d’exécution.

## Décision

Introduire un Manifest Builder chargé de convertir un plan d’exécution validé en manifeste déterministe, sans lecture supplémentaire des sources et sans écriture.

## Conséquences

- découplage entre découverte et exécution ;
- manifeste réutilisable par la copie, l’intégrité et la restauration ;
- meilleure traçabilité ;
- nécessité de versionner les évolutions futures du contrat.

## Alternatives écartées

Faire consommer directement l’Execution Plan par tous les moteurs a été écarté pour éviter de figer un contrat d’exécution interne comme format persistant.
