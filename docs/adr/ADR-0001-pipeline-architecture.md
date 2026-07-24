# ADR-0001

## Titre

Architecture Pipeline

## Statut

Accepted

## Contexte

FSBackup doit rester modulaire.

Les décisions métier doivent être séparées des opérations d'E/S.

## Décision

Le traitement est organisé selon le pipeline suivant :

Source Discovery
↓

Backup Planner
↓

Execution Planner
↓

Manifest Builder
↓

Copy Engine

Chaque étape possède une responsabilité unique.

## Conséquences

Les modules peuvent évoluer indépendamment.

Le moteur de copie reste totalement agnostique.