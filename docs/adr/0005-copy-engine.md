# ADR-0005 — Copy Engine

## Statut

Accepté.

## Contexte

La copie est une opération à effets de bord qui doit rester prévisible, observable et indépendante de la détection des sources.

## Décision

Limiter le Copy Engine à l’application d’opérations déjà planifiées et validées. Il crée les destinations nécessaires, copie les fichiers et retourne un bilan explicite des réussites et erreurs.

## Conséquences

- moteur testable avec des répertoires temporaires ;
- pas de logique de découverte cachée ;
- erreurs locales rapportées sans être ignorées ;
- responsabilité claire sur les écritures de fichiers.

## Alternatives écartées

Fusionner planification et copie a été écarté afin de conserver la prévisualisation et de réduire le risque d’écritures imprévues.
