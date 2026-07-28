# Deployment

Two ways to run HavenHunter unattended. Pick one.

## In-process schedule (simplest)

Set `SCAN_INTERVAL_MINUTES` in your environment to a positive number. The bot's
own job queue then runs a full scan on that interval while it is up. Nothing
else to install.

```
SCAN_INTERVAL_MINUTES=30
python -m havenhunter.app
```

## OS-level agent (macOS launchd)

For a process that survives crashes and relaunches at login, use the example
agent in this folder.

1. Copy `com.havenhunter.bot.example.plist` to
   `~/Library/LaunchAgents/com.havenhunter.bot.plist`.
2. Replace every `/ABSOLUTE/PATH/TO/...` with your real paths.
3. Load it:

   ```bash
   launchctl load ~/Library/LaunchAgents/com.havenhunter.bot.plist
   ```

To stop it:

```bash
launchctl unload ~/Library/LaunchAgents/com.havenhunter.bot.plist
```

On Linux the equivalent is a `systemd` user service; the same command
(`python -m havenhunter.app`) and environment apply.
