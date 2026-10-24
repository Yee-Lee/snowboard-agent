# Private Pi evidence packaging and Git privacy check

## Boundary

Private Pi results stay outside every Git worktree. This includes raw audio,
transcripts, prompts/responses, detailed operator comments, raw logs containing
content, and environment output that identifies a workstation or private home path.

The public Git projection may contain test/run IDs, candidate and artifact hashes,
status, numeric metrics, aggregate error categories, timestamps, sanitized reasons,
and logical reproduction locators. `Yee.Lee` and `yeelee.tw@gmail.com` are approved
public identities. Workstation type/OS, `/home/<name>/`, `/Users/<name>/`, local host
names, and operator-specific absolute paths are not public.

## Package on the Pi

For each private bundle, create one directory outside a repository:

```text
<private-root>/<bundle-id>/
├── manifest.private.json
├── SHA256SUMS
└── payload/
```

`manifest.private.json` records the bundle ID, owner, source run IDs, candidate
SHAs, classification, retention decision, and relative payload paths. It may contain
private metadata because it never enters Git. `SHA256SUMS` covers the manifest and
every payload file.

Set the directory and resulting archive to owner-only access. Package relative names
from the bundle directory so the archive does not preserve `/home/...`:

```bash
chmod -R go-rwx <private-root>/<bundle-id>
tar -C <private-root>/<bundle-id> -czf <bundle-id>.private.tgz .
chmod 600 <bundle-id>.private.tgz
```

Copy the archive to designated private storage outside a checkout, verify its
SHA-256 at the destination, and record receipt. Encryption is optional when the
source, transport, and destination are already trusted; the current design does not
add a key-management system.

The archive is never added to Git, including with `git add -f`. `.gitignore` reduces
accidents but is not the control.

## Create the public projection

Create a separate public JSON index from the private manifest. Do
not copy raw records and redact them afterward. Build a new document using only the
allowed fields below. Identify private material by `bundle_id`; resolve it through
the private manifest outside Git. Do not include environment metadata or paths.

```json
{
  "schema_version": 1,
  "records": [
    {
      "test_id": "T-001",
      "status": "PASS",
      "metrics": {"cer": 0.12},
      "error_counts": {"timeout": 0},
      "bundle_id": "evidence-001"
    }
  ]
}
```

Each record requires `test_id` and `status`. Optional fields are `run_id`,
`candidate_sha`, `artifact_sha256`, `metrics`, `error_counts`, `bundle_id`, `user`,
and `email`. Unknown fields are rejected. Metrics contain finite numbers only;
error counts are nonnegative integers. Status is one of `PASS`, `FAIL`, `REJECTED`,
`ACCEPTED`, `SKIP`, `UNKNOWN`, `INCONCLUSIVE`, or `NOT_APPLICABLE`.
IDs must be neutral test identifiers. Only the
approved user and email values are allowed. Free-form reasons belong in the private
bundle; manually reviewed Markdown may summarize them separately.

Scan the complete projection before staging:

```bash
python scripts/privacy_gate.py --strict-evidence scan-files <public-json-files...>
```

After `git add`, scan the exact staged blobs:

```bash
python scripts/privacy_gate.py scan-staged
```

The general scanner rejects private home paths, local SSH host identities, common
secret formats, private/binary payload types, files over 2 MiB, and configured
private sentinels. Strict evidence mode additionally validates the complete JSON
against the field allowlist. It prints only the filename and rule ID, never the
matched value. It does not maintain a workstation brand dictionary.

Schema validation cannot determine whether an identifier or Markdown paragraph
reveals private information. Review those manually before publication. Passing the
scanner is a check against common mistakes, not a guarantee of anonymity.

When a test has known private canaries, store them in an untracked owner-only file
and add:

```bash
python scripts/privacy_gate.py --sentinel-file <private-sentinels> scan-staged
```

Before push, review `git diff --cached` together with the scanner result. GitHub CI
may repeat the range scan, but it cannot undo a disclosure that was already pushed;
the staged check is mandatory.
