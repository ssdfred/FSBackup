# Runbook — Tests et qualité

## Commandes obligatoires

Depuis `backend/` :

```bash
python -m ruff check .
python -m pytest
```

La suite Pytest génère les rapports de couverture configurés dans `pyproject.toml`, notamment `htmlcov/` et `coverage.xml`.

## Ordre recommandé

1. Exécuter Ruff pour détecter rapidement les erreurs statiques.
2. Exécuter les tests du module modifié pendant le développement.
3. Exécuter la suite complète avant commit ou fusion.
4. Vérifier que la couverture globale ne régresse pas sans justification.

## Critères de validation

- aucune erreur Ruff ;
- aucun test en échec ou en erreur de collecte ;
- aucun avertissement critique ignoré ;
- comportement nominal, erreurs et données invalides couverts ;
- compatibilité Windows et Linux lorsque les chemins ou fichiers sont concernés.

## Exemple de test ciblé

```bash
python -m pytest app/modules/manifest_builder/tests -q
```

Un test ne doit pas dépendre d’un profil navigateur réel ni modifier les données de l’utilisateur. Utiliser `tmp_path`, des fixtures et des doublures locales.
