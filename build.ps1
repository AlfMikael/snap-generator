# build.ps1
# Prepares a clean build
# - Clones the repo
# - Renames files
# - Removes dev and VCS files

$manifest = Get-Content -Raw -Path ".\snap_generator.manifest" | ConvertFrom-Json -AsHashtable
$version = $manifest.version
$source_repo = "."
$name = "snap_generator_$version"
$target_folder = "$name"

if (Test-Path -Path $target_folder) {
    "Path already exists. Deleting all contents."
    Remove-Item -Recurse -Force $target_folder
}
"Building ..."
git clone --recurse-submodules --depth 1 $source_repo $target_folder
Rename-Item -Path "$target_folder/snap_generator.py" "$name.py"
Rename-Item -Path "$target_folder/snap_generator.manifest" "$target_folder/$name.manifest"

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
    "$target_folder/build-to-fusion.ps1",
    "$target_folder/copy-to-fusion.ps1"

)

foreach ($item in $itemsToRemove) {
    if (Test-Path -Path $item) {
        Remove-Item -Recurse -Force $item
    }
}