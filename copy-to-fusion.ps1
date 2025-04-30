# Copies the project in it's current state into the fusion add-in folder.
# Useful for testing during development.

$manifest = Get-Content -Raw -Path ".\snap-generator.manifest" | ConvertFrom-Json
$version = $manifest.version
$name = "snap_generator_$version"
$target_folder = Join-Path $env:APPDATA "Autodesk\Autodesk Fusion 360\API\AddIns\$name"

# Remove the old target folder if it exists
if (Test-Path -Path $target_folder) {
    "Path already exists. Deleting all contents."
    Remove-Item -Recurse -Force $target_folder
}

# Copy the current directory to the target folder
Copy-Item -Path . -Destination $target_folder -Recurse -Force

# Rename the main script
# Rename-Item -Path "$target_folder/snap_generator.py" "$target_folder/$name"
Rename-Item -Path "$target_folder/snap_generator.py" "$target_folder/$name.py"

# Remove unwanted files/folders as before
$itemsToRemove = @(
    "$target_folder/create_release.ps1",
    "$target_folder/.git",
    "$target_folder/.gitignore",
    "$target_folder/.gitmodules",
    "$target_folder/.idea",
    "$target_folder/.env",
    "$target_folder/apper/.gitignore",
    "$target_folder/apper/.git",
    "$target_folder/apper/docs",
    "$target_folder/build.ps1",
    "$target_folder/copy-to-fusion.ps1"
)

foreach ($item in $itemsToRemove) {
    if (Test-Path -Path $item) {
        Remove-Item -Recurse -Force $item
    }
}
