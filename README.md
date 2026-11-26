# corylus-companions

Character packs for the [Corylus](https://github.com/LudoBermejoES/corylus) writing
app's **Companions** module: the characters a writer can choose to keep them
company in a small window of their own (Ogam, the old sage, first).

This repo holds the **source of each pack** (manifests, hand-written line
catalogs in English and Spanish, credits). The packs themselves are published as
**GitHub Release assets** and downloaded by the app on request, never bundled with
it. The app pins every asset by URL, SHA-256 and size, and installs it only if the
download matches.

## What a pack contains

Data only, never code:

| File | Purpose |
|---|---|
| `character.json` | Identity, names (EN/ES), description, personality, chat persona, size, credits |
| `<id>.riv` or sprites | The animated art (Rive template re-skin; phase 0 uses three sprites) |
| `lines.en.json`, `lines.es.json` | Hand-written lines per situation |
| `CREDITS` | Art and writing credits |

The schema, the emotion contract and the validator live in the main Corylus repo
(`scripts/validate-characters.mjs`). Every pack must pass it before a release.

## Releases

- `companions-base-vX.Y.Z.zip`: the base pack, with Ogam. Installing the Companions
  module downloads this.
- `character-<id>-vX.Y.Z.zip`: one per extra character, installed on its own.

A new pack or version needs a new pinned entry in a Corylus release.

## Rights

The character art and lines are © Ludo Bermejo, published for use inside Corylus.
