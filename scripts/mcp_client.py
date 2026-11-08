#!/usr/bin/env python3
"""Minimal client for the Edits (metapilot-native) MCP server.

Reads the server URL and Authorization header from ~/.claude.json (user scope
entry "metapilot-native") and never prints the token.

Library use:
    from mcp_client import Client
    c = Client(); c.tool("appState")

CLI use:
    mcp_client.py tool <name> ['<json args>'] [image_dir]
    mcp_client.py list-tools [out.json]
    mcp_client.py resource <uri>
"""
import base64, json, os, sys, time, urllib.request

CONFIG = os.path.expanduser("~/.claude.json")
SERVER = "metapilot-native"


def _server_entry():
    cfg = json.load(open(CONFIG))
    entry = cfg.get("mcpServers", {}).get(SERVER)
    if not entry:
        sys.exit("metapilot-native is not registered in ~/.claude.json (user scope)")
    return entry["url"], entry.get("headers", {}).get("Authorization", "")


class Client:
    def __init__(self, timeout=180):
        self.url, self.auth = _server_entry()
        self.timeout = timeout
        self.sid = None
        self.n = 0
        self._rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                 "clientInfo": {"name": "edits-video-skill", "version": "1"}})
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _post(self, body):
        h = {"Authorization": self.auth, "Content-Type": "application/json",
             "Accept": "application/json, text/event-stream"}
        if self.sid:
            h["Mcp-Session-Id"] = self.sid
        req = urllib.request.Request(self.url, json.dumps(body).encode(), h)
        r = urllib.request.urlopen(req, timeout=self.timeout)
        self.sid = r.headers.get("Mcp-Session-Id") or self.sid
        t = r.read().decode()
        if not t.strip():
            return None
        if t.lstrip().startswith(("event", "data")):
            t = [l[5:].strip() for l in t.splitlines() if l.startswith("data:")][-1]
        return json.loads(t)

    def _rpc(self, method, params=None):
        self.n += 1
        return self._post({"jsonrpc": "2.0", "id": self.n, "method": method, "params": params or {}})

    def tool(self, name, args=None, image_dir=None):
        """Call a tool. Returns the parsed JSON payload of the first text block when possible.

        Inline images (captureFrame, frameSheet, previewVideo frames) are counted in `_images`.
        Pass image_dir to also write them to disk; their paths come back in `_imagePaths`.
        The app's own copies sit in its sandbox container, which other processes cannot read.
        """
        r = self._rpc("tools/call", {"name": name, "arguments": args or {}})
        if "error" in r:
            return {"ok": False, "rpcError": r["error"]}
        res = r["result"]
        texts = [c.get("text") for c in res.get("content", []) if c.get("type") == "text"]
        out = None
        if texts:
            try:
                out = json.loads(texts[0])
            except ValueError:
                out = {"text": texts[0]}
        if out is None:
            out = {}
        if isinstance(out, dict):
            if res.get("isError"):
                out.setdefault("ok", False)
            images = [c for c in res.get("content", []) if c.get("type") == "image"]
            if images:
                out["_images"] = len(images)
                if image_dir:
                    os.makedirs(image_dir, exist_ok=True)
                    stamp = time.strftime("%H%M%S")
                    paths = []
                    for i, img in enumerate(images):
                        ext = {"image/png": "png"}.get(img.get("mimeType"), "jpg")
                        path = os.path.join(image_dir, "%s-%s-%d.%s" % (name, stamp, i, ext))
                        with open(path, "wb") as f:
                            f.write(base64.b64decode(img["data"]))
                        paths.append(path)
                    out["_imagePaths"] = paths
        return out

    def list_tools(self):
        return self._rpc("tools/list")["result"]["tools"]

    def resource(self, uri):
        return self._rpc("resources/read", {"uri": uri})["result"]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    c = Client()
    cmd = sys.argv[1]
    if cmd == "tool":
        args = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
        image_dir = sys.argv[4] if len(sys.argv) > 4 else None
        print(json.dumps(c.tool(sys.argv[2], args, image_dir), indent=1))
    elif cmd == "list-tools":
        tools = c.list_tools()
        if len(sys.argv) > 2:
            json.dump({"result": {"tools": tools}}, open(sys.argv[2], "w"), indent=1)
        print("%d tools" % len(tools))
    elif cmd == "resource":
        print(json.dumps(c.resource(sys.argv[2]), indent=1))
    else:
        sys.exit(__doc__)
