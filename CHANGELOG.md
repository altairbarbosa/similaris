# Changelog

All notable changes to Similaris are documented in this file.

## [Unreleased]

### Added

- Introduced a responsive Fluent/WinUI-inspired interface with dedicated
  navigation for image organization, file conversion, image enhancement, and
  settings.
- Added consistent English, Brazilian Portuguese, and Spanish localization for
  the redesigned interface.
- Added source selection by folder or individual files, explicit destination
  selection, contextual hints, full-path tooltips, and operation-specific
  status messages.
- Added collapsible processing details with elapsed time, percentage, current
  activity, log copying, and quick access to the destination folder.
- Added an English `.env.example` template for local Microsoft Store identity
  settings.
- Added localization-catalog parity and narrow-image regression tests.

### Changed

- Reorganized duplicate detection, rename, conversion, and enhancement options
  into clearer task-oriented cards.
- Improved responsive behavior for narrow windows and compact sidebar mode.
- Replaced the settings text glyph with a full-size navigation icon consistent
  with the rest of the sidebar.
- Replaced platform-native checkboxes, radio buttons, sliders, and dropdowns
  with theme-aware controls that render consistently on Windows.
- Increased button hierarchy, spacing, hit targets, and selected-state clarity.
- Restricted GitHub release automation to the traditional Windows x64 portable
  build.
- Moved Microsoft Store MSIX generation to a local-only PowerShell workflow.
- Updated Store packaging documentation in all three supported languages.

### Fixed

- Prevented OpenCV feature extraction from crashing on images that are only one
  pixel wide or high.
- Added guarded image analysis so malformed or unsupported image data is
  reported without terminating the entire operation.
- Fixed language switching when the native Tk combobox popdown held focus and
  custom controls attempted to resolve that internal window.

### Security and privacy

- Removed Partner Center identity values from the tracked package manifest.
- Store identity values are now loaded from an ignored local `.env` file and
  safely XML-escaped before manifest generation.
- Microsoft Store packages, local environments, and generated build artifacts
  remain excluded from source control.
