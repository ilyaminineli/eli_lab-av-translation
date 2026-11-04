# Project format

Project files use the .eliav extension and contain UTF-8 JSON.

Top-level fields:

- format: must equal eli_lab_av_translation.
- schema_version: current version is 2.
- project: project metadata such as name.
- composition: canvas dimensions, frame rate, background and ordered layers.
- decks: deck IDs, media paths, segment in/out points, loop state and collection references.
- app_state.effects: master effect values and selected look.
- app_state.automation_settings: cut timing, segment length, loop probability and automatic variation settings.

Version 2 remains backward-compatible with version 1 projects. Missing effect and automation settings use application defaults.

A project stores references to footage, not the footage itself. Media paths are absolute in the first implementation. Missing files are logged when loading.

Writes are atomic: data is serialized to a sibling temporary file and moved into place only after the write completes.
