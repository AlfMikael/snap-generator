# Changelog
## [0.4.1]
- Fix format on manifest file
- Fix Build scripts 

## [0.4.0]
- Added and improved build-scripts to make testing more efficient.
- Changed location of config-files to the add-in folder #17.
- Cleaned up some spagetti- and unused code.
- Zero (gap) default profiles are now properly zero in all dimensions.
- Fixed bug which which caused error on Mac #14.
- Fixed various bugs that caused errors when trying to load config files.
- Fixed README file. It now more accurately reflects the state of the project.
- Changelog no longer follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

## [0.3.2]
- The new Fusion update included the Ground to Parent feature. This is disabled to prevent it from interfering with creating joints.

## [0.3.1]
- For Pin: When not performing a cut, also include a negative body, so that a manual cut can be performed in the future. This way a specific Pin may be saved and used for later, without having to re-generate it.
- For Pin: Added a positive body around the pin, which serves as the scaffolding. That way, it is no longer necessary to manually ensure that there is enough material to make a mating slot for the pin.
- For Pin: It is now more complicated to cut into bodies. Only two bodies can be cut into, and the ordering is not arbitrary. An illustrative blue and yellow line is now drawn by the pin geometry to help identify which bodies to select where.
- For Cantilever and SimpleCantilever: Altered the geometry function to align with the Pin.


## [0.3.0]
- Added 2 new commands, which are simplifications of the Cantilever and Pin
- Added a Settings command with two primary features
  - Easy access to, and ability to reset saved profiles
  - Ability to selectively disable commands, so they don't appear in the drop-down menu.
- Changed the algorithm for the Pin so that the legs become closer together, especially for small pins. This comes at the cost of limiting the largest possible gap in the thickness direction.
- Added the 'size' parameter to the Cantilever command to provide automatic scaling by a single parameter, for ease of use. The size parameter is now used in all commands.
  

## [0.2.1]
- Fixed a file handling bug which broke the application.

## [0.2.0]

### Added
- Changelog.
- New UI elements: Meaningful tooltip and tooltip image.

### Changed
- Slight modification of Cantilever shape.
- Ui relocation, now in a dropdown menu in SolidCreatePanel.
- Logs and config files moved to the right place, away from addin root.
- Changed the way CantileverPin scales as a function of size.

## [0.1.2-alpha] - 2021-08-01

### Fixed
- Bug in Cantilever feature when closing designs.

## [0.1.1-alpha] - 2021-07-31

## [0.1.0-alpha] - 2021-07-27
- Feature: Cantilever
- Feature: Cantilever Pin
- Everything around that is needed to implement these two features.


[0.4.1]: https://github.com/AlfMikael/snap-generator/compare/0.4.0...0.4.1
[0.4.0]: https://github.com/AlfMikael/snap-generator/compare/0.3.2...0.4.0
[0.3.2]: https://github.com/AlfMikael/snap-generator/compare/0.3.1...0.3.2
[0.3.1]: https://github.com/AlfMikael/snap-generator/compare/0.3.0...0.3.1
[0.3.0]: https://github.com/AlfMikael/snap-generator/compare/0.2.1...0.3.0
[0.2.1]: https://github.com/AlfMikael/snap-generator/compare/0.2.0...0.2.1
[0.2.0]: https://github.com/AlfMikael/snap-generator/compare/v0.1.2-alpha...0.2.0
[0.1.2-alpha]: https://github.com/AlfMikael/snap-generator/compare/v0.1.1-alpha...v0.1.2-alpha
[0.1.1-alpha]: https://github.com/AlfMikael/snap-generator/compare/v0.1.1-alpha...v0.1.2-alpha
[0.1.0-alpha]: https://github.com/AlfMikael/snap-generator/releases/tag/v0.1.0-alpha





