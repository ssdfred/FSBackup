# Encryption Engine

Le moteur de chiffrement protège une archive FSB complète dans un conteneur `FSBE` authentifié.

## Format v1

- en-tête magique `FSBE1` ;
- sel Scrypt aléatoire de 16 octets ;
- nonce AES-GCM aléatoire de 12 octets ;
- charge utile chiffrée et authentifiée par AES-256-GCM ;
- données associées versionnées : `FSBackup:FSBE:1`.

Le mot de passe n'est jamais écrit dans le fichier ni dans les rapports. La clé de 256 bits est dérivée à la demande avec Scrypt.

## Garanties

- un mauvais mot de passe échoue sans produire de fichier en clair ;
- toute modification de la charge utile est détectée ;
- le déchiffrement refuse d'écraser une destination existante par défaut ;
- les archives `.fsb` non chiffrées restent inchangées et compatibles.

## Limites du Sprint 7.1

Le module fournit le chiffrement et le déchiffrement de fichiers complets. Son orchestration automatique avec les API Archive et Restore sera ajoutée dans un incrément suivant.
