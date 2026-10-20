# CROWN’S FREEDOM

An experimental ECHO-style mod menu for **Borderlands 4 on Windows**. This is a PythonSDK mod, so it launches inside the game rather than as a separate EXE.

**Public checkpoint: 5.26.0 ECHO Fieldcraft R22.** It comes from the actual local R22 `.sdkmod` built on 19 October. The newer local R23 source fails a Player-page rendering regression and is preserved on the `development/r23-unverified` branch, without a playable release.

## Download and install

1. [Download the Windows mod ZIP](https://github.com/SneakiiCROWN/CROWNs-Freedom/releases/download/freedom-v5.26.0-r22-public-test-20261020/CROWNs-Freedom-Windows-R22-Test.zip) and choose **Extract All**.
2. Close Borderlands 4. If PythonSDK is not already installed, follow the [official BL4 SDK guide](https://bl-sdk.github.io/oak2-mod-db/) first. CROWN does not bundle or replace that loader.
3. Keep a backup of your current CROWN mod outside `sdk_mods`. Copy **CROWNs_Freedom_v5_26_ECHO_Fieldcraft_R22.sdkmod** into the game’s `sdk_mods` folder. Keep exactly one CROWN version active.
4. Start the game normally and press **F7**. No source build, Python install or extra launcher is needed for the mod.

## Controls

- **F7:** menu; **F11:** Quick Dock; **F8:** Travel Hub.
- **F6:** emergency close/unstuck; **F9:** focus recovery/diagnostics; **F10:** restore owned temporary effects.
- **F5:** hold-to-boost noclip when that mode is enabled.
- **L3 + R3:** controller menu chord. Controller operation still needs physical testing.

F10 does not undo permanent save changes. Keep save backups before experimenting.

## Current features and limits

The source includes the ECHO menu and Quick Dock, guarded item-pool spawning, wallet/XP tools, temporary combat/movement profiles, travel/bookmarks, appearance editing and optional community-mod adapters. Host authority, consent and competing-mod protections remain intact.

**86/86 offline regression programs passed** against the exact R22 runtime source. Only expected release-name strings in inherited tests were adjusted to R22; behavioural checks remain. The packaged SDK mod is CRC/hash checked and tested through an isolated synthetic SDK import/menu startup.

**Live BL4 gameplay is unverified.** The historical reopen/access-violation crash remains an open gate. Spawn/XP receipts, physical controller input, gamepad focus, co-op replication and native art/audio need real-game tests. Missing optional Arena, BL4Live or XP add-ons leave their integrations unavailable; those third-party programs are not bundled.

**Compatibility:** Windows PC Borderlands 4 / Oak2 PythonSDK, Python 3.12+. The project targets unrealsdk 3.2.0 and pyunrealsdk 1.10.0. No specific BL4 patch version or current-patch compatibility is certified. Use the official SDK build for your game; console support is not provided.

Next work is fixing the preserved R23 menu regression, native reopen stability and verified item/XP outcomes, then controller and optional-adapter testing. These are unfinished goals, not confirmed fixes.

## Update or remove

With the game closed, move the previous CROWN `.sdkmod` outside `sdk_mods`, then copy in the new one. Keep old downloads for rollback. Leave the SDK `settings` folder and character saves intact. To remove CROWN, remove only its `.sdkmod`; keep the SDK and unrelated mods. No game binaries, DLLs, DLC, player saves or private logs are included.

Artwork, sound and selected community-code/data credits are in `REFERENCE/SOURCE_CREDITS.md` and `REFERENCE/THIRD_PARTY_CREDITS_V5_10.md`. Third-party licences remain intact; see `LICENSE.txt` for original project material.

[Report a bug](https://github.com/SneakiiCROWN/CROWNs-Freedom/issues) with the release, game/SDK versions and reproduction steps. Keep private saves and raw account logs out of public reports.
