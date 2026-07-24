# ADR-0002 — Découverte des navigateurs

## Statut

Accepté.

## Contexte

Les profils de navigateurs varient selon le système, le navigateur et l’état local des fichiers. Certains fichiers peuvent être absents, verrouillés ou invalides.

## Décision

Centraliser la détection et l’inspection dans Browser Inspector, puis transmettre des résultats structurés à Source Discovery. L’inspection reste strictement en lecture seule et tolère les erreurs locales récupérables.

## Conséquences

- aucune duplication de la logique de détection ;
- comportement homogène entre les moteurs ;
- meilleure robustesse face aux profils incomplets ;
- nécessité de tests ciblés par navigateur et cas limite.

## Alternatives écartées

Faire redécouvrir les profils par chaque moteur a été écarté à cause de la duplication, du couplage au système et des incohérences possibles.
