# Project format

Project files use the .eliav extension and contain UTF-8 JSON.

Top-level fields:

- format: must equal eli_lab_av_translation.
- schema_version: current version is 1.
- project: project metadata such as name.
- composition: canvas dimensions, frame rate, background and ordered layers.
- decks: deck ids, media paths, loop state and collection references.

A project stores references to footage, not the footage itself. Media paths are absolute in the first implementation. Missing files are logged when loading; relinking UI is planned for a later M1 refinement.

Writes are atomic: data is serialized to a sibling temporary file and moved into place only after the write completes.
