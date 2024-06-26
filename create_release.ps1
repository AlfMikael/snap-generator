# Script that clones the repo with git, and then removes
# the things that are unneeded and unwanted for a release.

$version = "v0.3.1"
$source_repo = "."
$name = "snap_generator_$version"
$target_folder = "../$name"

if (Test-Path -Path $target_folder) {
    "Path already exists. Deleting all contents."
    rm -r -fo $target_folder
}
git clone --recurse-submodules --depth 1 $source_repo $target_folder
rename-item -Path "$target_folder/snap_generator.py" "$name.py"

rm $target_folder/create_release.ps1
rm -r -fo $target_folder/.git
rm -r -fo $target_folder/.gitignore
rm -r -fo $target_folder/.gitmodules
rm -r -fo $target_folder/.idea
rm -r -fo $target_folder/.env
rm -r -fo $target_folder/apper/.gitignore
rm -r -fo $target_folder/apper/.git
rm -r -fo $target_folder/apper/docs

