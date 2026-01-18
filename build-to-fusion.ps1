# Copies a new build into Fusion add-in folder.

$manifest = Get-Content -Raw -Path ".\snap_generator.manifest" | ConvertFrom-Json -AsHashtable
$version = $manifest.version
$name = "snap_generator_$version"

$subject_folder = Join-Path $env:APPDATA "Autodesk\Autodesk Fusion 360\API\AddIns\$name"
$target_folder = Join-Path $env:APPDATA "Autodesk\Autodesk Fusion 360\API\AddIns\$name"

# Build, overwriting old if necesary
.\build.ps1

if (Test-Path -Path $target_folder) {
    "Target path already exists. Deleting all contents. ($target_folder)"
    Remove-Item -Recurse -Force $target_folder
}

# Copy the current directory to the target folder
"Copying files ..."
Copy-Item -Path $name -Destination $target_folder -Recurse -Force
"Finished!"
