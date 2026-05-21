# Discord Social SDK files

This branch intentionally contains only the Discord Social SDK payload used by
the Dungeon Blitz native bridge.

The normal game branches keep `src/server/native_bridge/discord_social_sdk/`
out of the tracked tree so single-player users do not need to download the SDK.
Run the installer script from a project branch to restore this folder locally:

```sh
npm run install:discord-social-sdk
```

The SDK binaries are stored with Git LFS on this branch.
