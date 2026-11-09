# Recipes

Call sequences for common edits. Each is marked **tested** (run end to end against the live server on
2026-11-08) or **untested** (built from the schema; check each response and the frames).

All recipes assume a project is open (`appState.screen == "editor"`) and that ids come from
`elements`, `getElement` or the previous call's response. Finish every recipe with a visual check
(`captureFrame` or `frameSheet`) and `saveProject`.

Every media `path` (`importToMediaBin`, `replaceElementMedia`, the home import tools) must be an
absolute path under `~/Movies`: Edits is sandboxed, and `importToMediaBin` fails anywhere else
with `copyFailed ... Code=513`. `/Users/<user>/Movies/<proj>/` below is a folder you stage the
files in.

## Animated title (tested)

```
addText({text:"Skill test", duration:3, atSeconds:0})        -> id
selectTool({tool:"textPresets"})
applyTextPreset({id, name:"Strictly business"})              # overwrites font, color, size, position
setTextFont({id, family:"IGUIBetav9-Heavy"})                  # optional, after the preset
setTextStyle({id, size:64, color:"#FFFFFF", bold:true})
setEmphasis({id, style:"backgroundPill", color:"#000000AA"})
setTextPosition({id, x:0.5, y:0.15})                          # center of the text box
setTextAnimation({id, animation:"typewriter"})
captureFrame({times:"0.5,1.5,2.5"})                           # getElement.textPosition will still read [0,0]
```

Ids for presets, fonts, emphasis styles and animations: `references/catalogs.md`.

## Graded clip (tested)

```
listCatalog({kind:"filter", query:"warm"})                   -> filter id
applyFilter({id:<clip>, filter:<filterId>, intensity:0.7})
getElement({id:<clip>})                                      -> applied[].instanceId
updateCatalogItem({elementId:<clip>, instanceId, intensity:0.5})
applyEffect({id:<clip>, effect:"video_shake"})               # optional effect on top
removeCatalogItem({elementId:<clip>, instanceId})            # drop one item without undoing others
```

For a LUT: `selectById` the clips, then `applyLUT({table})`. With nothing selected it makes a new
adjustment layer instead.

## Transitions (tested)

```
addTransition({fromId:<clipA>, toId:<clipB>, filterId:"transition_dissolve", durationSeconds:0.4})
addTransition({fromId:<clipA>, toId:<clipB>, filterId:"normal"})    # removes it
```

Only between neighboring clips on the main track.

## Beat-synced cut (tested)

```
elements({fields:"id,content,trackType,startTime,endTime"})  -> music element id, video clip id
setBeatDensity({id:<music>, density:"medium"})               # default extreme is far too dense
beatMarkers({id:<music>})                                    -> markers[].timelineSeconds
splitAt({id:<clip>, times:[<beat times inside the clip>]})   -> pieces[].id
elements({fields:"id,content,trackType,startTime,endTime"})  # read the cuts back (below)
```

Keep only times strictly inside the clip's range. `beatMarkers` returns the markers visible at the
current density under `markers` (the key reads `beats` when the list is empty); `beatCount` is
the total at the densest setting, not the number returned. Each marker carries `timelineSeconds`,
`sourceSeconds`, `isDownbeat` and `strength`. It only finds beats on catalog music: on imported
audio it returned `beatCount: 0` (see "Imported audio has no auto beats" in the gotchas).

**Read the cuts back.** `splitAt` snaps each time to the project frame grid, so a cut lands up to
half a frame from its beat (8.3 ms at 60 fps, 16.7 ms at 30 fps), which is inaudible. The contact
sheet cannot show timing, so check it numerically: read the main track back and compare each
piece's `startTime` with the beat it was meant for.

```python
fps = c.tool("getCanvas")["frameRate"]
tol = 1 / (2 * fps)                       # half a frame
vid = sorted((e for e in c.tool("elements", {"fields": "id,trackType,startTime,endTime"})["elements"]
              if e["trackType"] == "video"), key=lambda e: e["startTime"])
starts = [e["startTime"] for e in vid]
for beat in targets:                      # the beat times you passed to splitAt
    s = min(starts, key=lambda s: abs(s - beat))
    print(beat, s, "ok" if abs(s - beat) <= tol else "OFF by %.3f s" % (s - beat))
for a, b in zip(vid, vid[1:]):            # neighbors should touch
    if b["startTime"] - a["endTime"] > 1e-6:
        print("gap", a["endTime"], b["startTime"])
```

Measured on 2026-11-09 (60 fps project, catalog music at `medium`): beats at 2.64 and 8.08 landed
at 2.6333 and 8.0833, inside the half-frame tolerance; a cut placed on purpose at 19.1 against a
beat at 19.0 was flagged `OFF by 0.100 s`. The 8.08 split also left a 1.7 ms sliver between the
two pieces (first piece ends 8.0817, second starts 8.0833). No frame time falls inside a gap that
small, so it renders nothing, but a gap of a frame or more would show as black: the second loop
reports both. If a cut reads OFF, fix the time and split again, or `move` the piece, rather than
trusting the request.

Then style the pieces per beat (`setTransforms` for punch-ins, `applyEffect`, transitions). The
beat detector can itself misplace a beat, which no read-back catches, so listen to a
`previewVideo` before export.

## Shot-based cut (tested for detectShots; the snap mode is untested)

```
detectShots({id:<clip>})                                     -> shots with sourceTime and timelineTime
splitAt({id:<clip>, times:[<sourceTime values>], snap:"sourceFrameCeil"})
```

`sourceFrameCeil` cuts on the exact source frame. With timeline times, leave `snap` at its default.

## Punch-in and reposition many elements (tested)

```
setTransforms({items: "[{\"id\":\"<a>\",\"scale\":1.2,\"x\":0.5,\"y\":0.45},{\"id\":\"<b>\",\"scale\":1.1}]"})
```

One undo step. `items` is a JSON string.

## Speed ramp (tested)

```
setSpeedCurve({id:<clip>, preset:"MONTAGE"})                 # uppercase preset ids
```

Presets: MONTAGE, HERO, BULLET, JUMP_CUT, FLASH_IN, FLASH_OUT, RAMP, STROBE. Speed-ramped clips are
refused by `detectShots`, so detect shots first.

## Music level and loudness check (tested)

```
setVolume({id:<music>, volume:0.8})
loudness({id:<clip>})                                        -> integratedLufs, samplePeakDb
```

`loudness` does not work on licensed catalog music. Untested: `processAudio({id, mode, chain})`
for EQ, voice isolation and loudness normalization; read its description in `tool-reference.md`
first.

## Pause cuts (tested for the analysis; the cut is untested)

```
findPauses({id:<clip>})                                      -> silent stretches
quietPoint({id:<clip>, seconds:<near a pause>})              -> the quietest 10 ms, a clean cut point
splitAt({id:<clip>, times:[<pause start>, <pause end>, ...]})
```

Removing the silent pieces needs `selectById` + `delete`, which is destructive: ask first. An
alternative that needs no delete is `trim` on the pieces' edges.

## Transcript jump cut (untested)

```
transcribeClip({id:<clip>})                                  -> words with start/end (timeline seconds)
splitAt({id:<clip>, times:[<word gap boundaries>]})
```

Then remove the unwanted pieces as in Pause cuts. There is no `transcriptJumpCut` tool.

## Captions (partly tested)

```
generateCaptions({source:"video", language:"en"})            # source: video, voiceover, importedAudio, all
listCatalog({kind:"captionStyle"})
setCaptionStyle({style:<id>})                                 # all captions; pass id for one
```

Tested only up to the "No audio found" error on a project whose clips have no audible track. Check
the composition has speech before running it.

## Reframe to another aspect (aspect change tested; autoReframe untested)

```
setAspectRatio({ratio:"16:9"})                               # instant: 1440x2560 becomes 2560x1440
setFrameRate({fps:30})                                       # export follows the project rate
autoReframe({subject:"largestPerson", motion:"follow", wideShotPolicy:"crop"})
captureFrame({times:"1,3,5"})
```

`setCanvas` does the same in one call but, on a freshly opened project, kept answering "an earlier
edit is still settling; retry" for 3 to 18 s per try. Use the two single-purpose tools instead.

`wideShotPolicy:"stack2"` turns wide shots into a two-panel split screen. For a manual split
screen: `splitScreen({id, layout, panels, background, gap})` (untested).

## Preview motion (tested)

```
previewVideo({startSeconds:0, durationSeconds:6, frameCount:12, maxWidth:480})
```

Synchronous, about 3.5 s, returns frames inline and an MP4 path. `previewVideoStatus` takes only
`{includeFrames}`.

## Export (tested)

```
setFrameRate({fps:30})                                       # the file follows the project rate
setExportSettings({resolutionType:"HD", aspectRatio:"nineBySixteen",
                   quality:"High", dynamicRange:"SDR",
                   frameRate:30})                            # the full preset row, all five
saveProject()
export({path:"/Users/<user>/Movies/<name>.mp4"})
exportStatus()                                               # poll: preparing -> exporting (progress) -> complete
```

- Send the whole row, `frameRate` included. On a new project a partial call leaves the preset
  incomplete and `export` fails with "incomplete preset row, missing: <fields>". The older
  `resolution:"720x1280"` form worked only on the bundled Example project, whose preset was
  already filled in.
- Valid values (the schema lists none; a wrong value returns this list): `resolutionType` 720p, HD,
  2K, 4K; `aspectRatio` nineBySixteen, sixteenByNine, fourByFive, oneByOne, fiveByFour,
  fourByThree, threeByFour; `quality` Low, Med, High; `dynamicRange` SDR, HDR.
- `HD` gives 1080x1920 or 1920x1080, HEVC video with AAC audio. Pass the project rate as
  `frameRate`: it must be present, and the file follows the project rate.
- Check the file, not the status: `ffprobe` for size, rate and duration, and a contact sheet pulled
  from the file (`ffmpeg -vf fps=1/3,scale=360:-1,tile=4x3`). Text animations show their real reveal
  timing only in the file; `captureFrame` can show the fully revealed text.

## Video from stills (tested)

There is no solid-color or title-card generator, so build each frame outside the app at the canvas
size (1440x2560 or 2560x1440): an HTML page rendered by headless Chrome, or ffmpeg. Use the
user's real brand files for logos and the exact wording for taglines. Write the files into a folder
under `~/Movies`; rendered video scenes (H.264 MP4s) import the same way and keep their length.

```
importToMediaBin({path:"/Users/<user>/Movies/<proj>/01.png"}) -> aliasId     # one call per file
addMediaPanelItemsToTimeline({aliasIds:[a1,a2,a3]})          # appends in order; stills last 3 s
trim({id, side:"right", deltaSeconds:0.5})                   # positive shortens; 3.0 -> 2.5 s
addTransition({fromId:a, toId:b, filterId:"transition_dissolve", durationSeconds:0.4})
```

A dissolve does not change the total duration. For video, `addMediaPanelItemsToTimeline` also
takes `sourceIn` and `sourceOut` (source seconds).

## Push-in on a still (tested)

```
setTransformKeyframe({id, time:<clip start>, scale:1.0,  x:0.5, y:0.5})
setTransformKeyframe({id, time:<clip end>,   scale:1.06, x:0.5, y:0.5})
```

`time` is timeline seconds and easing is linear. 1.05 to 1.06 over 3 s reads as gentle motion;
more starts to crop text baked into the still.

## Headline over a still (tested)

```
addText({text:"Track every dollar", duration:<clip length>, atSeconds:<clip start>})  -> id
setTextFont({id, family:"DMSans18pt-SemiBold"})
setTextStyle({id, size:24, color:"#FFFFFF", alignment:"center"})   # 9:16; at 16:9 use 40 and a "\n"
setTextPosition({id, x:0.5, y:0.14})
setTextAnimation({id, animation:"fligFadeUpWord"})           # word-by-word fade up, done by about 1 s
editText({id, text:"Track every\ndollar"})                   # change content without touching style
```

The text box width is fixed by the app: at 16:9, size 40 on one line overflows the frame, so break
the line yourself. `getElement` returns `text` and `fontSize` to confirm.

## Swap media without rebuilding (tested)

```
replaceElementMedia({id, path:"/Users/<user>/Movies/<proj>/new.png"})  # or video for photo, and back
slipClip({id, deltaSeconds:5.0})                             # video only: restore the in-point
```

Keeps the element id, its timeline duration, transform keyframes and transitions. Replacing a
video resets the in-point to the start of the source. Visual elements only: audio fails with
"is on an audio lane; replace targets visual clips only" (see "Swap a music bed").

## Swap a music bed (tested)

```
replaceAudio({id:<bed>, path:"/Users/<user>/Movies/<proj>/new-bed.m4a"})   # same id, old duration
trim({id:<bed>, side:"right", deltaSeconds:-<extra>})        # negative extends to the new length
```

`replaceAudio` keeps the element id, its volume and its place, so a build script needs no new id.
It does not take the new file's length: a 25 s file over a 23 s bed stays 23 s until the trim.

Alternative that leaves the old bed in place:

```
setVolume({id:<old bed>, volume:0})                          # non-destructive; no delete needed
seek({seconds:0})
importToMediaBin({path:"/Users/<user>/Movies/<proj>/new-bed.m4a"}) -> aliasId
addMediaPanelItemsToTimeline({aliasIds:[aliasId], startTime:0})   # lands on a free audio track
trim({id:<new bed>, side:"right", deltaSeconds:<excess>})    # end it with the picture
```

Cut the file to the timeline length first with ffmpeg (fade in 0.4 s, fade out 3 s) and match its
loudness to the old bed, so no trim is needed. Find the new element by diffing `elements` before and
after the add.

## Picture-in-picture clip (tested)

A phone clip set inside a card on a rendered scene, sped up, muted and faded:

```
addOverlay({startSeconds:14.3, path:"/Users/<user>/Movies/<proj>/IMG_2800.MOV", x:0.5, y:0.5677, scale:1.0})
setTransform({id, scale:0.4271, x:0.5, y:0.5677})            # scale is the fraction of canvas height
setSpeed({id, speed:4})                                      # 14.9 s source -> 3.7 s on the timeline
setVolume({id, volume:0})
setMask({id, shape:"rectangle", centerX:0.5, centerY:0.5, sizeW:1.0, sizeH:1.0, cornerRadius:0.03})
trim({id, side:"left", deltaSeconds:0.2333})                 # source seconds; moves startTime
move({id, toSeconds:14.3})                                   # put it back
seek({seconds:14.3}); toggleKeyframe({id, property:"opacity"}); setOpacity({id, opacity:0})
seek({seconds:14.5}); toggleKeyframe({id, property:"opacity"}); setOpacity({id, opacity:1})
seek({seconds:17.7}); toggleKeyframe({id, property:"opacity"}); setOpacity({id, opacity:1})
seek({seconds:17.9}); toggleKeyframe({id, property:"opacity"}); setOpacity({id, opacity:0})
trim({id, side:"right", deltaSeconds:0.3})                   # last: end on the faded-out key
```

`addOverlay` returns the id and a new overlay track; the clip runs at full source length until
`setSpeed` and the trims. Size the card in the rendered scene first and derive `x`, `y` and `scale`
from it (center and height as fractions of the canvas). Set every keyframe before the right trim:
seeking to the exact end edits the previous keyframe instead. Check the fades with a `frameSheet`
across the in and out points.

## Insert a still before the last clip (tested)

```
importToMediaBin({path}) ; addMediaPanelItemsToTimeline({aliasIds:[a]})   # appends, 3 s
reorderClip({id:<new>, position:<index of the last clip>})
trim({id:<new>, side:"right", deltaSeconds:-7})              # negative extends a still: 3 -> 10 s
```

## Music from a file (tested)

```
importToMediaBin({path:"/Users/<user>/Movies/<proj>/bed.mp3"}) -> aliasId
addMediaPanelItemsToTimeline({aliasIds:[aliasId]})           # lands on a new audio track at 0
trim({id:<audio>, side:"right", deltaSeconds:<excess>})      # end it with the picture
setVolume({id:<audio>, volume:0.8})
loudness({id:<audio>})                                       # works on imported audio
```

`listMusicTracks({query, license:"royaltyFree"})` returned nothing in testing, and passing a
`query` switches the panel to search. Catalog music is licensed for Meta's apps; ask the user about
the license of any track before a video leaves Instagram.

## Second aspect ratio from a finished edit (tested)

Finish and export the first format, then:

```
closeProject()                                               -> screen "home"
duplicateProject({id:<first>})                               -> new id; every element id is kept
renameProject({id:<new>, name:"<name> 16x9"})                # also works in the editor
openProject({id:<new>})
setAspectRatio({ratio:"16:9"}); setFrameRate({fps:30})
replaceElementMedia({id, path:<16:9 still>})                 # per still, same ids as the original
setTextPosition / setTextStyle / editText                    # re-lay the text for the wider frame
```

Because the ids carry over, the build script for the first format drives the second with only the
paths and text layout changed. Prebuild the second set of stills at 2560x1440.

Also tested 16:9 to 9:16 with rendered video clips: `saveProject` and `closeProject`, wait for
`appState.screen == "home"`, duplicate, then `setAspectRatio({ratio:"9:16"})` (1440x2560) and one
`replaceElementMedia` per clip. Dissolves and the imported music bed survive untouched. Give each
replacement a new filename; set `aspectRatio:"nineBySixteen"` in `setExportSettings` before the
second export.

## Work on a copy (tested)

On the home screen:

```
projects()                                                   -> ids
duplicateProject({id:<original>})                            -> new id, name "<name> copy"
openProject({id:<new id>})
```
