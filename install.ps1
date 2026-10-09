# Install pool-keeper for Codex and/or Claude Code (user level) on Windows, from a clone of
# this repo: links skills\pool-keeper into the agents' skill folders (directory junctions, no
# admin rights needed). Standard library Python only: there is no environment to create.
#
#   .\install.ps1                 # codex + claude
#   .\install.ps1 -Targets codex  # only Codex   (%USERPROFILE%\.codex\skills\pool-keeper)
#   .\install.ps1 -Targets claude # only Claude  (%USERPROFILE%\.claude\skills\pool-keeper)
#
# Claude Code users can also install it as a plugin instead (see README).
param([string[]]$Targets = @("codex", "claude"))
$ErrorActionPreference = "Stop"
$src = Join-Path $PSScriptRoot "skills\pool-keeper"

foreach ($t in $Targets) {
    switch ($t) {
        "codex"  { $base = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }; $dest = Join-Path $base "skills\pool-keeper" }
        "claude" { $dest = Join-Path $HOME ".claude\skills\pool-keeper" }
        default  { throw "unknown target: $t (use codex or claude)" }
    }
    New-Item -ItemType Directory -Force (Split-Path $dest) | Out-Null
    if (Test-Path $dest) {
        $item = Get-Item $dest -Force
        if (-not ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            Write-Host "skip ${t}: $dest exists and is not a link (remove it first)"; continue
        }
        $item.Delete()
    }
    New-Item -ItemType Junction -Path $dest -Target $src | Out-Null
    Write-Host "linked $dest -> $src"
}

python (Join-Path $src "pk.py") doctor
Write-Host "`nDone. Open your agent anywhere and say: set up pool-keeper (or attach your CV)."
