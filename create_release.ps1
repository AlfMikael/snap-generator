# Script that clones the repo with git, and then removes
# the things that are unneeded and unwanted for a release.

$version = "v0.2.1"
$source_repo = "git@github.com:AlfMikael/snap-generator.git"
$name = "snap-generator-$version"
$target_folder = "../$name"
$branch = "with_cadquery"

if (Test-Path -Path $target_folder) {
    "Path already exists. Deleting all contents."
    rm -r -fo $target_folder
}
git clone --recurse-submodules --depth 1 -b $branch $source_repo $target_folder

rename-item -Path "$target_folder/snap-generator.py" "$($name).py"
rm $target_folder/create_release.ps1
rm -r -fo $target_folder/.git
rm -r -fo $target_folder/.gitignore
rm -r -fo $target_folder/.gitmodules
rm -r -fo $target_folder/.idea
rm -r -fo $target_folder/.env
rm -r -fo $target_folder/apper/.gitignore
rm -r -fo $target_folder/apper/.git
rm -r -fo $target_folder/apper/docs

