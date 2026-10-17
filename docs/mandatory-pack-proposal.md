# Proposal: Mees SMP Lightly Modded Content Pack

This is a **proposal only**, separate from the optional client pack. It must not be automatically installed on Hagrid.

| Candidate | Why people might want it | Decision needed |
|---|---|---|
| Farmer's Delight Refabricated | Food, crops, cooking, player cafés | Vote on client requirement; evaluate Polymer server-only variant separately |
| Naturalist | More animals and wildlife | Vote; test spawn behavior and server performance |
| Skniro's Furniture | More decoration and player-built interiors | Vote; test client + server dependency and Bedrock incompatibility |
| Traveler's Backpack | Portable inventory for mining and travel | Voted-in replacement for Packed Up; balancing, dupe testing and recipes |
| Origins: Legacy | Player powers and limitations | Community poll supported this addition; still requires progression and PvP balancing |

Questions before approving a mandatory pack:

1. Are any *confirmed* players using Bedrock who can't switch to Java?
2. Is installing a Modrinth client profile acceptable to everyone who expects to play?
3. Are content additions supported by the **exact Minecraft 26.3 / Fabric** versions and dependencies currently deployed?
4. Does adding new content require new terrain? Hagrid's Overworld, Nether and End are already pregenerated; new structures may only generate in fresh chunks.
5. Can we run a copy of the world in staging and test C2ME, Geyser loss, graves, data migration, backup restore and mod removal?
6. When should changes go live? Not while players are active or hours before an announced launch.

**Do not try to make incompatible content mods vanilla-compatible by removing the client dependency in fabric.mod.json.** That can crash clients, silently break gameplay, or corrupt modded blocks. Real vanilla/Bedrock compatibility needs the mod's authors to provide appropriate fallback implementations (e.g. Polymer), tested on a world copy.

Make two votes: (1) accept losing vanilla/Bedrock access and needing a modpack, and (2) which specific mods are worth that tradeoff. No single player's suggestions should be treated as accepted by default.
