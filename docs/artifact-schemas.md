# Mutable artifact schemas and recovery

Raw exporter JSON is immutable. Mutable/rebuildable analysis state includes
annotations, autonomous run ledgers/candidates, runtime observations, protocol
contracts, and semantic metadata.

Writers use an adjacent advisory `.lock` file around the complete
read-modify-write transaction, flush a same-directory temporary file, and use
atomic replacement. Revision fields allow later tooling to identify update
order. Separate run ids remain the recommended way to parallelise agents.

## Audit

```powershell
revhub migrate-artifacts
```

The command reports every recognised artifact, schema version, and support
status. It exits non-zero for unknown/unsupported forms.

## Migration

```powershell
revhub migrate-artifacts --apply
```

Only explicit, recognisable migrations are applied. A timestamped backup is
written beneath `<export>/artifact_backups/` before replacement. Unknown newer
schemas are refused rather than guessed. Raw exports are never migrated by this
command.
