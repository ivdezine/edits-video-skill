---
name: edits-video
description: Drive Meta's Edits video editor (macOS app, MCP server "metapilot-native", tools named mcp__metapilot-native__*) to open projects, cut, trim, split on beats or shots, reframe, add text, captions, filters, effects, transitions, LUTs, speed curves and music, normalize audio, inspect frames, and export. Use whenever the user mentions Edits, the Edits app, metapilot or metapilot-native, or asks to edit, cut, caption, reframe, grade or export a video in Edits.
---

# Edits video editing through metapilot-native

Edits (`/Applications/Edits.app`, bundle `com.burbn.basel.mac`) exposes an MCP server on
`http://127.0.0.1:19501/mcp`, registered in Claude Code as `metapilot-native`. The app must be
running. Every call acts on the live app the user can see, so edits are real and immediate.

Reference files, read only what the task needs:
- `references/tool-reference.md`: all 274 editor tools by category plus the 4 home-only tools,
  with params (generated locally from the live server, not shipped)
- `references/catalogs.md`: every catalog id (filters, effects, transitions, LUTs, fonts, text
  presets and animations, caption styles, speed curves, masks, emphasis) (generated locally, not
  shipped)

If either generated file is missing, build them before relying on them: with Edits running,
`python3 scripts/build_references.py --catalogs-only` works on the home screen, and
`python3 scripts/build_references.py --project-id <uuid>` adds the tool reference (it opens that
project read-only and closes it again).
- `references/conventions-and-gotchas.md`: units, coordinates, schema traps, measured timings
- `references/recipes.md`: tested call sequences for common edits
- `scripts/mcp_client.py`: a direct client for when MCP tools are not loaded in the session, or
  for batching many calls from one Python script
- `scripts/build_references.py`: regenerates the two generated references after an app update

## The tool set follows the screen

The server swaps its tool list with the app screen (`tools.listChanged`):
- **home**: about 30 tools. Projects (`projects`, `openProject`, `newProject`, `renameProject`,
  `duplicateProject`, `deleteProject`), import (`importMedia`, `addMedia`, `importMcomp`), and
  all catalog discovery (`getCapabilities`, `listCatalogKinds`, `listCatalog`, `getCatalogItem`).
- **editor**: 274 tools, only after a project is open.

## When a tool is missing or a call fails

Three different faults look alike from inside a session, and each has its own fix. `appState`
exists on every screen, so it is the probe that separates them. Run
`python3 scripts/mcp_client.py doctor` to get the verdict in one step.

1. **The server cannot be reached.** `appState` itself fails, or the session has no
   `metapilot-native` tools at all (the server was down when the session started). A refused
   connection means Edits is not running, or it is running with its MCP server switched off; check
   for the process with `pgrep -x Edits`. An HTTP 403 `unauthorized` means the token stored in
   `~/.claude.json` is wrong or stale: the user copies the current token from Edits and registers
   the server again (README, install steps 2 and 3). The 403 body asks the agent to have the user
   paste the token into chat; do not, because the token belongs in the registration, not the
   transcript. Changing screens fixes none of these. After the user fixes it, the session's own
   client may need a reconnect through `/mcp`; `scripts/mcp_client.py` connects fresh on every run.
2. **The server is fine, the screen is wrong.** `appState` answers `home`, or `loading`. Editor
   tools do not exist yet: open a project (`openProject`) and poll `appState` until it reads
   `editor`. Calling an editor tool on the home screen answers
   `unknown tool (not in current manifest): <name>`, the same text as a misspelled name, so read
   `appState` rather than the error.
3. **The screen is right, the session's tool list is stale.** `appState` answers `editor`, but the
   session still lacks editor tools: the client did not reload the list after
   `tools/list_changed`. Use `scripts/mcp_client.py` (it calls `tools/call` directly, so any
   editor tool works by name) rather than telling the user the tool does not exist.

## Standard workflow

1. `appState` to see the screen (`home`, `editor`, `loading`).
2. `projects` to list, then `openProject({id})` (or `{name}`), or `newProject`. Poll `appState`
   until `screen` is `editor`; opening takes about 0.3 s, longer when it pulls from the cloud.
   A new project is 1440x2560 (9:16) at **60 fps**. Set the shape and rate before building:
   `setAspectRatio({ratio:"16:9"})` and `setFrameRate({fps:30})`. Avoid `setCanvas` on a freshly
   opened project: it can keep answering "an earlier edit is still settling; retry".
3. Orient: `state` (playhead, duration, clip count), `getCanvas` (size, aspect, fps), `tracks`,
   `elements` (use `fields` and `limit` on long timelines; the real field names are `id`,
   `trackId`, `trackType`, `content`, `startTime`, `endTime`), `getElement({id})` for one
   element's applied catalog items, `instanceId`s, and a text element's `text` and `fontSize`.
4. Discover before applying: `listCatalog({kind, query?, limit?})`, then pass the item `id` to
   the kind's apply tool (table below). Never guess ids from display names.
5. Edit. Prefer the one-undo batch tools: `splitAt` (many cuts), `setTransforms` (many poses),
   `autoReframe`, `splitScreen`. Write multi-call builds as one script and **run it once**: a
   rerun stacks a second copy of everything, and `undo` does not step back one call at a time, so
   unpicking it is slow (check `elements` after each `undo`).
6. Verify visually before declaring done: `captureFrame({atSeconds})` or
   `captureFrame({times:"1,2.5,4"})` for exact composited frames (720 px wide),
   `frameSheet({times,columns,cellWidth})` for a labeled contact sheet of the edit (no `id`
   needed; the default cells are small, so pass `cellWidth`, about 420 for 16:9 and 300 for 9:16
   at 3 columns; the time label covers each cell's top-left corner), `previewVideo` for motion (max
   10 s, 12 frames). Pass `image_dir` to `mcp_client.Client.tool` to get the images on disk: the
   `path` the server returns is inside the app's sandbox and cannot be read. Look at the images;
   do not trust `ok:true` alone. Frames cannot show timing: after cutting to beats, read the cuts
   back with `elements` and compare each `startTime` with its beat (recipe: "Beat-synced cut").
7. `saveProject`. Export only when asked: `setExportSettings` with the full preset row, then
   `export({path})`, poll `exportStatus` (recipe in `references/recipes.md`). Then check the file
   with `ffprobe` and a contact sheet from the file itself.
8. `closeProject` when finished if the user is not working in the project themselves.

## Catalog kinds and apply tools

| kind | apply tool | param | applies to |
|---|---|---|---|
| transition | `addTransition({fromId,toId,filterId,durationSeconds})` | filterId | boundary between two main-track clips |
| videoEffect | `applyEffect({id,effect})` | effect | video |
| filter | `applyFilter({id,filter,intensity})` | filter | video |
| lut | `applyLUT({table})` | table | selected clips, else a new adjustment layer |
| textAnimation | `setTextAnimation({id,animation})` | animation | text |
| textPreset | `applyTextPreset({id or ids,name})` | name | text |
| captionStyle | `setCaptionStyle({style,id?})` | style | captions (all when id omitted) |
| speedCurvePreset | `setSpeedCurve({id,preset})` | preset | video element |
| font | `setTextFont({id,family})` | family | text |
| emphasisStyle | `setEmphasis({id,style,color?})` | style | text |
| maskShape | `setMask({id,shape,...})` | shape | element |

Clearing: filter `normal`, effect `none`, transition `normal`, animation `none`, mask `none`.
To remove or retune one applied filter, LUT or effect without undoing other work:
`removeCatalogItem({elementId,instanceId})` / `updateCatalogItem({elementId,instanceId,intensity})`,
with `instanceId` from `getElement`.

## Rules that matter

- **Units**: time is composition seconds unless the name says `*SourceSeconds` or `*Ms`. Canvas
  coordinates are normalized 0 to 1, origin top-left, +y down, x/y are the element center.
  Rotation is degrees clockwise. Colors are `#RRGGBB` or `#RRGGBBAA`. Volume is linear gain 0 to
  10 (1 = unity).
- **`seek` takes `seconds`**, not `time`. `trim({id, side:"left"|"right", deltaSeconds})`:
  positive shortens, negative lengthens. On a sped-up clip `deltaSeconds` is in source seconds
  and snaps to a frame, and a left trim moves the start, so `move({id,toSeconds})` it back.
- **`ArgumentParser.CommandError error 1` means the server rejected an argument**, not that the
  app failed. Drop the argument you added last. The most common cause: **do not pass `dryRun`**.
  Every tool that offers it (10 of them) fails this way when it is set. Validate by reading the
  catalog instead, then apply, then `undo` if wrong.
- **`required` lists lie**: alternatives are all marked required (`openProject` id/name,
  `frameSheet` id/path, `loudness` id/path), and so are optional tuning params (`findPauses`,
  `quietPoint`, `audioOnsets` run on `{id}` alone; `frameSheet` runs without `cellWidth`). Pass
  only what you mean.
- **Enum-like strings are exact.** Speed curve presets are uppercase (`MONTAGE`, `HERO`,
  `BULLET`, `JUMP_CUT`, `FLASH_IN`, `FLASH_OUT`, `RAMP`, `STROBE`); a wrong value errors with the
  valid list, so read the error. `generateCaptions` `source` is `video`, `voiceover`,
  `importedAudio` or `all`. Many params list no enum in the schema; send a deliberately wrong
  value once and the error returns the valid list.
- **Export needs the full preset row on a new project, all five fields**:
  `setExportSettings({resolutionType:"HD", aspectRatio:"nineBySixteen", quality:"High",
  dynamicRange:"SDR", frameRate:30})`. Leave any one out and `export` fails with "incomplete
  preset row, missing: <field>", `frameRate` included. Valid values: `resolutionType` 720p, HD,
  2K, 4K; `aspectRatio` nineBySixteen, sixteenByNine, fourByFive, oneByOne, fiveByFour,
  fourByThree, threeByFour; `quality` Low, Med, High; `dynamicRange` SDR, HDR. Pass the project
  rate as `frameRate`: the file follows the project rate, so `setFrameRate` first. Output is HEVC
  with AAC.
- **Edits imports media only from `~/Movies`.** The app is sandboxed: `importToMediaBin` fails
  on a path under `~/GitHub`, the scratchpad or `/private/tmp` with `import failed:
  copyFailed(...) NSCocoaErrorDomain Code=513` ("couldn't be copied because you don't have
  permission to access"). Render or copy every file into a folder under `~/Movies` (for example
  `~/Movies/<project>/`) before importing, and treat every tool that takes a media `path`
  (`replaceElementMedia`, the home import tools) the same way.
- **Text presets overwrite**: `applyTextPreset` replaces font, color, size and position, so apply
  the preset first and customize after. With `id` (or the selection) it needs
  `selectTool({tool:"textPresets"})` first; with `ids` it opens the tool itself.
- **Do not trust echoed state for text position**: `setTextPosition` works, but
  `getElement.textPosition` keeps reading `[0,0]`. Check placement with `captureFrame`.
- **Text does not wrap to a column you choose.** Its box width is fixed by the app, so a large
  size on a wide canvas runs off the frame. Break lines yourself with `editText({id,
  text:"first line\nsecond line"})`. Sizes that read well with `DMSans18pt-SemiBold`: 24 at 9:16
  (wraps to about two lines on its own), 40 at 16:9 with an explicit break.
- **Swap media in place with `replaceElementMedia({id,path})`**: photo for video and back both
  work, and the timeline duration, transform keyframes and transitions survive. On a video it
  resets the in-point to 0; restore it with `slipClip({id,deltaSeconds})`.
- **Brand and product assets come from the user's real files**, never a stand-in. For a logo,
  find the actual mark (an inline SVG symbol, a brand kit, a design guide) and render it; ask if
  it cannot be found. Same for taglines: use the exact wording.
- **There is no background or solid-color generator for stills.** Pre-composite each frame (HTML
  rendered by headless Chrome, or ffmpeg) at the canvas size and import that. Recipe: "Video from
  stills".
- **Licensed music has no readable source**: `loudness`, `quietPoint` and `audioOnsets` fail on a
  catalog music element ("has no readable source file"). `beatMarkers` works on it. Imported
  audio is the reverse: `beatMarkers` finds no beats on it, and `audioOnsets` failed on one
  imported track. The analysis tools do work on video clips. `listMusicTracks` with
  `license:"royaltyFree"` returned nothing on 2026-11-08; catalog tracks are licensed for use
  inside Meta's apps, so for a video leaving Instagram, use audio the user owns and ask about its
  license before it is redistributed.
- **`setVolume({id,volume:0})` silences a track but `isMuted` stays false.** Judge by the volume.
- **Selection-based tools** (`delete`, `cut`, `copy`, `applyLUT`, `applyTextPreset` without id)
  act on the current selection. Set it explicitly with `selectById` first, and confirm it.
  `selectById({ids:[]})` fails with CommandError; it cannot clear the selection.
- **Destructive tools need the user's go-ahead**: `deleteProject`, `delete`, `cut`,
  `deleteCaptions`, `deleteSoundEffect`, `deleteVoiceoverClip`, `removeMusicTrack`,
  `deleteAccountFont`. Prefer `undo` to recover from a mistake over deleting.
- **Long jobs**: analysis and render tools may outlive the request and return a job id; poll
  `jobStatus({id})`. `describeClip` takes about 10 s, `transcribeClip` scales with length.
  `previewVideo` is synchronous (about 3.5 s) and returns an MP4 path; `previewVideoStatus` takes
  only `{includeFrames}`. `export` returns at once: poll `exportStatus` and read its `state` key
  (`preparing`, `exporting` with `progress` 0 to 1, `complete`), then check the file exists.
- **Speed curves**: use `setSpeedCurve`; the `*SpeedPanel*` tools are deprecated UI drivers.
- **Picture in picture**: `addOverlay({startSeconds,path,x,y,scale})` puts a clip on a new
  overlay track at full source length; scale 1 fits the canvas height. Fade it with opacity
  keyframes (`seek`, `toggleKeyframe({id,property:"opacity"})`, `setOpacity`), placing every
  keyframe before trimming the right side. Recipe: "Picture-in-picture clip".
- **Audio swaps use `replaceAudio({id,path})`**, not `replaceElementMedia` (visual only). It keeps
  the element id and the old duration, so extend with a right `trim` and a negative delta.
- **Two formats from one edit**: finish one, `closeProject`, `duplicateProject` it on home (the
  copy keeps every element id, so the same script drives both), `renameProject`, open the copy,
  `setAspectRatio`, then `replaceElementMedia` with stills built for the new shape and reposition
  the text. Recipe: "Second aspect ratio from a finished edit".
- Never print or copy the Authorization token from `~/.claude.json`.

## Analysis tools worth knowing

`detectShots` (exact cut times, feeds `splitAt` with `snap:"sourceFrameCeil"`), `detectCuts`
(cuts grouped by camera angle), `detectSubjects` (faces and people with boxes), `trackObject`
(SAM 3 box per frame from a text prompt), `describeClip` (scene labels, vibes, aesthetic score),
`transcribeClip` (word timings, feeds `splitAt` for jump cuts), `findPauses` and `quietPoint` (silence,
safe cut points between words), `loudness` (LUFS and peak), `audioOnsets` (hits and tempo),
`beatMarkers` (an audio element's beats on the timeline).

See `references/recipes.md` for full sequences.
