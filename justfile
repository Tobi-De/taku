@r *ARGS:
    uv run taku --scripts scripts  {{ ARGS }}

@fmt:
    uvx ruff format

@test:
    uv run pytest tests

# Run pre-commit
[group('lint')]
@pre-commit *ARGS:
    uvx prek {{ ARGS }}

# Run pre-commit on all files
[group('lint')]
@lint:
    just pre-commit run --all-files

# Generate changelog
[group('build')]
logchanges *ARGS:
    uvx git-cliff --output CHANGELOG.md {{ ARGS }}

# Bump project version and update changelog
[group('build')]
bumpver VERSION:
    #!/usr/bin/env bash
    set -euo pipefail
    uvx bump-my-version bump {{ VERSION }}
    just logchanges
    [ -z "$(git status --porcelain)" ] && { echo "No changes to commit."; git push && git push --tags; exit 0; }
    version="$(uv run bump-my-version show current_version)"
    git add -A
    git commit -m "Generate changelog for version ${version}"
    git tag -f "v${version}"
    git push && git push --tags
