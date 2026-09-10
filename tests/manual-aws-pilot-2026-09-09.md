# AWS pilot verification, 2026-09-09

Target: Singapore, profile `digital-twin`, stack `DigitalTwinPilot`.

Automated external check: `uv run python scripts/verify_aws_pilot.py`.
It tests HTTPS readiness, anonymous and synthetic-header denial, cross-origin
login denial, real administrator login, cookie flags, session, logout and
post-logout denial. It retrieves credentials privately and emits only statuses.

The first public attempt returned 504 because the extracted Caddyfile was mode
0600. After correcting it to 0644, a second attempt still returned 504 because
the origin rule used the VPC CIDR. Switching the rule to Singapore's AWS-managed
CloudFront origin-facing prefix list fixed external routing. These failures are
preserved in the deployment result; later successes do not erase them.

On the fresh pilot (one administrator, no course files), run this through
Session Manager on the host. It restores into temporary storage and compares
credential records without printing their contents. This small initial-state
smoke check is not the general backup procedure for populated courses; use a
separate durable backup destination for those, as documented in the CDK guide.

```bash
docker exec -i digital-twin-api python - <<'PY'
from pathlib import Path
import json, sqlite3, tempfile, time
from services.api.app.config import AppSettings
from services.operations import create_runtime_backup, restore_runtime_backup
settings = AppSettings.from_env(require_provider_credentials=False)
started = time.monotonic()
with tempfile.TemporaryDirectory(prefix="aws-pilot-restore-") as directory:
    root = Path(directory)
    archive = root / "backup.zip"
    manifest = create_runtime_backup(settings.database_path, settings.data_root, archive)
    restored_root = root / "restored"
    restored_db = restored_root / "digital-twin.sqlite3"
    restored = restore_runtime_backup(archive, restored_db, restored_root)
    with sqlite3.connect(settings.database_path) as original, sqlite3.connect(restored_db) as copy:
        expected = original.execute("SELECT account_id, password_hash FROM identity_credentials ORDER BY account_id").fetchall()
        actual = copy.execute("SELECT account_id, password_hash FROM identity_credentials ORDER BY account_id").fetchall()
        assert expected and expected == actual
        assert copy.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert manifest.schema_version == restored.schema_version
    print(json.dumps({"backup_restore": "passed", "identity_count": len(actual), "schema_version": restored.schema_version, "file_count": len(restored.data_files), "elapsed_seconds": round(time.monotonic()-started, 3)}))
PY
```

Observed: backup/restore passed, schema 19, one identity, zero source files,
0.015 seconds. One instantaneous Docker memory sample was 243.4 MiB API,
86.88 MiB ingestion worker, and 11.19 MiB web; these are not peak measurements.

Redeployment command: `npm --prefix infra/cdk run activate`. The second
activation explicitly reported that the existing administrator was preserved.

Reboot command:

```bash
aws ec2 reboot-instances --instance-ids i-0fde1692c45c87640   --profile digital-twin --region ap-southeast-1
```

After the host returns, check `mountpoint /var/lib/digital-twin`, Docker status,
and rerun the external authentication check. Never use this smoke procedure to
claim multi-AZ recovery, a production SLA, or populated-course restore coverage.

Observed reboot verification: boot at 2026-09-09 11:11:42 UTC; data mount present,
Docker active, all three containers running, and all nine public HTTPS/authentication
cases passed again.
