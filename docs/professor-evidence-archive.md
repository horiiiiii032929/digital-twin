# Professor evidence archive

The archive indexes the 70-slide `Course Digital Twin — Final Presentation`
on the author's Desktop and the immutable report submitted on 6 September 2026.
The DOCX is a linking index; datasets, original materials and saved outputs are
distributed separately in the same ZIP. Neither slides nor historical results
are regenerated.

## Build and verification

Use the Codex bundled Python with `python-docx` and `pypdf` available. Resolve
its path with the workspace dependency tool. Run these commands from the
repository root, substituting that interpreter for `python`:

```bash
python scripts/build_professor_evidence.py --inventory
python scripts/build_professor_evidence.py --build
python scripts/supplement_professor_evidence.py
python scripts/finalize_professor_evidence.py
python scripts/finalize_professor_evidence.py --dump-verify
uv run pytest tests/test_professor_evidence_archive.py -q
python scripts/package_professor_evidence.py
```

The first builder refuses to overwrite an existing output directory. Preserve
the prior archive before preparing another version. The inventory and staging
files live under ignored `reports/generated/professor-evidence-build/`; the
deliverables live under ignored `reports/generated/professor-evidence/`.
Render and inspect every DOCX page using the document skill before packaging.

The SQL restore check reconstructs a separate SQLite database, compares every
table's rows and hashes, executes every supplied query, compares its CSV
snapshot, and checks relative DOCX links after relocation. The package builder
then verifies copied file hashes and every ZIP member. This verifies archive
integrity, not the validity of the historical experiments.

## Storage decision

Use a downloadable SQLite database and SQLite SQL dump with private S3 object
storage. This supports offline SQL queries without a running database service.
PostgreSQL would support pgAdmin and shared live querying, but that is not the
requested handoff. DynamoDB would require a different query model and service
access without improving this static evidence archive. The application database
and deployment are unchanged.

The chosen archive can be replaced by a new versioned ZIP. The original files
remain local. Private signed download URLs expire; the downloaded archive does
not. There is no public bucket, web application, or live database endpoint.
Current regional storage/request prices and the actual ZIP size must be checked
before upload. Upload and link generation are separate from these local scripts.

## Interpretation and boundaries

- Primary study mappings are explicit. Supporting references are collected
  through four discovery levels and recursively linked within that inventory.
  This is not an inventory of every unrelated repository experiment.
- Source files are matched to original hashes where those hashes are recorded.
  The 32-PDF corpus is distinct from the IT5004 demonstration lecture and the
  public networking sources used by later factual and visual comparisons.
- Historical source snapshots remain in their ZIPs and are text indexed.
  Current implementation code is labelled as context, not a replacement for
  the historical dirty working tree.
- Missing referenced paths remain unresolved. Some are stale or illustrative
  references; a missing path alone does not establish that a result was lost.
  Known missing raw ledgers cannot be reconstructed from an aggregate summary.
- Authentication tables are excluded from companion SQLite exports. Other
  table values and binary columns are retained. The export does not preserve
  application constraints, indexes or triggers and is not a production backup.
- JSON roots and indexed members overlap. Queries must select an explicit file
  and locator grain before counting. Repeated ratings are not independent cases.
- Saved-data arithmetic checks reproduce the later learner study and teaching
  diagnostics; other metrics are preserved as recorded, without blanket claims
  of independent recalculation. Failed gates and disputed scores remain so.
- Private course material is for the source holder's requested professor
  research review. It is not published or assigned an open license.

The final manifest and query snapshots are the authoritative inventory and
validation evidence for the delivered archive.
