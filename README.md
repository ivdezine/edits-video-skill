# edits-video-skill

A [Claude Code](https://docs.claude.com/en/docs/claude-code) skill for driving the Edits video
editor for macOS through the local MCP (Model Context Protocol) server the app exposes, registered
as `metapilot-native`. With it, Claude can open projects, cut, trim, split on beats or shots,
reframe, add text, captions, filters, transitions, LUTs, speed curves and music, check loudness,
inspect frames, confirm that beat-synced cuts land on the beat, and export.

The video below was cut in Edits by Claude with this skill, from scene renders to export:

https://github.com/user-attachments/assets/02225140-ad35-4ce3-80b6-6262c665d020

Not affiliated with, endorsed by, or supported by Meta. Edits is a Meta product; this repository
contains only notes and scripts written against the app's local server.

## Status

- Tested against **Edits 454.0.0** for macOS (server `metapilot-native` 1.0.0) on 2026-11-08. The
  beat-synced cut recipe was retested on 2026-11-09.
- The server is not publicly documented and may change with any app update. Where the live server
  disagrees with these notes, the server wins: regenerate the references (below) and recheck.

## What is here

| path | contents |
|---|---|
| `SKILL.md` | the skill: workflow, catalog apply tools, the rules that bite |
| `references/conventions-and-gotchas.md` | units, coordinates, schema traps, measured timings |
| `references/recipes.md` | call sequences for common edits, each marked tested or untested |
| `scripts/mcp_client.py` | a dependency-free Python client for the server (library and CLI) |
| `scripts/build_references.py` | generates the tool reference and catalog ids from your own app |

Two reference files are deliberately not shipped: `references/tool-reference.md` (every tool with
its parameters) and `references/catalogs.md` (every filter, effect, transition, LUT, font, preset
and caption style id). They quote the app's own descriptions, so you generate them locally from
your installed version.

## Install

1. Clone into your skills folder:

   ```bash
   git clone https://github.com/ivdezine/edits-video-skill.git ~/.claude/skills/edits-video
   ```

2. In Edits, turn on its MCP server and copy the token the app shows for it. The server listens on
   `http://127.0.0.1:19501/mcp` while the app is running.

3. Register the server with Claude Code at user scope, replacing `<token>`:

   ```bash
   claude mcp add --transport http --scope user metapilot-native http://127.0.0.1:19501/mcp --header "Authorization: Bearer <token>"
   ```

   `scripts/mcp_client.py` reads the URL and token from that entry in `~/.claude.json` and never
   prints the token. Keep the token out of commits, logs and chat.

4. Generate the references. With Edits running on its home screen:

   ```bash
   python3 ~/.claude/skills/edits-video/scripts/build_references.py --catalogs-only
   ```

   For the full tool reference, pass a project to open read-only (it is closed again afterwards,
   and nothing in it is edited). Get an id from `python3 scripts/mcp_client.py tool projects`:

   ```bash
   python3 ~/.claude/skills/edits-video/scripts/build_references.py --project-id <uuid>
   ```

   Rerun this after every Edits update.

## Using it

Ask Claude Code to do something in Edits ("open my latest project and cut it to the beat"). The
skill loads on its own when Edits is mentioned. The app must be running, and every call acts on the
live app, so edits are real and immediate. Work on a duplicate of any project you care about.

The client also works on its own:

```bash
python3 scripts/mcp_client.py tool appState
python3 scripts/mcp_client.py list-tools tools.json
```

If Claude reports an Edits tool as missing, `python3 scripts/mcp_client.py doctor` says which of
three things is wrong: the server cannot be reached (Edits closed, its server off, or a stale
token), no project is open yet, or the session simply has not reloaded the tool list.

## Releases

What changed in each version is on the
[releases page](https://github.com/ivdezine/edits-video-skill/releases). If you installed with
`git clone`, update with `git pull` in `~/.claude/skills/edits-video`; your generated references are
not touched.

## License

MIT, see `LICENSE`. Covers the notes and scripts in this repository only.
