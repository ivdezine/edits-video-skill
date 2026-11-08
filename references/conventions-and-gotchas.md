# Conventions and gotchas

Everything here was measured against the live server (Edits for macOS, metapilot-native 1.0.0) on
2026-11-08, on a copy of the bundled Example project. Where a later app version disagrees, the live
server wins: rerun `scripts/build_references.py` and recheck.

## Transport

- MCP over streamable HTTP at `http://127.0.0.1:19501/mcp`, Bearer token in the `Authorization`
  header (stored in `~/.claude.json` under `mcpServers.metapilot-native`; never print it).
- Responses arrive as SSE `data:` lines. The server issues an `Mcp-Session-Id` header that must be
  sent back on every later request.
- `tools.listChanged` is true: the tool list follows the app screen.
  - home: 32 tools. Four exist only here: `duplicateProject`, `duplicateViaMcomp`, `exportMcomp`,
    `importMcomp`.
  - editor: 274 tools.
  - Catalog discovery (`getCapabilities`, `listCatalogKinds`, `listCatalog`, `getCatalogItem`)
    works on both screens.
- `scripts/mcp_client.py` handles all of this and can call any tool by name regardless of what the
  session's MCP client has loaded.

## Units and coordinates

| quantity | unit |
|---|---|
| time | composition (timeline) seconds, unless the name says `Source` or `Ms` |
| canvas position | normalized 0 to 1, origin top-left, +y down; x/y are the element center |
| scale | 1 = fit |
| rotation | degrees, clockwise |
| color | `#RRGGBB` or `#RRGGBBAA` (alpha last) |
| volume | linear gain 0 to 10, 1 = unity |
| export size | preset row: `resolutionType` (720p, HD, 2K, 4K) plus `aspectRatio` (nineBySixteen, sixteenByNine, ...) |
| frame rate | integer 24, 30 or 60; a new project starts at 60 |
| new project canvas | 1440x2560 (9:16) |
| text size | about 24 reads as a headline at 9:16, about 40 at 16:9 (`DMSans18pt-SemiBold`) |

## Tracks

A project has a magnetic main video track (clips butt against each other; transitions live only on
its boundaries), two free overlay tracks and two free audio tracks. `tracks` lists them; every
element carries its `trackId`.

## Schema traps

- **`ArgumentParser.CommandError error 1`** is the server's argument parser refusing an argument.
  It says nothing about which one. Remove arguments until it passes.
- **`dryRun` always triggers it.** The 10 tools that advertise `dryRun` (`applyLUT`,
  `applyTextPreset`, `setBeatDensity`, `setCaptionStyle` and others) fail whenever it is set.
- **`required` is unreliable.** Alternatives (`id` or `name`, `id` or `path`) are all marked
  required, and so are tuning params with server defaults. `findPauses({id})`, `quietPoint({id,
  seconds})` and `audioOnsets({id})` all work.
- **`previewVideoStatus` takes only `{includeFrames}`.** Passing `resultId` or `id` fails with
  CommandError.
- **`setExportSettings` needs the full preset row on a new project**: `resolutionType`,
  `aspectRatio`, `quality`, `dynamicRange`. A partial row makes `export` fail with "incomplete
  preset row". The schema lists no enums; a wrong value returns the valid list (values in
  `recipes.md`, Export). The `resolution:"WxH"` form only worked on the bundled Example project.
  Calling it with `{}` returns the current settings. Its `frameRate` is ignored: the file follows
  the project rate.
- **`setCanvas` can loop on "an earlier edit is still settling; retry"** right after a project
  opens (3 to 18 s per attempt, repeatedly). `setAspectRatio({ratio})` and `setFrameRate({fps})`
  apply at once.
- **`elements` field names** are `id`, `trackId`, `trackType` (main, overlay, audio), `content`
  (photo, video, text, audio), `startTime`, `endTime`. There is no `kind`, `start` or `duration`.
- **`selectById({ids:[]})`** fails with CommandError; it cannot clear the selection.
- **`undo` is not one step per call.** Some calls take several undos, some undos revert more than
  one call. Check `elements` after each. A build script run twice cost 30 undos to unpick: run
  build scripts once.
- **`setVolume({volume:0})` silences but `isMuted` stays false.**
- **`replaceElementMedia` is visual-only.** On an audio element it fails with "element ... is on an
  audio lane; replace targets visual clips only". To change a music bed without `delete`, set the
  old bed's volume to 0, then `importToMediaBin` and `addMediaPanelItemsToTimeline({aliasIds,
  startTime:0})`; the new bed lands on a free audio track. Recipe: "Swap a music bed".
- **Replacing a still with a file at the same path may not reload it.** Write the new version under
  a new filename before `replaceElementMedia`.
- **`listMusicTracks({license:"royaltyFree"})` returned nothing**, and a `query` switches the panel
  to its search tab.
- **Text does not wrap to a chosen width.** Break lines with "\n" in `editText` or `addText`.
- **`generateCaptions` `source`** is one of `video`, `voiceover`, `importedAudio`, `all`. With no
  audible source it fails with "No audio found". `setCaptionStyle` with no captions returns
  "no captions".
- **Speed curve presets are uppercase** (`MONTAGE`, `HERO`, `BULLET`, `JUMP_CUT`, `FLASH_IN`,
  `FLASH_OUT`, `RAMP`, `STROBE`). A lowercase id errors and lists the valid ids. `listCatalog`
  names `selectSpeedPanelPreset` as the apply tool for this kind; it is deprecated, use
  `setSpeedCurve({id,preset})`.
- **Text presets need the tool open.** `applyTextPreset({id,name})` errors "textPresets tool is not
  active" unless `selectTool({tool:"textPresets"})` ran first. The `ids` form opens it itself.
- **Text presets overwrite** font, color, size and position. Order: preset, then `setTextFont`,
  `setTextStyle`, `setTextPosition`, `setEmphasis`.
- **Applied catalog items.** `getElement` lists `applied[]` with an `instanceId` per item. A
  filter's real intensity sits in `params.intensity` (and `colorFilters`); the top-level
  `intensity` reads 1. `removeCatalogItem` echoes the pre-removal state in its response, but the
  item is gone: confirm with a second `getElement`.
- **`getElement.textPosition` stays `[0,0]`** after `setTextPosition`, although the text moves.
  Verify with `captureFrame`.
- **Transitions are removed by applying `normal`**: `addTransition({fromId,toId,filterId:"normal"})`
  returns `removed:true`.
- **Licensed music is opaque to audio analysis.** On a catalog music element, `loudness`,
  `quietPoint` and `audioOnsets` fail with "has no readable source file". `beatMarkers` and
  `setBeatDensity` work on it.
- **Beat density defaults to extreme**: a 60 s track returned about 228 beats. Set
  `setBeatDensity({id,density:"medium"})` (or `low`) before using `beatMarkers` for cut points.
- **`setTransforms` `items` is a JSON string**, not an array: `items: JSON.stringify([{id,scale,x,y}])`.
  The response carries a per-item result.
- **`transcriptJumpCut` is not a tool.** `transcribeClip`'s description mentions it, but no such
  tool is listed. Build jump cuts from `transcribeClip` or `findPauses` times with `splitAt`, then
  remove the gaps with `selectById` and `delete` (destructive: ask first).

## Destructive tools

Annotated `destructiveHint` by the server. Get the user's go-ahead before any of these:
`cut`, `delete`, `deleteAccountFont`, `deleteCaptions`, `deleteProject`, `deleteSoundEffect`,
`deleteVoiceoverClip`, `removeMusicTrack`.

Before experimenting on a project the user cares about, `duplicateProject({id})` on the home screen
(about 1.2 s, returns the new id and the name "<name> copy") and work on the copy.

## Measured timings

| call | time |
|---|---|
| `openProject` until `appState.screen` is `editor` | 0.3 to 0.7 s (longer if pulled from the cloud) |
| most reads (`state`, `elements`, `getElement`, `listCatalog`) | under 0.1 s |
| `captureFrame` | 0.2 to 1.3 s |
| `frameSheet` | about 0.8 s |
| `previewVideo` (synchronous, `rendering:false`) | about 3.5 s |
| `describeClip` | about 10 s |
| `duplicateProject` | about 1.2 s |
| `export` of the Example project at 720x1280, 30 fps | under 30 s, 251 MB file |
| `export` of a 28 s stills edit, HD 9:16 at 60 fps | about 12 s, 34 MB |
| `export` of the same edit, HD 16:9 at 30 fps | about 6 s, 23 MB |
| `setAspectRatio`, `setFrameRate`, `replaceElementMedia`, `importToMediaBin` | under 0.5 s |
| `setCanvas` on a freshly opened project | 3 to 18 s per retry, can repeat |

## Outputs on disk

- `captureFrame` returns inline JPEGs, 720 px wide (720x1280 for 9:16); nothing is written. It
  shows text fully revealed, so animation timing is only visible in an export.
- `frameSheet` returns an inline image and saves a PNG under the app container's `frame-sheets/`.
  That PNG is sandboxed (EPERM to other processes): pass `image_dir` to
  `mcp_client.Client.tool` to get the inline copy on disk. Cells are small (270 px wide in a
  one-column 16:9 sheet) and the time label covers each cell's top-left corner, so use
  `captureFrame` for detail.
- `previewVideo` returns a `resultId` and an MP4 path under the app container's `tmp/`.
- `export({path})` writes wherever `path` says; use an absolute path the user chose.

## Export states

`export` returns `ok:true` at once. `exportStatus` then moves through `preparing`, `exporting`
(with `progress` from 0 to 1) and `complete` (with `outputPath`); `idle` means nothing is running.
Poll every 1 to 2 s and confirm the file exists before reporting success.
