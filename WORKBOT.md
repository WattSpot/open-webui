# Workbot fork

This branch is based on upstream `v0.13.3` (`b0e6098e940942281d9c83f3529ea117287a3a22`). Keep the fork limited to native file configuration and preview annotations; use upstream Open Terminal and native Codex sessions.

`python backend/open_webui/__init__.py serve --config /path/config.json` loads explicit `startup` and registered `config` values before application imports. File-owned settings override database values and reject conflicting writes. It supports one Uvicorn worker. Secrets continue through upstream secret inputs; the file does not export environment variables. Bootstrap administrator name/email may be file-owned; the bootstrap password is a separate secret.

A terminal's administrator-owned `config.previews` contains `{id, label, url}` entries. The browser receives only these fields and renders fixed iframe tabs. The preview implements the `open-webui-preview` version 1 postMessage protocol: connect/ready, pick/selection and cancel, using an exact parent origin and per-frame nonce. Selection carries a real checkout root, query-free URL, selector, tag, role, label and bounded text. No browser automation, MCP or model request is needed to collect comments.

Comments stay in the chat draft until Send. Send validates one native Codex model and matching terminal/checkout, checks workspace reachability, then adds ordinary prompt context. Existing signed Codex state owns the conversation directory. Failed preflight preserves the draft; the client does not autostart a workspace or fall back to a different model. Native Open WebUI authorization remains the backend boundary.

Run the focused checks with the normal frontend and slim backend dependencies installed:

```bash
python -m unittest discover -s backend/tests -p 'test_*config.py'
npx vitest run src/lib/utils/previewAnnotations.test.ts src/lib/components/chat/ChatTabs/tabs.test.ts
npm run build
```

The upstream type-check baseline already contains thousands of diagnostics. Compare diagnostic identities against the unchanged tag; do not treat equal counts as proof. The Workbot workflow builds a slim Linux image, runs backend contracts inside that image, then publishes a commit-specific tag. Deployment must pin the resulting digest.
