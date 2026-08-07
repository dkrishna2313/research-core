# Exit Codes

The `research-core` CLI uses a stable set of exit codes to signal outcomes. These codes are part of the public API and will not change without a major version bump.

## Reference

| Code | Name | Meaning |
|------|------|---------|
| `0` | `SUCCESS` | Research completed successfully (COMPLETE or PARTIAL result) |
| `2` | `USAGE_ERROR` | Invalid CLI usage (missing subcommand, unknown flag, invalid format) |
| `3` | `INVALID_REQUEST` | Research question is blank or otherwise invalid |
| `4` | `UNKNOWN_PROFILE` | The specified profile ID is not recognized |
| `5` | `PROVIDER_FAILURE` | A knowledge or web provider raised an error |
| `6` | `EXECUTION_FAILURE` | The research pipeline failed to complete |
| `7` | `OUTPUT_FAILURE` | The result could not be rendered or serialized |
| `8` | `CONFIGURATION_FAILURE` | No providers configured, or conflicting flags (`--fixture` + `--knowledge-store`, `--web` in live mode, invalid store path) |

## Notes

- A `PARTIAL` result (some gaps identified, synthesis incomplete) exits with code `0`. It is a valid research artifact, not a failure.
- Exit code `2` is also used by `argparse` for unrecognized arguments and invalid option values.
- Exit codes `3–8` are specific to `research-core` and do not conflict with common POSIX conventions.

## Using in scripts

```bash
research-core run "question" --fixture
STATUS=$?

if [ $STATUS -eq 0 ]; then
    echo "Research complete"
elif [ $STATUS -eq 8 ]; then
    echo "No providers configured — add --fixture for local testing"
else
    echo "Error: exit code $STATUS"
fi
```

## Python API

The exit codes are available as an `IntEnum`:

```python
from research_core.cli.exit_codes import ExitCode

print(ExitCode.SUCCESS)          # 0
print(ExitCode.CONFIGURATION_FAILURE)  # 8
```
