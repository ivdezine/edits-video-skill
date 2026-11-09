# Changelog

Notable changes to this skill, newest first. Versions follow [Semantic Versioning](https://semver.org/).
Each version's full notes are on the [releases page](https://github.com/ivdezine/edits-video-skill/releases).
Dates are US Eastern.

## [1.1.1] - 2026-11-09

Beat-synced cuts are now checked, not assumed. Tested against Edits 454.0.0 (`metapilot-native`
1.0.0) on 2026-11-09.

### Added

- A read-back step in the beat-synced cut recipe (`references/recipes.md`). After `splitAt`, read
  the main track with `elements`, compare each piece's `startTime` with its beat, and flag any cut
  more than half a frame off. A second check reports gaps between neighboring pieces.
- `SKILL.md` step 6 points at that check: frames verify the picture, the read-back verifies timing.
- `CHANGELOG.md`, and a Releases section in the README.

### Fixed

- The recipe read beats from `beats[]`; `beatMarkers` returns them under `markers[]`, and
  `beatCount` is the densest-setting total, not the number returned.
- `SKILL.md` said the audio analysis tools work on imported audio. On imported music,
  `beatMarkers` finds no beats and `audioOnsets` failed, so beat-synced cuts need catalog music or
  hand-placed markers.
- `references/conventions-and-gotchas.md` records both, plus the sub-frame sliver a split can
  leave between pieces.

## [1.1.0] - 2026-11-08

### Added

- A triage section in `SKILL.md`, "When a tool is missing or a call fails", that tells apart an
  unreachable server, the wrong app screen, and a session whose tool list is stale, with the fix
  for each.
- `python3 scripts/mcp_client.py doctor`, which checks the connection, the screen and the tool
  count, then prints which case applies.
- The exact error each fault produces, in `references/conventions-and-gotchas.md`.

### Changed

- The command-line client exits with one plain sentence instead of a Python traceback when it
  cannot connect.

## [1.0.0] - 2026-11-08

First release. Tested against Edits 454.0.0 (`metapilot-native` 1.0.0) on 2026-11-08.

### Added

- `SKILL.md`: the workflow, the catalog apply tools, and the rules that bite.
- `references/conventions-and-gotchas.md`: units, coordinates, schema traps and measured timings.
- `references/recipes.md`: 24 call sequences for common edits, 19 tested end to end.
- `scripts/mcp_client.py`: a dependency-free Python client for the server.
- `scripts/build_references.py`: generates the tool reference and catalog ids from your installed
  version.

[1.1.1]: https://github.com/ivdezine/edits-video-skill/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/ivdezine/edits-video-skill/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/ivdezine/edits-video-skill/releases/tag/v1.0.0
