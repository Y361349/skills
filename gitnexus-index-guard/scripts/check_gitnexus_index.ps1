[CmdletBinding()]
param(
    [string]$RepoPath = (Get-Location).Path,
    [switch]$AutoAnalyze,
    [switch]$DisableAutoAnalyze,
    [switch]$OnlyCheck,
    [bool]$AutoInitWhenNeedsInit = $false,
    [switch]$WithEmbeddings,
    [int]$MaxAnalyzeMinutes = 20,
    [bool]$HookManagedNonBlocking = $true
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$worktreeChangedAfterIndexToleranceMs = 1000

function Get-CommandSafe {
    param([string]$Name)
    return Get-Command $Name -ErrorAction SilentlyContinue
}

function ConvertFrom-JsonSafe {
    param(
        [Parameter(Mandatory = $true)]
        [string]$JsonContent
    )
    $convertFromJsonCmd = Get-CommandSafe -Name 'ConvertFrom-Json'
    if ($convertFromJsonCmd -and $convertFromJsonCmd.Parameters.ContainsKey('Depth')) {
        return $JsonContent | ConvertFrom-Json -Depth 8
    }
    return $JsonContent | ConvertFrom-Json
}

function Invoke-Git {
    param(
        [string]$Path,
        [string[]]$GitArgs
    )
    $output = & git -C $Path @GitArgs 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "git command failed: git -C $Path $($GitArgs -join ' ')"
    }
    return (($output | Out-String).Trim())
}

function Get-HookIntegrationStatus {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot
    )

    $hooksDir = Join-Path $RepoRoot '.githooks'
    $postCommitPath = Join-Path $hooksDir 'post-commit'
    $postMergePath = Join-Path $hooksDir 'post-merge'

    $coreHooksPath = $null
    try {
        $configuredHooksPath = & git -C $RepoRoot config --get core.hooksPath 2>$null
        if ($LASTEXITCODE -eq 0) {
            $coreHooksPath = (($configuredHooksPath | Out-String).Trim())
            if ([string]::IsNullOrWhiteSpace($coreHooksPath)) {
                $coreHooksPath = $null
            }
        }
    } catch {
        $coreHooksPath = $null
    }

    function Test-HookRebuildWired {
        param([string]$Path)
        if (-not (Test-Path -LiteralPath $Path)) {
            return $false
        }

        try {
            $content = Get-Content -Raw -LiteralPath $Path
        } catch {
            return $false
        }

        if ([string]::IsNullOrWhiteSpace($content)) {
            return $false
        }

        $normalized = $content.ToLowerInvariant()
        $callsGuard = $normalized -match 'check_gitnexus_index\.ps1' -and $normalized -match '-autoanalyze'
        $callsAnalyzeDirectly = $normalized -match 'gitnexus@latest\s+analyze' -or $normalized -match 'gitnexus\s+analyze'
        $hasPluginMarker = $normalized -match 'gitnexus-index-guard-hook'
        return ($callsGuard -or $callsAnalyzeDirectly -or $hasPluginMarker)
    }

    $coreHooksPathEnabled = $false
    if ($null -ne $coreHooksPath) {
        $normalizedHooksPath = $coreHooksPath.Replace('\\', '/').TrimEnd('/')
        $coreHooksPathEnabled = ($normalizedHooksPath -eq '.githooks')
    }

    $hasHooksDir = Test-Path -LiteralPath $hooksDir
    $hasPostCommit = Test-Path -LiteralPath $postCommitPath
    $hasPostMerge = Test-Path -LiteralPath $postMergePath
    $postCommitWired = Test-HookRebuildWired -Path $postCommitPath
    $postMergeWired = Test-HookRebuildWired -Path $postMergePath

    return [ordered]@{
        hooksDir = $hooksDir
        repoHasHooksDir = [bool]$hasHooksDir
        coreHooksPath = $coreHooksPath
        coreHooksPathEnabled = [bool]$coreHooksPathEnabled
        postCommitPath = $postCommitPath
        postCommitExists = [bool]$hasPostCommit
        postCommitRebuildWired = [bool]$postCommitWired
        postMergePath = $postMergePath
        postMergeExists = [bool]$hasPostMerge
        postMergeRebuildWired = [bool]$postMergeWired
        commitRebuildReady = [bool]($hasHooksDir -and $coreHooksPathEnabled -and $hasPostCommit -and $postCommitWired)
        mergeRebuildReady = [bool]($hasHooksDir -and $coreHooksPathEnabled -and $hasPostMerge -and $postMergeWired)
    }
}

function Get-TimeEstimate {
    param(
        [bool]$NeedsInit,
        [int]$TrackedFileCount,
        [int]$ChangedCommitCount,
        [bool]$EmbeddingLikely
    )

    $level = 'medium'
    $minutes = '3-10'
    $reason = 'default baseline'

    if ($NeedsInit) {
        if ($TrackedFileCount -ge 0 -and $TrackedFileCount -le 2000) {
            $level = 'short'
            $minutes = '1-3'
            $reason = 'first index + small repo'
        } elseif ($TrackedFileCount -gt 2000 -and $TrackedFileCount -le 10000) {
            $level = 'medium'
            $minutes = '3-10'
            $reason = 'first index + medium repo'
        } else {
            $level = 'long'
            $minutes = '10+'
            $reason = 'first index + large repo'
        }
    } else {
        if ($ChangedCommitCount -ge 0 -and $ChangedCommitCount -le 3) {
            $level = 'short'
            $minutes = '1-3'
            $reason = 'few commits since last index'
        } elseif ($ChangedCommitCount -gt 3 -and $ChangedCommitCount -le 30) {
            $level = 'medium'
            $minutes = '3-10'
            $reason = 'moderate commits since last index'
        } elseif ($ChangedCommitCount -gt 30) {
            $level = 'long'
            $minutes = '10+'
            $reason = 'many commits since last index'
        }
    }

    if ($EmbeddingLikely) {
        if ($level -eq 'short') {
            $level = 'medium'
            $minutes = '3-10'
            $reason = "$reason + embeddings"
        } elseif ($level -eq 'medium') {
            $level = 'long'
            $minutes = '10+'
            $reason = "$reason + embeddings"
        } else {
            $reason = "$reason + embeddings"
        }
    }

    return [ordered]@{
        level = $level
        minutes = $minutes
        reason = $reason
    }
}

function Invoke-GitNexusAnalyze {
    param(
        [string]$Root,
        [string[]]$AnalyzeArgs,
        [int]$TimeoutMinutes
    )

    function Start-AnalyzeProcess {
        param(
            [string]$ExePath,
            [string[]]$CmdArgs,
            [string]$WorkingDir,
            [int]$TimeoutMs,
            [hashtable]$EnvironmentVars
        )

        $start = Get-Date
        $startProcessArgs = @{
            FilePath = $ExePath
            ArgumentList = $CmdArgs
            WorkingDirectory = $WorkingDir
            NoNewWindow = $true
            PassThru = $true
        }
        if ($EnvironmentVars -and $EnvironmentVars.Count -gt 0) {
            $startProcessCmd = Get-CommandSafe -Name 'Start-Process'
            if ($startProcessCmd -and $startProcessCmd.Parameters.ContainsKey('Environment')) {
                $startProcessArgs.Environment = $EnvironmentVars
            }
        }
        $process = Start-Process @startProcessArgs
        $completed = $process.WaitForExit($TimeoutMs)
        if (-not $completed) {
            try {
                $process.Kill($true)
            } catch {
                try {
                    $process.Kill()
                } catch {
                    # ignore
                }
            }
            return [ordered]@{
                completed = $false
                timedOut = $true
                exitCode = $null
                durationMs = [int]((Get-Date) - $start).TotalMilliseconds
            }
        }
        return [ordered]@{
            completed = $true
            timedOut = $false
            exitCode = $process.ExitCode
            durationMs = [int]((Get-Date) - $start).TotalMilliseconds
        }
    }

    $timeoutMs = [Math]::Max(1, $TimeoutMinutes) * 60 * 1000
    $gitnexusCommand = Get-CommandSafe -Name 'gitnexus'
    $npxCommand = Get-CommandSafe -Name 'npx'
    if (-not $gitnexusCommand -and -not $npxCommand) {
        throw 'gitnexus command not found in PATH and npx is not available'
    }

    $filePath = $null
    $argumentList = @()
    $retryFilePath = $null
    $retryArgumentList = @()
    $commandType = if ($gitnexusCommand) { [string]$gitnexusCommand.CommandType } else { '' }

    if (-not $gitnexusCommand -and $npxCommand) {
        # Use npx fallback when gitnexus isn't installed in PATH.
        # Use cmd.exe to reliably execute npx.cmd in non-interactive contexts (hooks/automation).
        $filePath = 'cmd.exe'
        $argumentList = @('/c', 'npx', '-y', 'gitnexus@latest') + $AnalyzeArgs
    } elseif ($commandType -eq 'ExternalScript' -and $gitnexusCommand.Path -match '\.ps1$') {
        $pwshPath = Join-Path $PSHOME 'pwsh.exe'
        if (-not (Test-Path -LiteralPath $pwshPath)) {
            $pwshCmd = Get-CommandSafe -Name 'pwsh'
            if ($pwshCmd -and $pwshCmd.Path) {
                $pwshPath = $pwshCmd.Path
            } else {
                $pwshPath = 'powershell.exe'
            }
        }
        $filePath = $pwshPath
        $argumentList = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $gitnexusCommand.Path) + $AnalyzeArgs

        $baseDir = Split-Path -Path $gitnexusCommand.Path -Parent
        $cliPath = Join-Path $baseDir 'node_modules/gitnexus/dist/cli/index.js'
        if (Test-Path -LiteralPath $cliPath) {
            $localNodeExe = Join-Path $baseDir 'node.exe'
            $retryFilePath = if (Test-Path -LiteralPath $localNodeExe) { $localNodeExe } else { 'node' }
            $retryArgumentList = @('--stack_size=65500', $cliPath) + $AnalyzeArgs
        }
    } else {
        $filePath = if ($gitnexusCommand -and $gitnexusCommand.Path) { $gitnexusCommand.Path } else { 'gitnexus' }
        $argumentList = $AnalyzeArgs
    }

    $firstRun = Start-AnalyzeProcess -ExePath $filePath -CmdArgs $argumentList -WorkingDir $Root -TimeoutMs $timeoutMs -EnvironmentVars $null
    $finalRun = $firstRun
    $retryApplied = $false
    $attempts = 1

    if ($firstRun.completed -and -not $firstRun.timedOut -and $firstRun.exitCode -ne 0 -and $retryFilePath -and $retryArgumentList.Count -gt 0) {
        $retryRun = Start-AnalyzeProcess -ExePath $retryFilePath -CmdArgs $retryArgumentList -WorkingDir $Root -TimeoutMs $timeoutMs -EnvironmentVars $null
        $finalRun = $retryRun
        $retryApplied = $true
        $attempts = 2
    }

    return [ordered]@{
        executed = $true
        completed = $finalRun.completed
        timedOut = $finalRun.timedOut
        exitCode = $finalRun.exitCode
        durationMs = $finalRun.durationMs
        attempts = $attempts
        retryApplied = $retryApplied
        firstExitCode = $firstRun.exitCode
    }
}

$startedAt = Get-Date
$autoAnalyzeEnabled = [bool]$AutoAnalyze -and (-not $DisableAutoAnalyze)
if ($OnlyCheck) {
    $autoAnalyzeEnabled = $false
    $AutoInitWhenNeedsInit = $false
}
$result = [ordered]@{
    ok = $false
    repoPath = $null
    repoRoot = $null
    isGitRepo = $false
    isIndexed = $false
    needsInit = $false
    isStale = $false
    worktreeDirty = $false
    worktreeDirtyFileCount = 0
    worktreeChangedAfterIndex = $false
    currentCommit = $null
    indexedCommit = $null
    indexedAt = $null
    changedCommitCount = -1
    trackedFileCount = -1
    embeddingsCount = 0
    recommendedAnalyzeArgs = @()
    estimatedAnalyze = $null
    hookManagedNonBlocking = [bool]$HookManagedNonBlocking
    hookIntegration = [ordered]@{
        hooksDir = $null
        repoHasHooksDir = $false
        coreHooksPath = $null
        coreHooksPathEnabled = $false
        postCommitPath = $null
        postCommitExists = $false
        postCommitRebuildWired = $false
        postMergePath = $null
        postMergeExists = $false
        postMergeRebuildWired = $false
        commitRebuildReady = $false
        mergeRebuildReady = $false
    }
    manualRebuildGate = [ordered]@{
        bypassedByHooks = $false
        reason = ''
    }
    autoAnalyze = [ordered]@{
        requested = [bool]($autoAnalyzeEnabled -or $AutoInitWhenNeedsInit)
        blockedByLongEstimate = $false
        blockedByHookManagedPolicy = $false
        executed = $false
        completed = $null
        timedOut = $false
        exitCode = $null
        durationMs = $null
        attempts = 0
        retryApplied = $false
        firstExitCode = $null
    }
    firstInitConfirmation = [ordered]@{
        required = $false
        question = ''
        suggestedAction = ''
        expectedAnswer = 'yes|no'
    }
    checkDurationMs = 0
    message = ''
}

try {
    if (-not (Get-CommandSafe -Name 'git')) {
        throw 'git command not found in PATH'
    }

    $resolvedPath = (Resolve-Path -LiteralPath $RepoPath).Path
    $result.repoPath = $resolvedPath

    try {
        $repoRoot = Invoke-Git -Path $resolvedPath -GitArgs @('rev-parse', '--show-toplevel')
    } catch {
        throw 'target path is not inside a git repository'
    }

    $result.isGitRepo = $true
    $result.repoRoot = $repoRoot
    $result.currentCommit = Invoke-Git -Path $repoRoot -GitArgs @('rev-parse', 'HEAD')
    $result.hookIntegration = Get-HookIntegrationStatus -RepoRoot $repoRoot

    # working tree dirty detection (covers uncommitted changes)
    $dirtyLines = @()
    try {
        $dirtyLines = & git -C $repoRoot status --porcelain 2>$null
    } catch {
        $dirtyLines = @()
    }
    $result.worktreeDirtyFileCount = [int](($dirtyLines | Measure-Object -Line).Lines)
    $result.worktreeDirty = ($result.worktreeDirtyFileCount -gt 0)

    $dirtyMaxMtimeUtc = $null
    if ($result.worktreeDirty) {
        foreach ($line in $dirtyLines) {
            if ([string]::IsNullOrWhiteSpace($line) -or $line.Length -lt 4) {
                continue
            }
            $pathPart = ($line.Substring(3)).Trim()
            if ([string]::IsNullOrWhiteSpace($pathPart)) {
                continue
            }
            if ($pathPart -match ' -> ') {
                $pathPart = ($pathPart -split ' -> ')[-1].Trim()
            }
            $fullPath = Join-Path $repoRoot $pathPart
            if (-not (Test-Path -LiteralPath $fullPath)) {
                continue
            }
            $mtime = (Get-Item -LiteralPath $fullPath).LastWriteTimeUtc
            if ($null -eq $dirtyMaxMtimeUtc -or $mtime -gt $dirtyMaxMtimeUtc) {
                $dirtyMaxMtimeUtc = $mtime
            }
        }
    }

    $metaPath = Join-Path $repoRoot '.gitnexus\meta.json'
    $meta = $null
    if (Test-Path -LiteralPath $metaPath) {
        $result.isIndexed = $true
        $meta = ConvertFrom-JsonSafe -JsonContent (Get-Content -Raw -LiteralPath $metaPath)
    } else {
        $result.isIndexed = $false
    }

    if ($result.isIndexed -and $null -ne $meta) {
        $metaMtimeUtc = $null
        try {
            $metaMtimeUtc = (Get-Item -LiteralPath $metaPath).LastWriteTimeUtc
        } catch {
            $metaMtimeUtc = $null
        }
        $result.worktreeChangedAfterIndex = $false
        if ($result.worktreeDirty -and $null -ne $dirtyMaxMtimeUtc) {
            if ($null -eq $metaMtimeUtc) {
            $result.worktreeChangedAfterIndex = $true
        } else {
            $result.worktreeChangedAfterIndex = ($dirtyMaxMtimeUtc -gt $metaMtimeUtc.AddMilliseconds($worktreeChangedAfterIndexToleranceMs))
        }
    }

    $result.indexedCommit = [string]$meta.lastCommit
        $result.indexedAt = [string]$meta.indexedAt
        if ($null -ne $meta.stats -and $null -ne $meta.stats.embeddings) {
            $result.embeddingsCount = [int]$meta.stats.embeddings
        }

        if ([string]::IsNullOrWhiteSpace($result.indexedCommit)) {
            $result.isStale = $true
            $result.changedCommitCount = -1
        } else {
            $result.isStale = ($result.currentCommit -ne $result.indexedCommit) -or $result.worktreeChangedAfterIndex
            try {
                $delta = Invoke-Git -Path $repoRoot -GitArgs @('rev-list', '--count', "$($result.indexedCommit)..HEAD")
                $result.changedCommitCount = [int]$delta
            } catch {
                $result.changedCommitCount = -1
            }
        }
    } else {
        $result.needsInit = $true
        $result.isStale = $true
    }

    try {
        $result.trackedFileCount = [int]((& git -C $repoRoot ls-files 2>$null | Measure-Object -Line).Lines)
    } catch {
        $result.trackedFileCount = -1
    }

    $embeddingLikely = $WithEmbeddings -or ($result.embeddingsCount -gt 0)
    $analyzeArgs = @('analyze')
    if ($result.worktreeChangedAfterIndex -and (-not $result.needsInit) -and ($result.currentCommit -eq $result.indexedCommit)) {
        $analyzeArgs += '--force'
    }
    if ($embeddingLikely) {
        $analyzeArgs += '--embeddings'
    }
    $result.recommendedAnalyzeArgs = $analyzeArgs

    $result.estimatedAnalyze = Get-TimeEstimate -NeedsInit $result.needsInit -TrackedFileCount $result.trackedFileCount -ChangedCommitCount $result.changedCommitCount -EmbeddingLikely $embeddingLikely

    $hooksReadyForCommitRefresh = [bool]$result.hookIntegration.commitRebuildReady
    $result.manualRebuildGate.bypassedByHooks = [bool](
        $HookManagedNonBlocking -and
        $hooksReadyForCommitRefresh -and
        (-not $result.needsInit) -and
        $result.isStale
    )
    if ($result.manualRebuildGate.bypassedByHooks) {
        $result.manualRebuildGate.reason = 'repo .githooks is wired for commit-time GitNexus refresh'
    }

    $result.autoAnalyze.blockedByLongEstimate = [bool](
        $autoAnalyzeEnabled -and
        ($result.needsInit -or $result.isStale) -and
        $null -ne $result.estimatedAnalyze -and
        $result.estimatedAnalyze.level -eq 'long'
    )
    $result.autoAnalyze.blockedByHookManagedPolicy = [bool](
        $autoAnalyzeEnabled -and
        $result.manualRebuildGate.bypassedByHooks
    )
    $shouldAutoAnalyze = (
        -not $result.autoAnalyze.blockedByLongEstimate -and
        -not $result.autoAnalyze.blockedByHookManagedPolicy -and
        (($autoAnalyzeEnabled -and ($result.needsInit -or $result.isStale)) -or ($AutoInitWhenNeedsInit -and $result.needsInit))
    )
    if ($shouldAutoAnalyze) {
        $auto = Invoke-GitNexusAnalyze -Root $repoRoot -AnalyzeArgs $analyzeArgs -TimeoutMinutes $MaxAnalyzeMinutes
        $result.autoAnalyze.executed = $auto.executed
        $result.autoAnalyze.completed = $auto.completed
        $result.autoAnalyze.timedOut = $auto.timedOut
        $result.autoAnalyze.exitCode = $auto.exitCode
        $result.autoAnalyze.durationMs = $auto.durationMs
        $result.autoAnalyze.attempts = $auto.attempts
        $result.autoAnalyze.retryApplied = $auto.retryApplied
        $result.autoAnalyze.firstExitCode = $auto.firstExitCode

        if ($auto.completed -and -not $auto.timedOut -and $auto.exitCode -eq 0) {
            $metaPathAfterAnalyze = Join-Path $repoRoot '.gitnexus\meta.json'
            if (Test-Path -LiteralPath $metaPathAfterAnalyze) {
                $metaAfterAnalyze = ConvertFrom-JsonSafe -JsonContent (Get-Content -Raw -LiteralPath $metaPathAfterAnalyze)
                $result.isIndexed = $true
                $result.indexedCommit = [string]$metaAfterAnalyze.lastCommit
                $result.indexedAt = [string]$metaAfterAnalyze.indexedAt
                if ($null -ne $metaAfterAnalyze.stats -and $null -ne $metaAfterAnalyze.stats.embeddings) {
                    $result.embeddingsCount = [int]$metaAfterAnalyze.stats.embeddings
                }
                if (-not [string]::IsNullOrWhiteSpace($result.indexedCommit)) {
                    $result.needsInit = $false

                    # recompute worktree status after analyze (avoid repeated analyze when worktree is dirty but unchanged)
                    $dirtyLinesAfterAnalyze = @()
                    try {
                        $dirtyLinesAfterAnalyze = & git -C $repoRoot status --porcelain 2>$null
                    } catch {
                        $dirtyLinesAfterAnalyze = @()
                    }
                    $result.worktreeDirtyFileCount = [int](($dirtyLinesAfterAnalyze | Measure-Object -Line).Lines)
                    $result.worktreeDirty = ($result.worktreeDirtyFileCount -gt 0)

                    $dirtyMaxMtimeUtcAfterAnalyze = $null
                    if ($result.worktreeDirty) {
                        foreach ($line in $dirtyLinesAfterAnalyze) {
                            if ([string]::IsNullOrWhiteSpace($line) -or $line.Length -lt 4) {
                                continue
                            }
                            $pathPart = ($line.Substring(3)).Trim()
                            if ([string]::IsNullOrWhiteSpace($pathPart)) {
                                continue
                            }
                            if ($pathPart -match ' -> ') {
                                $pathPart = ($pathPart -split ' -> ')[-1].Trim()
                            }
                            $fullPath = Join-Path $repoRoot $pathPart
                            if (-not (Test-Path -LiteralPath $fullPath)) {
                                continue
                            }
                            $mtime = (Get-Item -LiteralPath $fullPath).LastWriteTimeUtc
                            if ($null -eq $dirtyMaxMtimeUtcAfterAnalyze -or $mtime -gt $dirtyMaxMtimeUtcAfterAnalyze) {
                                $dirtyMaxMtimeUtcAfterAnalyze = $mtime
                            }
                        }
                    }

                    $metaMtimeUtcAfterAnalyze = $null
                    try {
                        $metaMtimeUtcAfterAnalyze = (Get-Item -LiteralPath $metaPathAfterAnalyze).LastWriteTimeUtc
                    } catch {
                        $metaMtimeUtcAfterAnalyze = $null
                    }
                    $result.worktreeChangedAfterIndex = $false
                    if ($result.worktreeDirty -and $null -ne $dirtyMaxMtimeUtcAfterAnalyze) {
                        if ($null -eq $metaMtimeUtcAfterAnalyze) {
                            $result.worktreeChangedAfterIndex = $true
                        } else {
                            $result.worktreeChangedAfterIndex = ($dirtyMaxMtimeUtcAfterAnalyze -gt $metaMtimeUtcAfterAnalyze.AddMilliseconds($worktreeChangedAfterIndexToleranceMs))
                        }
                    }

                    $result.isStale = ($result.currentCommit -ne $result.indexedCommit) -or $result.worktreeChangedAfterIndex
                    try {
                        $deltaAfterAnalyze = Invoke-Git -Path $repoRoot -GitArgs @('rev-list', '--count', "$($result.indexedCommit)..HEAD")
                        $result.changedCommitCount = [int]$deltaAfterAnalyze
                    } catch {
                        $result.changedCommitCount = -1
                    }
                }
            }
        }
    }

    if ($result.autoAnalyze.executed -and ($result.autoAnalyze.timedOut -or ($null -ne $result.autoAnalyze.exitCode -and $result.autoAnalyze.exitCode -ne 0))) {
        $result.message = 'analyze execution failed, check autoAnalyze fields'
        $result.ok = $false
    } elseif ($result.needsInit) {
        $result.firstInitConfirmation.required = $true
        $result.firstInitConfirmation.question = 'Detected GitNexus index is not initialized. Run initialization now? (yes/no)'
        $result.firstInitConfirmation.suggestedAction = 'If yes, run: gitnexus analyze (or npx -y gitnexus@latest analyze).'
        if ($result.autoAnalyze.requested -and -not $result.autoAnalyze.executed -and $result.autoAnalyze.blockedByLongEstimate) {
            $result.message = 'Detected GitNexus index is not initialized. Auto-analyze was skipped because estimate is long. Run initialization now? (yes/no)'
        } else {
            $result.message = 'Detected GitNexus index is not initialized. Run initialization now? (yes/no)'
        }
        $result.ok = $true
    } elseif ($result.isStale) {
        if ($result.manualRebuildGate.bypassedByHooks) {
            if ($result.worktreeChangedAfterIndex -and $result.currentCommit -eq $result.indexedCommit) {
                $result.message = 'worktree changed since last index, but repo hooks are wired for refresh on commit/merge (non-blocking)'
            } else {
                $result.message = 'index is stale, but repo hooks are wired for auto refresh on commit/merge (non-blocking)'
            }
        } elseif ($result.worktreeChangedAfterIndex -and $result.currentCommit -eq $result.indexedCommit) {
            $result.message = 'worktree changed since last index, re-analyze recommended'
        } elseif ($result.autoAnalyze.requested -and -not $result.autoAnalyze.executed -and $result.autoAnalyze.blockedByHookManagedPolicy) {
            $result.message = 'index is stale, auto-analyze skipped by hook-managed non-blocking policy'
        } elseif ($result.autoAnalyze.requested -and -not $result.autoAnalyze.executed -and $result.autoAnalyze.blockedByLongEstimate) {
            $result.message = 'index is stale, but auto-analyze skipped because estimate is long'
        } else {
            $result.message = 'index is stale, re-analyze recommended'
        }
        $result.ok = $true
    } else {
        $result.message = 'index is up-to-date'
        $result.ok = $true
    }
} catch {
    $result.message = $_.Exception.Message
    $result.ok = $false
}

$result.checkDurationMs = [int]((Get-Date) - $startedAt).TotalMilliseconds
$result | ConvertTo-Json -Depth 8
