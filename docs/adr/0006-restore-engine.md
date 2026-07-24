# ADR-0006 — Restore Engine

## Statut

Accepté.

## Contexte

Une restauration doit pouvoir être exécutée à partir d’une sauvegarde persistée, même si le navigateur ou la source d’origine n’est plus disponible.

## Décision

Le Restore Engine consomme les informations du manifeste et des artefacts de sauvegarde. Il valide les chemins de destination, évite les sorties hors de la racine autorisée et retourne un bilan détaillé.

## Conséquences

- restauration indépendante de la découverte initiale ;
- sécurité renforcée sur les chemins ;
- comportement reproductible ;
- besoin de conserver un manifeste compatible avec la sauvegarde.

## Alternatives écartées

Reconstruire la restauration depuis une nouvelle inspection locale a été écarté, car l’environnement peut avoir changé et ne représente pas la sauvegarde produite.
