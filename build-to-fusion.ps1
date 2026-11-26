# Copies a new build into Fusion add-in folder.

$name = "snap_generator"

$target_folder = Join-Path $env:APPDATA "Autodesk\Autodesk Fusion 360\API\AddIns\$name"

# Build, overwriting old if necesary
.\build.ps1

if (Test-Path -Path $target_folder) {
    "Target path already exists. Deleting all contents. ($target_folder)"
    Remove-Item -Recurse -Force $target_folder
}

# Copy the current directory to the target folder
"Copying files ..."
Copy-Item -Path (Join-Path "dist" $name) -Destination $target_folder -Recurse -Force
"Finished!"
