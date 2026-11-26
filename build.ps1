# build.ps1
# Prepares a clean build
# - Clones the repo
# - Packages the add-in in a stable folder
# - Removes dev and VCS files

$source_repo = "."
$name = "snap_generator"
$target_folder = Join-Path "dist" $name

if (Test-Path -Path $target_folder) {
    "Path already exists. Deleting all contents."
    Remove-Item -Recurse -Force $target_folder
}
"Building ..."
git clone --recurse-submodules $source_repo $target_folder
if ($LASTEXITCODE -ne 0) { throw "Could not clone the add-in and its submodules." }
$manifest = Get-Content -Raw "$target_folder/snap_generator.manifest" | ConvertFrom-Json -AsHashtable
$version = $manifest.version
$archive = Join-Path "dist" "${name}_$version.zip"

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
Compress-Archive -Path $target_folder -DestinationPath $archive -Force -ErrorAction Stop
"Built $archive"
