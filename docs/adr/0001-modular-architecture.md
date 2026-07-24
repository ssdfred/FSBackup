# ADR-0001 — Architecture modulaire

## Statut

Accepté.

## Contexte

FSBackup combine découverte, planification, copie, archivage, intégrité et restauration. Une orchestration monolithique rendrait les responsabilités difficiles à tester et à faire évoluer.

## Décision

Organiser le backend en modules fonctionnels autonomes respectant la séparation `API → Service → Models / Repository`. Les échanges entre modules passent par des schémas explicites.

## Conséquences

- responsabilités localisées ;
- tests unitaires plus simples ;
- évolution indépendante des moteurs ;
- contrats intermodules à maintenir avec soin.

## Alternatives écartées

Un service global unique a été écarté en raison du couplage et du risque de régression qu’il introduirait.
