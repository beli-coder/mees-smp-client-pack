# Mees SMP — Lite & Technical (v0.4.0 candidate)

**Minecraft Java 26.3 · Fabric Loader 0.19.5**

This repository builds two Modrinth-ready client editions for the same Mees SMP server. **Version 0.4.0 is staged for testing, not deployed to the live server.** Existing 0.3.0 release users should remain on their current packs until the content upgrade is approved and deployed.

## Editions

| | Lite | Technical |
|---|---|---|
| Audience | Casual players who want fewer extras | Builders, redstone engineers, technical players |
| Shared gameplay | Farmer's Delight Refabricated, Naturalist, Skniro's Furniture, Traveler's Backpack, Origins: Legacy | The same five gameplay mods |
| Graphics and navigation | Sodium, Iris, Distant Horizons (configurable), performance fixes, Xaero maps | Same, plus Continuity, dynamic lights, animations and visual polish |
| Multiplayer | Simple Voice Chat | Simple Voice Chat |
| Inventory/UI | Mouse Tweaks, AppleSkin, Shulker Box Tooltip, Mod Menu | Same, plus Inventory Profiles Next, Jade, BetterF3 and other HUD tools |
| Building | Basic vanilla building | Litematica, MiniHUD, MaLiLib, JEI |

**Origins: Legacy** is an unofficial compatible port. The original Origins project does not list Minecraft 26.3 support.

**Distant Horizons** is now in both editions, but is adjustable/disableable for low-performance systems. It was already included in Technical.

## Critical server migration requirement

The five gameplay mods change the Minecraft content registry and require matching server-side mods. The current Hagrid server remains untouched. Do **not** publish these builds as replacements for the optional 0.3.0 packs until a staging world has passed compatibility tests and a coordinated upgrade is announced.

Moving to a mandatory gameplay modpack will likely exclude vanilla Java and Bedrock clients unless separate server-side compatibility solutions are tested. Back up the world first, test existing saves and client connections, confirm the server's Fabric loader and all dependencies, and plan a maintenance window. Pregenerated chunks may not get new world-generation content.

The staged manifests are:
- Technical: `manifest.json` and `pack.lock.json`.
- Lite: `profiles/lite/manifest.json` and `profiles/lite/pack.lock.json`.

The GitHub workflow resolves and commits lockfiles when manifests change. Release-tag publication remains opt-in through `MODRINTH_AUTO_PUBLISH=true` or a manually requested workflow dispatch; do not turn on Modrinth publishing before testing.

## Building locally

```bash
python3 -m unittest discover -s tests -v
python3 scripts/modpack.py lock --profile technical
python3 scripts/modpack.py lock --profile lite
python3 scripts/modpack.py build --profile technical
python3 scripts/modpack.py build --profile lite
```

Expected outputs:
- `dist/Mees-SMP-Client-0.4.0.mrpack` (Technical).
- `dist/Mees-SMP-Lite-0.4.0.mrpack` (Lite).

## Modrinth project

Both editions are version entries under the same [Mees SMP Modrinth project](https://modrinth.com/project/mees-modpack):
`0.4.0-lite` and `0.4.0-technical`. They are distinct labeled releases, not independent automatic-update channels.

The repository secret `API_TOKEN_MODRINTH` is used only during Modrinth uploads. Do not expose it in commits, documentation or chats.

**Extended description ready to paste:** [docs/modrinth-description.md](docs/modrinth-description.md).

## Server and community

- Java server: `mees.clayton.engineer` (current configuration still unchanged).
- World map: https://map.clayton.engineer
- Discord: https://discord.gg/m8gB5gX9HP
