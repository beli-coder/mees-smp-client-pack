# Mees SMP 0.4 server content upgrade — Hagrid playbook

## What changes

The Fabric 26.3 server needs **five** shared gameplay mods, plus
**Forge Config API Port** (required dependency for Traveler's Backpack).
This playbook also pins Fabric API from the tested client lockfile:

| New/mod compatibility | Locked file |
|---|---|
| Farmer's Delight Refabricated | \`FarmersDelight-26.3-3.6.28+refabricated.jar\` |
| Naturalist | \`naturalist-2.0.6-fabric-26.3.jar\` |
| Skniro's Furniture | \`SkniroFurniture-1.6.1-26.3-Fabric.jar\` |
| Traveler's Backpack | \`travelersbackpack-fabric-26.3-11.4.1.jar\` |
| Origins: Legacy | \`Origins-Legacy-1.12.20+26.3.jar\` |
| Forge Config API Port | exact Fabric 26.3 pin from \`profiles/lite/pack.lock.json\` |
| Fabric API | exact pin from \`profiles/lite/pack.lock.json\` |

Do NOT install Distant Horizons, Iris, Sodium, Litematica, or other
client utilities on the server. The currently running server does not need
any configuration changes until we finish staging tests.

## 1. Prepare safely on Hagrid

On Hagrid as \`crasch\`:

\`\`\`bash
cd ~/mees-pack-pipeline
git status --short
git pull --ff-only origin main
python3 -m unittest discover -s tests -v
python3 scripts/prepare_hagrid_upgrade.py --verify-only
python3 scripts/prepare_hagrid_upgrade.py \
  --server /opt/minecraft/server \
  --stage "$HOME/mees-0.4-staging"
\`\`\`

The command makes an isolated stage directory under your home directory.
It downloads only the seven server modules from the **existing committed
Modrinth lockfile**, verifies their SHA-512 hashes and expected sizes, and
replaces old versions **only inside the stage**. No server shutdown occurs.

It **does not copy the production world** (you will test on a disposable,
new world first), and rewrites staging's \`server.properties\` to bind
\`127.0.0.1:25575\`. Staging-only copies of Geyser, Floodgate, Simple Voice
Chat, BlueMap, Just Enough Backups, ServerPassword, and Chunky are moved to
\`mods-disabled-in-staging\` so their network ports and external backup
configuration cannot collide with production. The live server, mods,
world, and service are untouched.

If the command fails, the partial staging folder is discarded.
If staging already exists, it refuses to overwrite it.

## 2. Boot the disposable staging server

Identify the actual launcher in your existing service definition; do not
guess its name or reuse the production working directory.

\`\`\`bash
sudo systemctl cat minecraft.service
find ~/mees-0.4-staging -maxdepth 1 -name '*.jar' -printf '%f\n'
java -version
\`\`\`

Start staging **from the staging directory** using the same Fabric launcher
as in the service definition, but with a smaller JVM heap and **without**
production-only service flags. For example (replace the JAR filename with
the real one):

\`\`\`bash
cd ~/mees-0.4-staging
java -Xms1G -Xmx4G -jar YOUR_FABRIC_SERVER_LAUNCHER.jar nogui
\`\`\`

Do not run the production \`systemctl\` command in place for staging:
it would use the wrong \`WorkingDirectory\`, ports, backup destination,
or Java command. Check the staging terminal for "Done" and review any
missing dependency, mixin, or mod incompatibility errors. Connect through
an SSH tunnel if desired (local port 25575); do not expose this port to
the internet.

Smoke-test with a **v0.4.0 Lite/Technical client**, then confirm:
Farmer's Delight cooking and crops; Naturalist mobs; Skniro's Furniture
items and placement; Traveler's Backpack equipping and inventory;
Origins selection, abilities and limitations. Stop with \`stop\` in
the staging console, NOT \`systemctl stop minecraft\`.

## 3. Existing world and production deployment — gate, not yet automatic

Before touching production, plan a short maintenance window and tell
players the server will require a modded Java/Fabric client. Bedrock/
vanilla crossplay must not be promised after the mandatory content upgrade.
Make a JEB backup **and** an independent offsite/VM snapshot.

For the existing-world compatibility test, arrange a consistent world
snapshot with Minecraft fully stopped while copying it. Do not copy a
live-changing world directory and call it a valid backup. Test restoration
to a *separate* staging directory before the production change.

Only after both fresh-world and restored-world staging tests pass:

1. Notify players; set the server in maintenance/offline mode.
2. Stop \`minecraft.service\`, verify it is inactive, and create a new,
   restorable copy of the current world and mods with the service stopped.
3. Install the staged, pinned server JARs after reviewing removed/
   replaced versions. Keep the existing server-only mods.
4. Restart the server and verify logs, TPS, connection, player inventories,
   Origin selection, modded blocks, voice chat and backups.
5. Keep a rollback plan that restores BOTH the old mods AND the matching
   pre-upgrade world. Never load a modded world and then simply remove its
   content mods; blocks/items can be lost.

**No automatic or blind "upgrade production" command is provided.**
The staging run is the safe first step; it does not imply Hagrid has
already been updated.
