[CmdletBinding()]
param(
  [switch]$KeepServices,
  [switch]$SkipBackend,
  [switch]$SkipBuild,
  [switch]$SkipE2E,
  [switch]$SkipServices
)

$ErrorActionPreference = "Stop"
$script:failures = [System.Collections.Generic.List[string]]::new()

function Invoke-Gate {
  param(
    [Parameter(Mandatory)] [string]$Name,
    [Parameter(Mandatory)] [scriptblock]$Command
  )

  Write-Host "`n==> $Name" -ForegroundColor Cyan
  & $Command
  $exitCode = $LASTEXITCODE
  if ($exitCode -ne 0) {
    $script:failures.Add("$Name (exit $exitCode)")
    throw "Gate failed: $Name (exit $exitCode)"
  }
}

$root = (& git rev-parse --show-toplevel).Trim()
if (-not $root) {
  throw "Run this script from inside the Talaqi Git worktree."
}
Set-Location $root

$stackWasRunning = $true
if ($SkipServices) {
  if (-not $SkipBackend) {
    throw "-SkipServices requires -SkipBackend because API tests need the disposable database."
  }
} else {
  $existingServices = @(& docker compose ps -q)
  if ($LASTEXITCODE -ne 0) {
    throw "Docker Compose is required for the disposable PostgreSQL test stack. Use -SkipServices -SkipBackend only for static/frontend-only checks."
  }
  $stackWasRunning = $existingServices.Count -gt 0
}

try {
  Invoke-Gate "Install locked JavaScript dependencies" { corepack pnpm install --frozen-lockfile }
  Invoke-Gate "Sync locked Python dependencies" { python -m uv sync --frozen }
  if (-not $SkipServices) {
    Invoke-Gate "Start disposable test services" { docker compose up -d --wait }
    Invoke-Gate "Upgrade the disposable database" { python -m uv run alembic upgrade head }
    Invoke-Gate "Check one Alembic head" {
      $heads = @(& python -m uv run alembic heads)
      if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
      if ($heads.Count -ne 1) {
        Write-Error "Expected exactly one Alembic head; found $($heads.Count)."
        exit 1
      }
    }
  }
  Invoke-Gate "Check JavaScript formatting" { corepack pnpm format:check }
  Invoke-Gate "Lint JavaScript" { corepack pnpm lint }
  Invoke-Gate "Type-check TypeScript" { corepack pnpm typecheck }
  Invoke-Gate "Check Python formatting" { python -m uv run ruff format --check . }
  Invoke-Gate "Lint Python" { python -m uv run ruff check . }
  Invoke-Gate "Type-check Python" { python -m uv run pyright }
  Invoke-Gate "Check OpenAPI drift" { corepack pnpm openapi:check }

  if (-not $SkipBackend) {
    Invoke-Gate "Run API and worker tests" { python -m uv run pytest -q }
  }
  Invoke-Gate "Run JavaScript tests" { corepack pnpm test }

  if (-not $SkipBuild) {
    Invoke-Gate "Build web production bundle with webpack" {
      corepack pnpm --filter @talaqi/web exec next build --webpack
    }
  }
  if (-not $SkipE2E) {
    Invoke-Gate "Run serial Playwright journeys" { corepack pnpm e2e }
  }

  Write-Host "`nRelease preflight passed." -ForegroundColor Green
}
catch {
  Write-Error $_
  exit 1
}
finally {
  if (-not $SkipServices -and -not $KeepServices -and -not $stackWasRunning) {
    Write-Host "`nStopping disposable test services." -ForegroundColor DarkGray
    & docker compose down
  }
}
