[CmdletBinding()]
param(
    [switch]$Force,
    [switch]$Yes
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-CommandSafe {
    param([string]$Name)
    return Get-Command $Name -ErrorAction SilentlyContinue
}

function Get-HomeDir {
    $homeDir = $env:USERPROFILE
    if ([string]::IsNullOrWhiteSpace($homeDir)) {
        $homeDir = $HOME
    }
    if ([string]::IsNullOrWhiteSpace($homeDir)) {
        throw 'cannot resolve home directory from USERPROFILE/HOME'
    }
    return $homeDir
}

function Get-GitConfigValue {
    param(
        [string]$Key
    )
    $output = & git config --global --get $Key 2>$null
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

function Test-InteractiveHost {
    try {
        if (-not [Environment]::UserInteractive) {
            return $false
        }
        if ($null -eq $Host -or $null -eq $Host.UI -or $null -eq $Host.UI.RawUI) {
            return $false
        }
        return $true
    } catch {
        return $false
    }
}

try {
    if (-not (Get-CommandSafe -Name 'git')) {
        throw 'git command not found in PATH'
    }

    $homeDir = Get-HomeDir
    $templateRoot = Join-Path $homeDir '.codex\git-templates\gitnexus-githooks-bootstrap'
    $templateRootGit = ([System.IO.Path]::GetFullPath($templateRoot)).Replace('\', '/')

    $existingTemplateDir = Get-GitConfigValue -Key 'init.templateDir'
    if ($null -ne $existingTemplateDir -and $existingTemplateDir -ne $templateRootGit -and (-not $Force)) {
        throw "global init.templateDir already set to '$existingTemplateDir'. Re-run with -Force to override."
    }

    if (-not $Yes) {
        if (-not (Test-InteractiveHost)) {
            throw 'non-interactive host detected. Re-run with -Yes to proceed without prompt.'
        }

        Write-Host '即将执行以下修改（全局一次）：'
        Write-Host ("- 写入 Git 模板目录: {0}" -f $templateRootGit)
        if ($null -eq $existingTemplateDir) {
            Write-Host '- 设置 git config --global init.templateDir（当前为空）'
        } else {
            Write-Host ("- 设置 git config --global init.templateDir（当前为: {0}）" -f $existingTemplateDir)
        }
        Write-Host '- 模板将安装 hooks: post-checkout / post-commit / post-merge'
        Write-Host '- 回滚: git config --global --unset init.templateDir'
        Write-Host ''

        $answer = Read-Host '是否继续安装？输入 y 确认，其他任意键取消'
        if ($answer -notmatch '^(y|Y|yes|YES)$') {
            Write-Output ([ordered]@{
                ok = $false
                templateRoot = $templateRootGit
                message = 'cancelled by user'
            } | ConvertTo-Json -Depth 5)
            exit 0
        }
    }

    $hooksDir = Join-Path $templateRoot 'hooks'
    New-Item -ItemType Directory -Path $hooksDir -Force | Out-Null

    $bootstrapPostCheckout = @(
        '#!/bin/sh'
        'set -u'
        ''
        '# Bootstrapper hook (installed via git init.templateDir).'
        '# If the repo contains versioned ".githooks", enable it automatically.'
        ''
        'REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"'
        ''
        'if [ -d "$REPO_ROOT/.githooks" ]; then'
        '  hooks_path="$(git config --get core.hooksPath 2>/dev/null || echo '')"'
        '  if [ -z "$hooks_path" ]; then'
        '    git config core.hooksPath .githooks >/dev/null 2>&1 || true'
        '  fi'
        'fi'
        ''
        'exit 0'
        ''
    ) -join "`n"

    $bootstrapPostCommit = @(
        '#!/bin/sh'
        'set -u'
        ''
        '# Bootstrapper hook (installed via git init.templateDir).'
        '# If the repo contains versioned ".githooks", enable it automatically.'
        ''
        'REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"'
        'REPO_HOOK="$REPO_ROOT/.githooks/post-commit"'
        ''
        'if [ -f "$REPO_HOOK" ]; then'
        '  hooks_path="$(git config --get core.hooksPath 2>/dev/null || echo '')"'
        '  if [ -z "$hooks_path" ]; then'
        '    git config core.hooksPath .githooks >/dev/null 2>&1 || true'
        '  fi'
        '  sh "$REPO_HOOK" || true'
        'fi'
        ''
        'exit 0'
        ''
    ) -join "`n"

    $bootstrapPostMerge = @(
        '#!/bin/sh'
        'set -u'
        ''
        '# Bootstrapper hook (installed via git init.templateDir).'
        '# If the repo contains versioned ".githooks", enable it automatically.'
        ''
        'REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"'
        'REPO_HOOK="$REPO_ROOT/.githooks/post-merge"'
        ''
        'if [ -f "$REPO_HOOK" ]; then'
        '  hooks_path="$(git config --get core.hooksPath 2>/dev/null || echo '')"'
        '  if [ -z "$hooks_path" ]; then'
        '    git config core.hooksPath .githooks >/dev/null 2>&1 || true'
        '  fi'
        '  sh "$REPO_HOOK" || true'
        'fi'
        ''
        'exit 0'
        ''
    ) -join "`n"

    Write-Utf8NoBomLfFile -Path (Join-Path $hooksDir 'post-checkout') -Content $bootstrapPostCheckout -Overwrite:$Force
    Write-Utf8NoBomLfFile -Path (Join-Path $hooksDir 'post-commit') -Content $bootstrapPostCommit -Overwrite:$Force
    Write-Utf8NoBomLfFile -Path (Join-Path $hooksDir 'post-merge') -Content $bootstrapPostMerge -Overwrite:$Force

    & git config --global init.templateDir $templateRootGit | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw 'failed to set global init.templateDir'
    }

    Write-Output ([ordered]@{
        ok = $true
        templateRoot = $templateRootGit
        installedHooks = @('post-checkout', 'post-commit', 'post-merge')
        message = 'global git template hooks installed; new clones will auto-enable repo .githooks when present'
    } | ConvertTo-Json -Depth 5)
} catch {
    Write-Output ([ordered]@{
        ok = $false
        message = $_.Exception.Message
    } | ConvertTo-Json -Depth 5)
    exit 1
}
