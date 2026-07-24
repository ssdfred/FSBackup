# Runbook — Dépannage

## Erreur pendant la collecte Pytest

Vérifier d’abord l’import mentionné dans la trace et l’installation des dépendances :

```bash
python -m pip install -r requirements.txt
python -m pytest --collect-only
```

Éviter les noms de modules de tests identiques lorsqu’ils peuvent provoquer un conflit d’import. Préférer des noms explicites comme `test_manifest_builder_service.py`.

## Différence entre Windows et Linux

- utiliser `pathlib` dans le code ;
- ne pas comparer des chemins avec des séparateurs codés en dur ;
- exécuter la suite complète sur les deux plateformes après une modification liée aux fichiers ;
- ne pas dépendre d’un navigateur réellement installé dans les tests.

## Fichier verrouillé ou inaccessible

L’inspection et les contrôles doivent isoler les erreurs locales, les journaliser au niveau adapté et retourner une valeur neutre ou un résultat d’erreur structuré lorsque la poursuite est sûre.

## Test utilisant `datetime`

Ne pas modifier directement les méthodes de `datetime.datetime`, type immuable sur les versions récentes de Python. Tester avec des timestamps réels ou remplacer le symbole importé dans le module concerné.

## Dépendance TestClient

Si Starlette signale une dépendance HTTP manquante, réinstaller strictement `requirements.txt` avant de modifier le code. Les dépendances nécessaires aux tests doivent être versionnées.

## Diagnostic minimal

```bash
python --version
python -m pip check
python -m ruff check .
python -m pytest -x -vv
```

Conserver la première trace complète : elle contient généralement la cause primaire, contrairement aux erreurs en cascade.
