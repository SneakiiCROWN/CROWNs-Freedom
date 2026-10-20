# Preserved local source and public package

Runtime source and all 122 art/audio/asset-manifest files match the actual local R22 SDK mod. Runtime SHA-256: 431eba03c60548961d9e0174b7b912b6db18b82451730cd1cc246f63c20ce203.

The original SDK mod remains untouched locally (SHA-256 3ffa1eedb3feae2b251216d1e755c47f24a1937f863590030e014ea2111096b3). Its non-runtime reference folder contained private crash logs, user directives and unrelated upstream archives. Those files are excluded from this public source/package; they are not rewritten or deleted from the original.

Latest local R23 source is retained separately, SHA-256 93c5cc931f79d8212a3bf31cd881835fddada35c062498b3798aee42474456d0. With complete fixtures it passes 85/86 offline programs; test_arsenal_events.py detects a Player-page render failure. It has no prerelease asset.

R22 passes all 86 programs with 15 expected-release-identity string adjustments in inherited tests, recorded separately. Runtime/behaviour assertions are unchanged. The test fixture reference files are safe asset hash and credit documents. Public build automation packages only the reviewed tree and never changes the installed game or its settings.
