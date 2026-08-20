# Load Extension in Chrome for Local Testing
# Usage: .\load-extension.ps1

$extensionPath = Join-Path $PSScriptRoot "extension"
$extensionPath = (Resolve-Path $extensionPath).Path

Write-Host "🔧 AI Phishing Detector Extension Loader" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📁 Extension path: $extensionPath" -ForegroundColor Green
Write-Host ""

# Check if extension folder exists
if (-not (Test-Path $extensionPath)) {
    Write-Host "❌ ERROR: Extension folder not found at $extensionPath" -ForegroundColor Red
    exit 1
}

# Check if manifest.json exists
$manifestPath = Join-Path $extensionPath "manifest.json"
if (-not (Test-Path $manifestPath)) {
    Write-Host "❌ ERROR: manifest.json not found" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Extension folder verified" -ForegroundColor Green
Write-Host ""

# Find Chrome installation
$chromePaths = @(
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)

$chromePath = $null
foreach ($path in $chromePaths) {
    if (Test-Path $path) {
        $chromePath = $path
        break
    }
}

if (-not $chromePath) {
    Write-Host "⚠️  Chrome not found. Please:" -ForegroundColor Yellow
    Write-Host "  1. Open Chrome manually" -ForegroundColor Gray
    Write-Host "  2. Go to: chrome://extensions/" -ForegroundColor Gray
    Write-Host "  3. Enable 'Developer mode' (top right)" -ForegroundColor Gray
    Write-Host "  4. Click 'Load unpacked'" -ForegroundColor Gray
    Write-Host "  5. Select this folder: $extensionPath" -ForegroundColor Gray
    Write-Host ""
    Read-Host "Press Enter to continue"
    exit 0
}

Write-Host "✅ Chrome found at: $chromePath" -ForegroundColor Green
Write-Host ""

# Launch Chrome with extension
Write-Host "🚀 Launching Chrome with extension..." -ForegroundColor Cyan
Write-Host ""

# Create a user data directory for testing (isolated from default Chrome profile)
$testDataDir = Join-Path $env:TEMP "chrome-phishing-test"
if (-not (Test-Path $testDataDir)) {
    New-Item -ItemType Directory -Path $testDataDir -Force | Out-Null
}

Write-Host "📋 Quick Test Checklist:" -ForegroundColor Yellow
Write-Host "  [ ] Popup opens without crashing" -ForegroundColor Gray
Write-Host "  [ ] Can analyze a URL (https://google.com)" -ForegroundColor Gray
Write-Host "  [ ] Sidebar opens without crashing" -ForegroundColor Gray
Write-Host "  [ ] Check DevTools (F12) console - NO errors" -ForegroundColor Gray
Write-Host ""

# Start Chrome
try {
    # Note: Chrome doesn't support loading unpacked via command line
    # So we'll just open Chrome to extensions page with instructions
    & $chromePath "chrome://extensions/" | Out-Null

    Write-Host "✅ Chrome opened to extensions page" -ForegroundColor Green
    Write-Host ""
    Write-Host "📖 Steps to load extension:" -ForegroundColor Yellow
    Write-Host "  1. Enable 'Developer mode' (top right toggle)" -ForegroundColor Gray
    Write-Host "  2. Click 'Load unpacked'" -ForegroundColor Gray
    Write-Host "  3. Navigate to: $extensionPath" -ForegroundColor Gray
    Write-Host "  4. Select the 'extension' folder" -ForegroundColor Gray
    Write-Host ""
    Write-Host "🔗 Ready to test! See EXTENSION_TESTING.md for test cases." -ForegroundColor Cyan
} catch {
    Write-Host "❌ Error launching Chrome: $_" -ForegroundColor Red
    exit 1
}
