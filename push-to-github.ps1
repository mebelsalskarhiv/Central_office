# ========================================
# Universal GitHub Push Script
# ========================================

param(
    [string]$RepoName = "",
    [string]$RepoDescription = "",
    [switch]$Private = $false
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  GitHub Push Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

function Test-Command {
    param($Command)
    try {
        if (Get-Command $Command -ErrorAction Stop) {
            return $true
        }
    }
    catch {
        return $false
    }
}

Write-Host "[1/7] Checking Git..." -ForegroundColor Yellow
if (-not (Test-Command "git")) {
    Write-Host "[ERROR] Git not installed!" -ForegroundColor Red
    Write-Host "Download from: https://git-scm.com/download/win" -ForegroundColor Red
    pause
    exit 1
}
Write-Host "[OK] Git installed" -ForegroundColor Green
Write-Host ""

Write-Host "[2/7] Checking GitHub CLI..." -ForegroundColor Yellow
if (-not (Test-Command "gh")) {
    Write-Host "[WARNING] GitHub CLI not installed!" -ForegroundColor Yellow
    Write-Host "Installing GitHub CLI via winget..." -ForegroundColor Yellow

    if (Test-Command "winget") {
        winget install --id GitHub.cli --silent
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

        if (-not (Test-Command "gh")) {
            Write-Host "[ERROR] Failed to install GitHub CLI automatically" -ForegroundColor Red
            Write-Host "Install manually from: https://cli.github.com/" -ForegroundColor Red
            Write-Host "After installation, restart PowerShell and run this script again" -ForegroundColor Yellow
            pause
            exit 1
        }
    }
    else {
        Write-Host "[ERROR] winget not found" -ForegroundColor Red
        Write-Host "Install GitHub CLI manually from: https://cli.github.com/" -ForegroundColor Red
        pause
        exit 1
    }
}
Write-Host "[OK] GitHub CLI installed" -ForegroundColor Green
Write-Host ""

Write-Host "[3/7] Checking GitHub authentication..." -ForegroundColor Yellow
$authStatus = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARNING] You are not authenticated with GitHub" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Browser will open for authentication..." -ForegroundColor Cyan
    Write-Host "Follow instructions in terminal and browser" -ForegroundColor Cyan
    Write-Host ""
    pause

    gh auth login --web --git-protocol https

    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Authentication failed" -ForegroundColor Red
        pause
        exit 1
    }
}
Write-Host "[OK] Authentication successful" -ForegroundColor Green
Write-Host ""

$githubUser = gh api user --jq .login
Write-Host "GitHub user: $githubUser" -ForegroundColor Cyan
Write-Host ""

Write-Host "[4/7] Repository setup..." -ForegroundColor Yellow

if ([string]::IsNullOrEmpty($RepoName)) {
    $currentDir = Split-Path -Leaf (Get-Location)
    $RepoName = Read-Host "Enter repository name (default: $currentDir)"
    if ([string]::IsNullOrEmpty($RepoName)) {
        $RepoName = $currentDir
    }
}

if ([string]::IsNullOrEmpty($RepoDescription)) {
    $RepoDescription = Read-Host "Enter repository description (optional)"
}

$visibility = "public"
if ($Private) {
    $visibility = "private"
}
else {
    $visibilityChoice = Read-Host "Public or private repository? (public/private, default: public)"
    if ($visibilityChoice -eq "private") {
        $visibility = "private"
    }
}

Write-Host ""
Write-Host "Repository name: $RepoName" -ForegroundColor Cyan
Write-Host "Description: $RepoDescription" -ForegroundColor Cyan
Write-Host "Visibility: $visibility" -ForegroundColor Cyan
Write-Host ""

$confirm = Read-Host "Continue? (y/n)"
if ($confirm -ne "y") {
    Write-Host "Cancelled by user" -ForegroundColor Yellow
    exit 0
}
Write-Host ""

Write-Host "[5/7] Initializing Git..." -ForegroundColor Yellow
if (-not (Test-Path ".git")) {
    git init
    Write-Host "[OK] Git repository initialized" -ForegroundColor Green

    if (-not (Test-Path ".gitignore")) {
        Write-Host "Creating basic .gitignore..." -ForegroundColor Yellow
        @"
# Python
__pycache__/
*.py[cod]
venv/
env/
.env

# Node
node_modules/

# IDE
.vscode/
.idea/

# Logs
logs/
*.log

# OS
.DS_Store
Thumbs.db
"@ | Out-File -FilePath ".gitignore" -Encoding UTF8
        Write-Host "[OK] .gitignore created" -ForegroundColor Green
    }
}
else {
    Write-Host "[OK] Git repository already exists" -ForegroundColor Green
}
Write-Host ""

Write-Host "[6/7] Adding files to Git..." -ForegroundColor Yellow

$status = git status --porcelain
if ([string]::IsNullOrEmpty($status)) {
    Write-Host "[INFO] No changes to commit" -ForegroundColor Yellow
}
else {
    git add .

    $commitMessage = Read-Host "Enter commit message (default: 'Initial commit')"
    if ([string]::IsNullOrEmpty($commitMessage)) {
        $commitMessage = "Initial commit"
    }

    git commit -m $commitMessage
    Write-Host "[OK] Files committed" -ForegroundColor Green
}
Write-Host ""

Write-Host "[7/7] Pushing to GitHub..." -ForegroundColor Yellow

$repoExists = gh repo view "$githubUser/$RepoName" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "[WARNING] Repository $githubUser/$RepoName already exists" -ForegroundColor Yellow
    $overwrite = Read-Host "Use existing repository? (y/n)"
    if ($overwrite -ne "y") {
        Write-Host "Cancelled by user" -ForegroundColor Yellow
        exit 0
    }

    $remotes = git remote
    if ($remotes -notcontains "origin") {
        git remote add origin "https://github.com/$githubUser/$RepoName.git"
    }
}
else {
    Write-Host "Creating repository on GitHub..." -ForegroundColor Yellow

    $createArgs = @("repo", "create", $RepoName, "--$visibility", "--source=.", "--remote=origin")
    if (-not [string]::IsNullOrEmpty($RepoDescription)) {
        $createArgs += "--description"
        $createArgs += $RepoDescription
    }

    & gh @createArgs

    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to create repository" -ForegroundColor Red
        pause
        exit 1
    }
}

$currentBranch = git branch --show-current
if ([string]::IsNullOrEmpty($currentBranch)) {
    $currentBranch = "main"
    git branch -M main
}

Write-Host "Pushing code to GitHub..." -ForegroundColor Yellow
git push -u origin $currentBranch

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to push code to GitHub" -ForegroundColor Red
    pause
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  SUCCESS!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Repository created and code pushed!" -ForegroundColor Green
Write-Host ""
Write-Host "Repository URL:" -ForegroundColor Cyan
Write-Host "https://github.com/$githubUser/$RepoName" -ForegroundColor White
Write-Host ""
Write-Host "Open in browser? (y/n)" -ForegroundColor Yellow
$openBrowser = Read-Host
if ($openBrowser -eq "y") {
    Start-Process "https://github.com/$githubUser/$RepoName"
}

Write-Host ""
Write-Host "Done!" -ForegroundColor Green
pause
