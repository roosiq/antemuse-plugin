# Desktop harness

Mounts the real `desktop/plugin.js` outside the app, so the pane can be checked
where Hermes Desktop is not installed.

```bash
./tools/desktop_harness/setup.sh      # symlink react/react-dom/jsdom from the app checkout
node tools/desktop_harness/mount.mjs
```

`setup.sh` reads `HERMES_APP_NODE_MODULES`, defaulting to
`~/.hermes/hermes-agent/node_modules`. It installs nothing: it links the
three packages and writes a `@hermes/plugin-sdk` stub beside the harness, because
`plugin.js` imports only constants from that alias.

What the mount proves: the plugin registers a pane, a status chip and a palette
command (never a pane alone, which would disable the plugin when the pane closed);
the pane polls `ctx.rest('/state')` every 2 s through `ctx.setInterval`; an active
state renders its label, counts, contract and glyph lines with the art marked
`aria-hidden`; idle renders `no state` and no frame; a missing backend renders
`backend unavailable` rather than an empty box.

What it cannot prove: CSS, pane placement, or the real gateway transport. Those
need the app, and the change record says so instead of implying otherwise.
