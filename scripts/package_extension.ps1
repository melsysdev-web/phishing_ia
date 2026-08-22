<#
.SYNOPSIS
    Empaqueta extension/ en un ZIP subible a Edge Add-ons / Chrome Web Store.

.DESCRIPTION
    Existe porque el ZIP 1.0.4 se armo a mano y salio roto de cuatro formas a la
    vez: manifest.json bajo extension/ en vez de en la raiz, sin config.js, con
    la URL apuntando a localhost y sin el host del backend en host_permissions.
    Ninguno de los cuatro se ve inspeccionando el codigo fuente -- solo se ven
    en el paquete. Cada validacion de aqui corresponde a uno de esos fallos.

.EXAMPLE
    venv\Scripts\python -c "pass"; .\scripts\package_extension.ps1
    .\scripts\package_extension.ps1 -OutDir dist
#>
[CmdletBinding()]
param(
    [string]$SourceDir = "extension",
    [string]$OutDir    = "."
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.IO.Compression.FileSystem

$repoRoot = Split-Path -Parent $PSScriptRoot
$src      = Join-Path $repoRoot $SourceDir
$errors   = New-Object System.Collections.ArrayList

function Fail($msg) { [void]$errors.Add($msg); Write-Host "  [FALLO] $msg" -ForegroundColor Red }
function Ok($msg)   { Write-Host "  [OK] $msg" -ForegroundColor Green }

Write-Host "`nEmpaquetando extension" -ForegroundColor Cyan
Write-Host "Origen: $src`n"

if (-not (Test-Path $src)) { throw "No existe el directorio de origen: $src" }

# --- 1. manifest valido -----------------------------------------------------
$manifestPath = Join-Path $src "manifest.json"
if (-not (Test-Path $manifestPath)) { throw "No hay manifest.json en $src" }

try   { $manifest = Get-Content $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json }
catch { throw "manifest.json no es JSON valido: $($_.Exception.Message)" }

$version = $manifest.version
if ([string]::IsNullOrWhiteSpace($version)) { throw "manifest.json sin campo version" }
Ok "manifest.json valido (version $version)"

# --- 2. archivos referenciados por el manifest existen ----------------------
$refs = @()
if ($manifest.background.service_worker) { $refs += $manifest.background.service_worker }
if ($manifest.action.default_popup)      { $refs += $manifest.action.default_popup }
if ($manifest.side_panel.default_path)   { $refs += $manifest.side_panel.default_path }
foreach ($p in $manifest.icons.PSObject.Properties) { $refs += $p.Value }

foreach ($r in $refs) {
    if (Test-Path (Join-Path $src $r)) { Ok "referencia del manifest: $r" }
    else { Fail "el manifest referencia '$r' pero el archivo no existe" }
}

# --- 3. config.js presente y coherente --------------------------------------
# Fallo real del ZIP 1.0.4: config.js no entro, y sin el ni el service worker
# (importScripts) ni los HTML (<script src>) arrancan.
$configPath = Join-Path $src "config.js"
if (-not (Test-Path $configPath)) {
    Fail "falta config.js -- el service worker y los HTML lo cargan, sin el la extension no arranca"
} else {
    $config = Get-Content $configPath -Raw -Encoding UTF8
    Ok "config.js presente"

    if ($config -match 'BACKEND_DEFAULT_URL\s*=\s*"([^"]*)"') {
        $url = $Matches[1]
        if ($url -match 'localhost|127\.0\.0\.1') {
            Fail "BACKEND_DEFAULT_URL apunta a '$url' -- un usuario final no tiene backend local"
        } elseif ($url -notmatch '^https://') {
            Fail "BACKEND_DEFAULT_URL no es https: '$url'"
        } else {
            Ok "BACKEND_DEFAULT_URL = $url"

            # 4. ese host debe estar declarado en host_permissions
            $hostOk = $false
            foreach ($h in $manifest.host_permissions) {
                if ($h -like "$url/*" -or $url -like ($h -replace '\*$','') + '*') { $hostOk = $true }
            }
            if ($hostOk) { Ok "host declarado en host_permissions" }
            else { Fail "host_permissions no declara $url" }
        }
    } else { Fail "no se encontro BACKEND_DEFAULT_URL en config.js" }

    # Clave vacia solo vale si el backend publico esta declarado a proposito.
    # Vacia y sin declarar es el caso que da 403 en todos los analisis.
    $isPublic = $config -match 'BACKEND_IS_PUBLIC\s*=\s*true'
    $keyEmpty = $config -match 'BACKEND_DEFAULT_API_KEY\s*=\s*""'

    if ($keyEmpty -and $isPublic) {
        Ok "backend publico declarado (BACKEND_IS_PUBLIC) -- sin X-API-Key, coherente"
        Write-Host "       recuerda: Render necesita ALLOW_UNAUTHENTICATED=true y API_KEY vacia" -ForegroundColor Yellow
    } elseif ($keyEmpty) {
        Fail "BACKEND_DEFAULT_API_KEY vacia sin declarar BACKEND_IS_PUBLIC -- todo analisis dara 403"
    } elseif ($isPublic) {
        Fail "BACKEND_IS_PUBLIC=true pero hay una clave definida -- decide un modelo u otro"
    } else { Ok "BACKEND_DEFAULT_API_KEY definida" }
}

# --- 5. scripts referenciados desde HTML e importScripts existen ------------
Get-ChildItem $src -Recurse -Include *.html, *.js | ForEach-Object {
    $file    = $_
    $content = Get-Content $file.FullName -Raw -Encoding UTF8
    $found   = [regex]::Matches($content, '(?:<script[^>]+src="([^"]+)"|importScripts\(([^)]+)\))')
    foreach ($m in $found) {
        $raw = if ($m.Groups[1].Success) { @($m.Groups[1].Value) }
               else { [regex]::Matches($m.Groups[2].Value, "'([^']+)'") | ForEach-Object { $_.Groups[1].Value } }
        foreach ($ref in $raw) {
            if ($ref -match '^https?://') { continue }
            $target = Join-Path $file.DirectoryName $ref
            if (-not (Test-Path $target)) {
                Fail "$($file.Name) carga '$ref' y no existe en el paquete"
            }
        }
    }
}
Ok "referencias de <script src> e importScripts resueltas"

# --- 5b. codigo remoto ------------------------------------------------------
# Manifest V3 prohibe cargar codigo remoto y las tiendas rechazan por ello de
# forma automatica. La CSP ademas lo bloquea en ejecucion, asi que un <script
# src="https://..."> no funciona Y provoca el rechazo.
Get-ChildItem $src -Recurse -Include *.html | ForEach-Object {
    $c = Get-Content $_.FullName -Raw -Encoding UTF8
    foreach ($m in [regex]::Matches($c, '<script[^>]+src="(https?://[^"]+)"')) {
        Fail "$($_.Name) carga codigo remoto: $($m.Groups[1].Value) -- Manifest V3 lo prohibe"
    }
}
Ok "sin codigo remoto"

if ($errors.Count -gt 0) {
    Write-Host "`n$($errors.Count) problema(s). No se genera el ZIP.`n" -ForegroundColor Red
    exit 1
}

# --- 6. construir el ZIP con el manifest EN LA RAIZ -------------------------
# CreateFromDirectory mete el CONTENIDO del directorio en la raiz del ZIP.
# Empaquetar la carpeta extension/ en su lugar es lo que hacia que la tienda
# respondiera "Manifest file is missing or unreadable".
# -OutDir admite tanto una ruta relativa al repo como una absoluta; sin esta
# distincion, Join-Path concatena las dos y produce una ruta invalida.
if ([System.IO.Path]::IsPathRooted($OutDir)) {
    $outPath = $OutDir
} else {
    $outPath = Join-Path $repoRoot $OutDir
}
if (-not (Test-Path $outPath)) { New-Item -ItemType Directory -Path $outPath | Out-Null }
$zip = Join-Path $outPath "ai-phishing-detector-$version.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }

[System.IO.Compression.ZipFile]::CreateFromDirectory(
    $src, $zip, [System.IO.Compression.CompressionLevel]::Optimal, $false)

# --- 7. verificar el ZIP ya construido, no la carpeta ----------------------
$archive = [System.IO.Compression.ZipFile]::OpenRead($zip)
try {
    $names = $archive.Entries | ForEach-Object { $_.FullName }
    if ($names -notcontains "manifest.json") {
        Remove-Item $zip -Force
        throw "manifest.json no quedo en la raiz del ZIP -- la tienda lo rechazaria"
    }
    if ($names -notcontains "config.js") {
        Remove-Item $zip -Force
        throw "config.js no entro en el ZIP"
    }
    Write-Host "`n[OK] ZIP verificado: manifest.json y config.js en la raiz" -ForegroundColor Green
    Write-Host "     $($names.Count) archivos, $([math]::Round((Get-Item $zip).Length/1KB,1)) KB"
} finally { $archive.Dispose() }

Write-Host "`nPaquete listo: $zip`n" -ForegroundColor Cyan
Write-Host "Siguiente paso: descomprimirlo en una carpeta limpia y cargarlo con"
Write-Host "edge://extensions -> Cargar desempaquetada. Probar desde el ZIP, no"
Write-Host "desde extension/, que es lo que oculto los fallos del 1.0.4.`n"
