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
- How each fault answers (measured 2026-11-08; `mcp_client.py doctor` reads them for you):
  - Nothing listening on the port (Edits closed, or its server off): connection refused.
  - Wrong token: HTTP 403 with `{"error":"unauthorized", ...}`. Its `instructions` field asks
    the agent to have the user paste the token into chat; re-register the server instead.
  - A tool the current screen does not offer, editor tools on home included: `tools/call` returns
    `unknown tool (not in current manifest): <name>` with `isError`, the same as a misspelled
    name. Only `appState` tells the two apart.

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
  `aspectRatio`, `quality`, `dynamicRange` and `frameRate`. A partial row makes `export` fail
  with "incomplete preset row, missing: <fields>"; a call with the first four and no `frameRate`
  failed as "missing: frameRate", and a call with only `resolution` and `frameRate` listed the
  other four. The schema lists no enums; a wrong value returns the valid list (values in
  `recipes.md`, Export). The `resolution:"WxH"` form only worked on the bundled Example project.
  Calling it with `{}` returns the current settings. Pass the project rate as `frameRate`; the
  file follows the project rate either way.
- **Imports read only from `~/Movies`.** Edits is sandboxed. `importToMediaBin` on a file under
  `~/GitHub/...` or the session scratchpad under `/private/tmp/...` fails with `import failed:
  copyFailed(file:///..., Error Domain=NSCocoaErrorDomain Code=513 "<file> couldn't be copied
  because you don't have permission to access ...")`. The same file under
  `~/Movies/<folder>/` imports at once. Treat every tool that takes a media `path` the same way
  (`replaceElementMedia` worked from `~/Movies` too); stage rendered clips, stills and audio there.
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
- **`beatMarkers` returns `markers`, not `beats`.** The list sits under `markers` (each with
  `timelineSeconds`, `sourceSeconds`, `isDownbeat`, `strength`), except that an empty result came
  back as `beats: []`. `beatCount` stays the extreme-density total (228) whatever the density;
  the number returned is `visibleCount` (9 at `medium` on a 25 s cut). Read either key.
- **Imported audio has no auto beats.** On a music element imported from a file, `beatMarkers`
  returned `beatCount: 0` at every density, and `audioOnsets` failed on the same element with the
  generic "The operation could not be completed" (2026-11-09). Beat-synced cuts need catalog
  music, or beats placed by hand with `addBeatMarker`.
- **`splitAt` cuts land on the frame grid, not on the requested time.** With the default
  `snap:"projectFrame"` a cut moves to the nearest project frame, up to half a frame away. One
  split also left a 1.7 ms sliver between the pieces. Read the track back with `elements` after
  every split that has to hit exact times (recipe: "Beat-synced cut").
- **`setTransforms` `items` is a JSON string**, not an array: `items: JSON.stringify([{id,scale,x,y}])`.
  The response carries a per-item result.
- **`trim` on a sped-up clip counts source seconds.** At `setSpeed` 4, `deltaSeconds:0.3` on the
  right removed 0.267 source seconds and 0.067 timeline seconds; the value snaps to a frame
  (`0.75` became `0.767`). A negative delta lengthens. A left trim moves `startTime` as well, so
  put the clip back with `move({id,toSeconds})` and confirm with `getElement`.
- **Opacity keyframes take three calls per point**: `seek({seconds})`,
  `toggleKeyframe({id,property:"opacity"})`, then `setOpacity({id,opacity})`, which answers
  `keyframed:true` and the `editTargetSeconds` it wrote. `getElement.mediaKeyframes` reports each
  point's `time` relative to the clip's source (`sourceInPoint` plus the offset from the clip
  start, so a clip trimmed to 0.233 shows its first key at 0.233) and its value as `alpha`.
  Seeking to the element's exact end clamps the playhead inside the clip, and `setOpacity` then
  edits the previous keyframe: place the fade-out keyframes while the clip is still long, then
  trim the right side. Keyframes survive the trim.
- **`addOverlay` scale 1 fits the canvas height.** `setTransform({id,scale,x,y})` resizes it, with
  `x`, `y` the normalized center; `getTransform` echoes the values. A rectangle `setMask` with
  `cornerRadius` (0.03 reads as a card's rounded corner) clips it, and `setVolume({id,volume:0})`
  and `setSpeed({id,speed})` work on overlays as on main clips.
- **`replaceElementMedia` refuses audio** with "is on an audio lane; replace targets visual clips
  only". Use `replaceAudio({id,path})`: it keeps the element id but also the old duration, so a
  longer file needs `trim({id,side:"right",deltaSeconds:-<extra>})` afterward.
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
  `mcp_client.Client.tool` to get the inline copy on disk. Default cells are small (270 px wide
  in a one-column 16:9 sheet; a six-frame, three-column 16:9 sheet came back 810x302). Pass
  `cellWidth` for a larger sheet: `cellWidth:420` with 3 columns gave 1260x472 at 16:9, and
  `cellWidth:300` with 3 columns gave 900x1066 at 9:16. The schema marks `cellWidth` required; it
  is optional. The time label covers each cell's top-left corner, so use `captureFrame` for
  detail.
- `previewVideo` returns a `resultId` and an MP4 path under the app container's `tmp/`.
- `export({path})` writes wherever `path` says; use an absolute path the user chose.

## Export states

`export` returns `ok:true` at once. `exportStatus` reports under the key `state` (not `status`),
which moves through `preparing`, `exporting`
(with `progress` from 0 to 1) and `complete` (with `outputPath`); `idle` means nothing is running.
Poll every 1 to 2 s and confirm the file exists before reporting success.
