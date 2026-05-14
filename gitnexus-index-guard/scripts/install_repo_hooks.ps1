[CmdletBinding()]
param(
    [string]$RepoPath = (Get-Location).Path,
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-CommandSafe {
    param([string]$Name)
    return Get-Command $Name -ErrorAction SilentlyContinue
}

function Get-RepoRoot {
    param([string]$Path)
    $output = & git -C $Path rev-parse --show-toplevel 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw 'target path is not inside a git repository'
    }
    return (($output | Out-String).Trim())
}

function Get-GitConfigValue {
    param(
        [string]$Root,
        [string]$Key
    )
    $output = & git -C $Root config --get $Key 2>$null
    if ($LASTEXITCODE -ne 0) {
        return $null
    }
    $value = (($output | Out-String).Trim())
    if ([string]::IsNullOrWhiteSpace($value)) {
        return $null
    }
    return $value
}

function Write-Utf8NoBomLfFile {
    param(
        [string]$Path,
        [string]$Content,
        [switch]$Overwrite
    )
    if ((Test-Path -LiteralPath $Path) -and (-not $Overwrite)) {
        return
    }
    $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($Path, $Content, $utf8NoBom)
}

try {
    if (-not (Get-CommandSafe -Name 'git')) {
        throw 'git command not found in PATH'
    }

    $resolvedPath = (Resolve-Path -LiteralPath $RepoPath).Path
    $repoRoot = Get-RepoRoot -Path $resolvedPath

    $hooksDir = Join-Path $repoRoot '.githooks'
    New-Item -ItemType Directory -Path $hooksDir -Force | Out-Null

    $postCommit = @(
        '#!/bin/sh'
        'set -u'
        ''
        '# Auto refresh GitNexus index after committing code changes.'
        '# gitnexus-index-guard-hook: commit-rebuild'
        '# Enable hooks once per clone:'
        '#   git config core.hooksPath .githooks'
        ''
        'REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"'
        'HOME_DIR="${USERPROFILE:-${HOME:-}}"'
        'GUARD_PS1="${HOME_DIR}/.codex/skills/gitnexus-index-guard/scripts/check_gitnexus_index.ps1"'
        ''
        'echo "[git-hook] GitNexus index refresh (post-commit) ..."'
        ''
        'if command -v pwsh >/dev/null 2>&1 && [ -f "$GUARD_PS1" ]; then'
        '  if out="$(pwsh -NoProfile -ExecutionPolicy Bypass -File "$GUARD_PS1" -RepoPath "$REPO_ROOT" -AutoAnalyze -HookManagedNonBlocking:$false 2>&1)"; then'
        '    msg="$(printf ''%s\n'' "$out" | awk -F''"'' ''/"message"[[:space:]]*:/ {m=$4} END{print m}'' )"'
        '    if [ -n "$msg" ]; then'
        '      echo "[git-hook] GitNexus: $msg"'
        '    else'
        '      echo "[git-hook] GitNexus index guard completed."'
        '    fi'
        '    exit 0'
        '  fi'
        '  echo "[git-hook] GitNexus index refresh failed (index-guard). Continue." >&2'
        'fi'
        ''
        'if command -v npx >/dev/null 2>&1; then'
        '  cd "$REPO_ROOT"'
        '  if npx -y gitnexus@latest analyze >/dev/null; then'
        '    echo "[git-hook] GitNexus index refreshed (npx)."'
        '    exit 0'
        '  fi'
        '  echo "[git-hook] GitNexus index refresh failed (npx). Continue." >&2'
        'fi'
        ''
        'echo "[git-hook] Skip: pwsh/gitnexus-index-guard and npx not available." >&2'
        'exit 0'
        ''
    ) -join "`n"

    $postMerge = @(
        '#!/bin/sh'
        'set -u'
        ''
        '# Auto refresh GitNexus index after merge/pull.'
        '# gitnexus-index-guard-hook: merge-rebuild'
        '# Enable hooks once per clone:'
        '#   git config core.hooksPath .githooks'
        ''
        'REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"'
        'HOME_DIR="${USERPROFILE:-${HOME:-}}"'
        'GUARD_PS1="${HOME_DIR}/.codex/skills/gitnexus-index-guard/scripts/check_gitnexus_index.ps1"'
        ''
        'echo "[git-hook] GitNexus index refresh (post-merge) ..."'
        ''
        'if command -v pwsh >/dev/null 2>&1 && [ -f "$GUARD_PS1" ]; then'
        '  if out="$(pwsh -NoProfile -ExecutionPolicy Bypass -File "$GUARD_PS1" -RepoPath "$REPO_ROOT" -AutoAnalyze -HookManagedNonBlocking:$false 2>&1)"; then'
        '    msg="$(printf ''%s\n'' "$out" | awk -F''"'' ''/"message"[[:space:]]*:/ {m=$4} END{print m}'' )"'
        '    if [ -n "$msg" ]; then'
        '      echo "[git-hook] GitNexus: $msg"'
        '    else'
        '      echo "[git-hook] GitNexus index guard completed."'
        '    fi'
        '    exit 0'
        '  fi'
        '  echo "[git-hook] GitNexus index refresh failed (index-guard). Continue." >&2'
        'fi'
        ''
        'if command -v npx >/dev/null 2>&1; then'
        '  cd "$REPO_ROOT"'
        '  if npx -y gitnexus@latest analyze >/dev/null; then'
        '    echo "[git-hook] GitNexus index refreshed (npx)."'
        '    exit 0'
        '  fi'
        '  echo "[git-hook] GitNexus index refresh failed (npx). Continue." >&2'
        'fi'
        ''
        'echo "[git-hook] Skip: pwsh/gitnexus-index-guard and npx not available." >&2'
        'exit 0'
        ''
    ) -join "`n"

    $readme = @(
        '# Git hooks: Auto refresh GitNexus index'
        ''
        'Purpose: keep GitNexus index in sync after commit/merge and avoid stale code intelligence.'
        ''
        '## Enable (once per clone)'
        ''
        'Run in repo root:'
        ''
        '```bash'
        'git config core.hooksPath .githooks'
        '```'
        ''
        '## Trigger points'
        ''
        '- `post-commit`: refresh index after commit'
        '- `post-merge`: refresh index after merge / pull'
        ''
        '## Notes'
        ''
        '- Hook is best-effort and does not block commit/pull.'
        '- Manual guard checks can use hook-managed non-blocking gate when hooks are fully wired.'
        '- If estimate level is `long`, auto analyze is skipped to avoid blocking.'
        ''
        '## Disable'
        ''
        '```bash'
        'git config --unset core.hooksPath'
        '```'
        ''
    ) -join "`n"

    Write-Utf8NoBomLfFile -Path (Join-Path $hooksDir 'post-commit') -Content $postCommit -Overwrite:$Force
    Write-Utf8NoBomLfFile -Path (Join-Path $hooksDir 'post-merge') -Content $postMerge -Overwrite:$Force
    Write-Utf8NoBomLfFile -Path (Join-Path $hooksDir 'README.md') -Content $readme -Overwrite:$Force

    $existingHooksPath = Get-GitConfigValue -Root $repoRoot -Key 'core.hooksPath'
    if ($null -ne $existingHooksPath -and $existingHooksPath -ne '.githooks' -and (-not $Force)) {
        throw \"core.hooksPath already set to '$existingHooksPath'. Re-run with -Force to override.\"
    }
    & git -C $repoRoot config core.hooksPath .githooks | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw 'failed to set core.hooksPath'
    }

    Write-Output ([ordered]@{
        ok = $true
        repoRoot = $repoRoot
        hooksDir = $hooksDir
        coreHooksPath = '.githooks'
        message = 'git hooks installed for auto GitNexus index refresh'
    } | ConvertTo-Json -Depth 5)
} catch {
    Write-Output ([ordered]@{
        ok = $false
        message = $_.Exception.Message
    } | ConvertTo-Json -Depth 5)
    exit 1
}
