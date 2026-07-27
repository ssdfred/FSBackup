# Validation Windows de bout en bout

Ce protocole valide qu’une sauvegarde créée par FSBackup peut être retrouvée, contrôlée et restaurée sans altérer la source.

## Périmètre

Le scénario couvre :

- une source Windows ou un dossier de test ;
- une destination locale distincte ;
- la création d’une archive `.fsb` ou `.fsbe` ;
- les exclusions explicitement confirmées ;
- la vérification d’intégrité ;
- le catalogue local ;
- la restauration dans un dossier isolé ;
- la comparaison des fichiers restaurés avec les fichiers attendus.

## Préparation du jeu de test

Créer un dossier dédié contenant au minimum :

```text
FSBackup-E2E-Source/
├── Documents/
│   ├── texte.txt
│   └── données.json
├── Projet/
│   ├── fichier-source.py
│   └── node_modules/
│       └── fichier-a-exclure.txt
└── Image/
    └── image-test.png
```

Les fichiers doivent avoir des contenus différents afin que les comparaisons par empreinte soient significatives.

## Scénario de sauvegarde

1. Choisir `Dossier personnalisé`.
2. Sélectionner le dossier `FSBackup-E2E-Source`.
3. Choisir une destination différente de la source.
4. Nommer l’archive `validation-e2e`.
5. Activer la vérification d’intégrité.
6. Laisser le chiffrement désactivé pour le premier passage.
7. Lancer la sauvegarde.

Le rapport doit confirmer :

- la création de l’archive ;
- le nombre de fichiers copiés ;
- l’intégrité valide ;
- l’absence d’erreur ;
- les éventuels avertissements ;
- les exclusions réellement appliquées.

## Scénario avec exclusion

Répéter le test avec une exclusion explicite de `node_modules`.

Vérifier que :

- l’exclusion est décochée par défaut ;
- une confirmation séparée est exigée ;
- le rapport indique les fichiers et octets exclus ;
- `fichier-a-exclure.txt` n’est pas présent après restauration ;
- les autres fichiers restent présents.

## Contrôle dans le catalogue

1. Ouvrir `Mes sauvegardes`.
2. Analyser le dossier de destination.
3. Vérifier que l’archive apparaît comme valide.
4. Vérifier le nom, la taille, la date, le nombre de fichiers et la version FSBackup.
5. Utiliser l’action `Restaurer` depuis le catalogue.

## Scénario de restauration

1. Restaurer dans un dossier vide `FSBackup-E2E-Restauration`.
2. Laisser l’écrasement désactivé.
3. Vérifier que l’intégrité est contrôlée avant extraction.
4. Vérifier que la restauration se termine sans erreur.
5. Contrôler le nombre de fichiers restaurés et les avertissements.

## Comparaison PowerShell

Comparer les empreintes des fichiers attendus :

```powershell
$source = "H:\FSBackup-E2E-Source"
$restore = "H:\FSBackup-E2E-Restauration"

$sourceFiles = Get-ChildItem $source -Recurse -File |
    Where-Object { $_.FullName -notmatch "\\node_modules\\" }

$results = foreach ($file in $sourceFiles) {
    $relative = $file.FullName.Substring($source.Length).TrimStart("\\")
    $restored = Join-Path $restore $relative

    [pscustomobject]@{
        Fichier = $relative
        Présent = Test-Path $restored
        SourceSHA256 = (Get-FileHash $file.FullName -Algorithm SHA256).Hash
        RestaurationSHA256 = if (Test-Path $restored) {
            (Get-FileHash $restored -Algorithm SHA256).Hash
        } else {
            $null
        }
    }
}

$results |
    Select-Object Fichier, Présent,
        @{Name="Identique";Expression={
            $_.Présent -and $_.SourceSHA256 -eq $_.RestaurationSHA256
        }} |
    Format-Table -AutoSize
```

Tous les fichiers attendus doivent afficher `Présent = True` et `Identique = True`.

## Critères de réussite

Le Sprint 10.8 est validé lorsque :

- les tests automatisés et Ruff sont verts ;
- une archive réelle est créée ;
- son intégrité est valide ;
- elle est reconnue par le catalogue ;
- elle peut être restaurée dans un dossier isolé ;
- les empreintes des fichiers attendus sont identiques ;
- les exclusions confirmées ne réapparaissent pas dans la restauration ;
- aucune donnée source n’est modifiée pendant le processus.
