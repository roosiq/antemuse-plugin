# Plugin updates — say it in a message, not only in a slash command

Status: **implemented** 2026-11-08. Owner: Ryan Cook.

## Problem

The plugin's only channel to the person was the reply text of a slash command. On
Discord that channel is fragile: app commands are capped at 100, this machine already
syncs 95, and `sync()` skips the batch when the fingerprint is unchanged — so a command
that exists in the code may not exist in the client. Anything that must be *seen* cannot
depend on being *typed*.

## Requirement

A recommendation — the one message the plugin originates rather than answers — is posted
through the host's own message channel (`PluginContext.post_message`), which works on
every platform Hermes supports and needs no command registration.

Rules:

1. **One message per cooling window** (45 minutes), never per turn.
2. **Never on the human card and never as a tool block** — text only, no words on the
   picture.
3. **Fail-open:** a platform that refuses the message must not cost the turn; the failure
   is logged, not raised.
4. **No new command.** The update replaces a command, it does not add one.

## Acceptance criteria

1. A fired recommendation calls `post_message` exactly once and is not repeated for the
   same line.
2. With no host, or a host without `post_message`, nothing raises and nothing is posted.
3. State entry, exit and expiry remain driven by the reply to the command that asked for
   them; this mechanism exists only for messages nobody asked for.

## Must not change

`/return`, `CONTROL_TOOLS`, state definitions, durations, turn budgets, cadence, the
no-words rule on the human card, and the rule that rendering never needs a model call.
