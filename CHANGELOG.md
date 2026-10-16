# Changelog

## 0.2.2 — CI release repair

- Align the client manifest with the intended release, upgrade the Zoomify Fabric dependency resolver, and keep pinned builds for tags.
- Refresh and commit the lockfile when the manifest changes on main, instead of failing on an obsolete lockfile.
- Retain Node.js 24-compatible GitHub Actions.

## 0.2.0 — Deluxe client pack (draft, pending live dependency lock and test)

- Expanded from 8 to 31 explicitly requested Fabric 26.3 mods plus their required libraries.
- Added a full default rendering stack: Sodium, Iris, Distant Horizons, ImmediatelyFast, Entity Culling, Reese's Sodium Options, Continuity, LambDynamicLights, Visuality and Not Enough Animations.
- Added inventory features: Mouse Tweaks, Shulker Box Tooltip, AppleSkin, Jade, Tooltip Scroll and Held Item Info.
- Added BetterF3, Zoomify, Chat Heads, Better Mount HUD and Advancement Plaques.
- Added JEI recipe browsing, Litematica and MiniHUD for builders.
- Improved dependency resolution to reuse exact pinned dependencies instead of mistakenly selecting a second newer version when the same project appears by slug and by project ID.
- Added a SHA-256 of the complete manifest to the lockfile, preventing stale-pack builds.
- Added offline resolver tests and tag/manifest version checks to GitHub Actions.
- No server-side or mandatory-content mods added to this pack.

## 0.1.0 — Initial optional client pack

- Fabric 26.3 base with voice, Xaero maps, Sodium, Iris, Distant Horizons and Inventory Profiles Next.
- `.mrpack` builder, GitHub workflow, Xaero Fair Play datapack installer and mandatory-pack proposal.
