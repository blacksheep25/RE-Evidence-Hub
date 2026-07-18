# Optional semantic search

Semantic search is a rebuildable lead generator. It never changes raw evidence
or accepted names.

## Install and build

```powershell
python -m pip install -e '.[semantic]'
revhub use TargetClient.exe
revhub semantic-index
```

The only supported format is stored with the export:

```text
derived/semantic/
  metadata.json   model, addresses, source fingerprint, schema
  vectors.npz     normalized float32 function vectors
```

This replaces user-global Chroma collections and duplicate vector folders.
Moving the export moves its index. Re-exported or changed functions require a
rebuild.

## Query

```powershell
revhub query semantic 'packet dispatch' --limit 10
revhub serve
# POST /semantic, /hybrid, or /ask
```

Core routes start without semantic dependencies or an index. Optional routes
return an actionable unavailable response instead of preventing the service
from starting.

## Evidence rule

Similarity establishes neither ownership nor behavior. Follow a semantic hit
with `lookup`, inspect concrete strings/imports/relationships and control flow,
then record a reviewed annotation only when direct evidence supports it.
