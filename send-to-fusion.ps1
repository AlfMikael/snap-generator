# Convenience script to copy the build directly into the 
# Fusion 360 add-in folder.
# Only works in Windows (for obvious reasons)

$manifest = Get-Content -Raw -Path ".\snap-generator.manifest" | ConvertFrom-Json
$version = $manifest.version
$subjectFolder = "snap_generator_v$version"
$targetFolder = Join-Path $env:APPDATA "Autodesk\Autodesk Fusion 360\API\AddIns\$subjectFolder"

if (-not (Test-Path $subjectFolder)) {
    Write-Host "No build folder found. Excpected '$subjectFolder'. Building ..."
    .\build.ps1
}

if (Test-Path $targetFolder) {
    Write-Host "Target folder already exists. Deleting ..."
    rm -r $targetFolder
}
cp -r $subjectFolder $targetFolder
Write-Host "Copied $subjectFolder to $targetFolder"