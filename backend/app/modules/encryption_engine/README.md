# Encryption Engine

Le moteur de chiffrement protège une archive FSB complète dans un conteneur `FSBE` authentifié.

## Format v2

Les nouvelles archives utilisent le format `FSBE2` :

- sel Scrypt aléatoire de 16 octets ;
- préfixe de nonce aléatoire de 8 octets ;
- taille de bloc enregistrée dans l'en-tête ;
- taille originale enregistrée et vérifiée au déchiffrement ;
- blocs chiffrés séparément avec AES-256-GCM ;
- nonce unique composé du préfixe et du compteur de bloc ;
- compteur également inclus dans les données associées authentifiées.

La taille de bloc est configurable entre 64 Kio et 16 Mio et vaut 1 Mio par défaut. Le traitement reste ainsi borné en mémoire, quelle que soit la taille totale de l'archive.

## Compatibilité v1

Le moteur continue de reconnaître et de déchiffrer les anciens conteneurs `FSBE1` créés avant le Sprint 7.3. Les nouvelles opérations de chiffrement produisent uniquement du `FSBE2`.

## Garanties

- le mot de passe et la clé dérivée ne sont jamais écrits dans le fichier ni dans les rapports ;
- un mauvais mot de passe échoue sans laisser de fichier en clair ;
- toute modification d'un bloc, de sa taille ou de l'en-tête est détectée ;
- les données supplémentaires placées après le dernier bloc sont refusées ;
- la taille restaurée doit correspondre à la taille originale authentifiée ;
- le chiffrement et le déchiffrement refusent d'écraser une destination existante par défaut ;
- les archives `.fsb` non chiffrées restent inchangées et compatibles.

## Dérivation de clé

Une clé de 256 bits est dérivée à la demande avec Scrypt (`n=2^14`, `r=8`, `p=1`) et un sel aléatoire propre à chaque conteneur.
