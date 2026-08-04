# Jeux de sauvegarde fractionnés

FSBackup peut créer un jeu de sauvegarde composé d'archives autonomes et
reprenables. Le mode historique à archive unique reste disponible et les
contrats existants restent compatibles.

## Structure

```text
sauvegarde-poste/
├── backup-set.json
├── sauvegarde-poste-part-0001.fsb
├── sauvegarde-poste-part-0002.fsb
└── sauvegarde-poste-part-0003.fsb
```

Chaque archive contient son propre manifeste et peut être restaurée seule.
`backup-set.json` décrit l'ensemble, l'état de chaque lot, l'empreinte du plan
et l'empreinte SHA-256 de l'archive validée.

## Contrat de création

Les champs suivants enrichissent `POST /api/v1/backup/run` :

- `segmented` active le jeu fractionné ; sa valeur par défaut API reste
  `false` pour préserver les clients existants ;
- `segment_size_bytes` définit la taille cible maximale entre deux fichiers ;
- `resume` autorise la réutilisation des lots terminés.

Un fichier plus grand que la taille cible forme un lot autonome. Il n'est
jamais découpé arbitrairement.

## Reprise sûre

Après chaque lot, le manifeste est remplacé atomiquement. Un lot existant
n'est réutilisé que si :

1. son empreinte de plan correspond encore aux fichiers prévus ;
2. son archive existe ;
3. son empreinte SHA-256 correspond ;
4. sa vérification d'intégrité réussit.

Une erreur de périphérique Windows 433 interrompt immédiatement le lot courant
au lieu de produire des milliers d'erreurs. Les lots précédemment validés sont
conservés et la même demande peut être relancée pour reprendre.

## Restauration et rétention

La restauration accepte le chemin du dossier du jeu ou celui de
`backup-set.json`. Un jeu incomplet n'est jamais restauré comme une sauvegarde
complète ; chaque archive autonome reste cependant restaurable séparément.

Le catalogue présente un jeu comme une seule sauvegarde et masque ses parties.
La rétention protège actuellement les jeux contre une suppression partielle.
