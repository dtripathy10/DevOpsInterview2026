# How do you schedule a task to run periodically in Linux
## Option 1: cron (most common)

**Example task:** every 5 minutes, check disk usage and log a warning if it's above 80%.

**Step 1: Write the script** at `/usr/local/bin/check-disk.sh`:

```bash
#!/bin/bash
USAGE=$(df / --output=pcent | tail -1 | tr -dc '0-9')
if [ "$USAGE" -gt 80 ]; then
  echo "$(date '+%F %T') WARNING: disk at ${USAGE}%"
fi
```

```bash
sudo chmod +x /usr/local/bin/check-disk.sh
```

**Step 2: Test it by hand** before scheduling:

```bash
/usr/local/bin/check-disk.sh
```

**Step 3: Add the schedule.**

```bash
crontab -e
```

```
*/5 * * * * /usr/local/bin/check-disk.sh >> /var/log/check-disk.log 2>&1
```

**Step 4: Verify.**

```bash
crontab -l                      # shows your schedule
tail -f /var/log/check-disk.log # watch the output (the file needs to be writable by your user)
grep CRON /var/log/syslog       # Debian/Ubuntu; use journalctl -u cron or /var/log/cron on RHEL
```

### Reading the schedule

```
┌───────── minute (0-59)
│ ┌─────── hour (0-23)
│ │ ┌───── day of month (1-31)
│ │ │ ┌─── month (1-12)
│ │ │ │ ┌─ day of week (0-7, Sunday is 0 or 7)
* * * * *  command
```

| Schedule | Meaning |
|---|---|
| `*/5 * * * *` | Every 5 minutes |
| `0 * * * *` | Every hour, on the hour |
| `30 2 * * *` | Daily at 02:30 |
| `0 9 * * 1-5` | 09:00 on weekdays |
| `0 0 1 * *` | Midnight on the 1st of each month |

## Option 2: systemd timer (modern alternative)

Better logging, easier status checks, and it can catch up on missed runs.

`/etc/systemd/system/check-disk.service`:
```ini
[Unit]
Description=Check disk usage

[Service]
Type=oneshot
ExecStart=/usr/local/bin/check-disk.sh
```

`/etc/systemd/system/check-disk.timer`:
```ini
[Unit]
Description=Run disk check every 5 minutes

[Timer]
OnCalendar=*:0/5
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now check-disk.timer

systemctl list-timers | grep check-disk   # next and last run
journalctl -u check-disk.service          # output and errors
```

Output goes to the journal automatically, so no `>>` redirect is needed. `Persistent=true` runs a missed job after the machine was off.

## Common reasons a cron job "doesn't run"

| Problem | Fix |
|---|---|
| Script not executable | `chmod +x` |
| Relative paths or missing `PATH` (cron's environment is minimal) | Use absolute paths, or set `PATH=...` at the top of the crontab |
| Works by hand, fails in cron | Environment differences: variables, working directory, shell. Test with `env -i /bin/bash script.sh` |
| No output anywhere | Redirect with `>> file 2>&1`, otherwise errors go to local mail or nowhere |
| Wrong time | Cron uses the server's timezone (check `timedatectl`) |
| Runs overlap | Use `flock -n /tmp/job.lock script.sh` to stop a second copy starting while the first is running |
| Edited the wrong crontab | `crontab -l` is per user, and `sudo crontab -l` is root's. System jobs live in `/etc/crontab` and `/etc/cron.d/` (these have an extra user column) |

An overlap-safe version of the line:

```
*/5 * * * * flock -n /tmp/check-disk.lock /usr/local/bin/check-disk.sh >> /var/log/check-disk.log 2>&1
```

## In containers and Kubernetes

- **Docker:** running cron inside a container is awkward. Prefer a scheduler outside it, such as a host cron job calling `docker run --rm myimage` or a systemd timer.
- **Kubernetes:** use a `CronJob`, which uses the same cron syntax:
  ```yaml
  apiVersion: batch/v1
  kind: CronJob
  metadata:
    name: check-disk
  spec:
    schedule: "*/5 * * * *"
    concurrencyPolicy: Forbid
    jobTemplate:
      spec:
        template:
          spec:
            restartPolicy: OnFailure
            containers:
            - name: check
              image: busybox
              command: ["sh", "-c", "date; echo checking"]
  ```
  `concurrencyPolicy: Forbid` is the equivalent of the `flock` protection.

## Interview-ready answer

"I'd write the script, test it manually, then schedule it with cron using absolute paths and log redirection, or with a systemd timer if I want better logging and catch-up behavior. I'd guard against overlapping runs with `flock`, and check the schedule and logs to confirm it ran. In Kubernetes I'd use a CronJob with `concurrencyPolicy: Forbid`."
