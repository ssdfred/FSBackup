# Documentation FSBackup

Cette documentation décrit l’architecture, les décisions structurantes et les procédures de maintenance de FSBackup.

## Architecture

- [Vue d’ensemble](architecture/overview.md)
- [Flux d’exécution](architecture/execution-flow.md)
- [Responsabilités des modules](architecture/modules.md)
- [Manifeste de sauvegarde](architecture/manifest.md)

## Architecture Decision Records

- [ADR-0001 — Architecture modulaire](adr/0001-modular-architecture.md)
- [ADR-0002 — Découverte des navigateurs](adr/0002-browser-discovery.md)
- [ADR-0003 — Plan d’exécution](adr/0003-execution-plan.md)
- [ADR-0004 — Manifest Builder](adr/0004-manifest-builder.md)
- [ADR-0005 — Copy Engine](adr/0005-copy-engine.md)
- [ADR-0006 — Restore Engine](adr/0006-restore-engine.md)
- [ADR-0007 — Integrity Engine](adr/0007-integrity-engine.md)

## Runbooks

- [Construction et installation](runbooks/build.md)
- [Tests et qualité](runbooks/testing.md)
- [Dépannage](runbooks/troubleshooting.md)

## Principes

La documentation complète les contrats du code sans les remplacer. En cas d’écart, le comportement testé et les schémas publics existants restent la source de vérité opérationnelle.
