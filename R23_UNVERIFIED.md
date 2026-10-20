# Preserved current local R23 source — no prerelease

This branch retains the newer local SOURCE and tests without changing the owner’s working directory. Source SHA-256: 93c5cc931f79d8212a3bf31cd881835fddada35c062498b3798aee42474456d0.

With the complete reference fixtures, 85/86 regression programs pass. test_arsenal_events.py detects State.draw_ok == false on the Player page at 2560×1440. The metadata still labels an older R16 candidate; it is preserved as found rather than silently relabelled. This branch is not the playable release and has no R23 download.

The main branch and R22 prerelease contain the most recent passing actual local build. Original R23 work and every local backup remain preserved. Continue repairs here before building/promoting a future version.
