# Learn systemd by running a Python application

The best way to learn `systemd` is to build a small Python service and let Linux manage its entire lifecycle: starting it, passing configuration, restarting it after failure, checking its health, and shutting it down gracefully.

We'll build a working HTTP application and a production-style service definition, using the same concepts you'll encounter when deploying Java microservices, Python automation jobs, or platform services on Linux.

## 1. What is systemd?

`systemd` is the service manager used by many Linux distributions. It runs and supervises processes independently of your terminal session.

Imagine you have a Python application called `payment-api.py`. You could start it manually:

Bash

```
python3 payment-api.py --port 8088
```

But that leaves several problems. What happens if the SSH session closes? What happens if the process crashes? How will it start after a server reboot? Where do you find its logs?

`systemd` manages those responsibilities.

systemd service manager

Reads the unit file and manages the process lifecycle.

Configuration

Command-line arguments, environment variables, working directory and user.

Supervision

Startup, readiness, restart policy, stop signals and timeouts.

Observability

Service status, exit codes and logs in the system journal.

Security

Service user, filesystem permissions and process restrictions.

Python HTTP application

Receives arguments, environment variables and signals.

A `systemd` service is normally described by a file ending in `.service`. The directives in that file configure systemd's behaviour; they do not all become parameters passed to Python. We'll implement both kinds: application configuration and systemd's process-management protocol. The official service and execution documentation describes these separately.

![](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1

## 2. Understand the three types of parameters

Before writing code, understand this distinction.

| Type                   | Example              | What happens                                                                       |
| ---------------------- | -------------------- | ---------------------------------------------------------------------------------- |
| Command-line arguments | `--port 8088`        | Python receives them through `sys.argv` and `argparse`.                            |
| Environment variables  | `APP_ENV=production` | Python reads them using `os.environ` or `os.getenv()`.                             |
| systemd directives     | `Restart=on-failure` | systemd enforces the behaviour; Python does not receive this as a normal argument. |

For example, `User=pyapp` determines which Linux user runs the application. `WorkingDirectory=/opt/demo-python` sets its current directory. `Restart=on-failure` controls what happens if its process exits unsuccessfully.

Python needs no special code to understand these three directives. It experiences their effects.

We will also implement two important systemd-to-application messages:

* `READY=1` — tells systemd that the service has completed startup.

* `WATCHDOG=1` — tells systemd that the running service is still responding.

These are especially valuable for long-running production services.

![](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1

## 3. Build the Python application

Our example will expose three HTTP endpoints:

| Endpoint  | Purpose                                                                          |
| --------- | -------------------------------------------------------------------------------- |
| `/`       | Returns a message and application details.                                       |
| `/health` | Returns a basic health response.                                                 |
| `/config` | Shows the application's configuration and selected systemd-provided information. |

We'll use Python's standard library, so you do not need Flask, FastAPI, or any third-party packages.

Create a file called `app.py` and add the following code.

Python

Run

```
#!/usr/bin/env python3

import argparse
import json
import logging
import os
import signal
import socket
import threading

from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


def systemd_notify(message):
    """
    Send a message to systemd using its notification socket.

    Examples:
        READY=1       Application has finished starting.
        WATCHDOG=1    Application watchdog heartbeat.
        STOPPING=1    Application is shutting down.
    """
    notify_socket = os.getenv("NOTIFY_SOCKET")

    # Running outside a systemd notification-enabled service?
    if not notify_socket:
        return False

    # Linux abstract Unix sockets use '@' in the environment variable.
    address = (
        "\0" + notify_socket[1:]
        if notify_socket.startswith("@")
        else notify_socket
    )

    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
            sock.connect(address)
            sock.sendall(message.encode("utf-8"))
        return True
    except OSError:
        logging.exception("Failed to notify systemd")
        return False


def get_arguments():
    parser = argparse.ArgumentParser(description="Example systemd-managed API")

    # Environment variables provide defaults.
    # Explicit command-line arguments take precedence.
    parser.add_argument(
        "--host",
        default=os.getenv("APP_HOST", "127.0.0.1"),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("APP_PORT", "8088")),
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=os.getenv("LOG_LEVEL", "INFO").upper(),
    )

    return parser.parse_args()


def main():
    args = get_arguments()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(message)s",
    )

    app_env = os.getenv("APP_ENV", "development")
    instance_name = os.getenv("INSTANCE_NAME", "local-instance")
    app_message = os.getenv("APP_MESSAGE", "Hello from Python!")

    # systemd creates this directory when StateDirectory= is configured.
    # The fallback allows the application to run outside systemd too.
    state_dir = Path(
        os.getenv("STATE_DIRECTORY", "/tmp/demo-python-state")
    )
    state_dir.mkdir(parents=True, exist_ok=True)

    # Demonstrate persistent application state.
    start_record = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "pid": os.getpid(),
        "instance": instance_name,
        "environment": app_env,
    }

    (state_dir / "last-start.json").write_text(
        json.dumps(start_record, indent=2),
        encoding="utf-8",
    )

    try:
        watchdog_usec = int(os.getenv("WATCHDOG_USEC", "0"))
    except ValueError:
        watchdog_usec = 0

    # These values are read from the environment created for the process.
    systemd_info = {
        "invocation_id": os.getenv("INVOCATION_ID"),
        "state_directory": str(state_dir),
        "runtime_directory": os.getenv("RUNTIME_DIRECTORY"),
        "notify_socket_available": bool(os.getenv("NOTIFY_SOCKET")),
        "watchdog_interval_usec": watchdog_usec,
    }

    application_config = {
        "host": args.host,
        "port": args.port,
        "log_level": args.log_level,
        "app_env": app_env,
        "instance_name": instance_name,
        "message": app_message,
    }

    class RequestHandler(BaseHTTPRequestHandler):

        def send_json(self, status_code, data):
            body = json.dumps(data, indent=2).encode("utf-8")

            self.send_response(status_code)
            self.send_header(
                "Content-Type", "application/json; charset=utf-8"
            )
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = urlsplit(self.path).path

            if path == "/":
                self.send_json(200, {
                    "message": app_message,
                    "instance": instance_name,
                    "environment": app_env,
                })

            elif path == "/health":
                self.send_json(200, {
                    "status": "ok",
                    "instance": instance_name,
                })

            elif path == "/config":
                self.send_json(200, {
                    "application": application_config,
                    "systemd": systemd_info,
                })

            else:
                self.send_json(404, {"error": "Not found"})

        def log_message(self, format_string, *args):
            logging.info(
                "client=%s %s",
                self.client_address[0],
                format_string % args,
            )

    # Creating this server binds the listening socket.
    server = ThreadingHTTPServer(
        (args.host, args.port),
        RequestHandler,
    )
    server.daemon_threads = True

    stop_requested = threading.Event()
    watchdog_stop = threading.Event()

    def handle_signal(signum, frame):
        logging.info(
            "Received %s; graceful shutdown requested",
            signal.Signals(signum).name,
        )
        stop_requested.set()

    # systemd normally sends SIGTERM when stopping this service.
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    server_thread = threading.Thread(
        target=server.serve_forever,
        kwargs={"poll_interval": 0.5},
        name="http-server",
    )
    server_thread.start()

    def watchdog_loop():
        if watchdog_usec <= 0:
            return

        watchdog_pid = os.getenv("WATCHDOG_PID")
        if watchdog_pid and watchdog_pid.isdigit():
            if int(watchdog_pid) != os.getpid():
                return

        # Send heartbeats at half the configured watchdog interval.
        interval = max(watchdog_usec / 1_000_000 / 2, 0.5)

        while not watchdog_stop.wait(interval):
            # Withhold heartbeats if the HTTP server thread has stopped.
            if not server_thread.is_alive():
                logging.error("HTTP server stopped; withholding heartbeat")
                return

            if not systemd_notify("WATCHDOG=1"):
                logging.warning("Could not send watchdog heartbeat")

    watchdog_thread = threading.Thread(
        target=watchdog_loop,
        name="systemd-watchdog",
        daemon=True,
    )
    watchdog_thread.start()

    logging.info(
        "Starting instance=%s environment=%s host=%s port=%d",
        instance_name,
        app_env,
        args.host,
        args.port,
    )

    # Type=notify services must send READY=1 after startup succeeds.
    if systemd_notify(
        f"READY=1\nSTATUS=Listening on {args.host}:{args.port}"
    ):
        logging.info("Sent READY=1 to systemd")
    else:
        logging.info("Running without systemd readiness notification")

    try:
        stop_requested.wait()
    finally:
        watchdog_stop.set()
        systemd_notify("STOPPING=1\nSTATUS=Graceful shutdown")

        logging.info("Stopping HTTP server")
        server.shutdown()
        server_thread.join()
        server.server_close()

        logging.info("HTTP server stopped cleanly")


if __name__ == "__main__":
    main()
```

### Understand the Python code

Focus on five important concepts rather than memorising the whole application.

A. Command-line arguments

Python

Run

```
parser.add_argument("--port", type=int, default=8088)
```

When systemd starts Python with `--port 8088`, the value is available through `args.port`. The application uses `argparse` to parse the arguments.

B. Environment variables

Python

Run

```
app_env = os.getenv("APP_ENV", "development")
```

If systemd supplies `APP_ENV=production`, the application uses that value. Otherwise, it falls back to `development`.

C. Readiness notification

Python

Run

```
systemd_notify("READY=1")
```

This is a message to systemd, not a command-line argument. With `Type=notify`, systemd can wait for the application to send this message before treating startup as complete.

D. Watchdog heartbeat

Python

Run

```
systemd_notify("WATCHDOG=1")
```

This tells systemd that the watchdog heartbeat is being sent. The service must continue sending heartbeats within the configured timeout or systemd considers it failed.

![](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

E. Graceful shutdown

Python

Run

```
signal.signal(signal.SIGTERM, handle_signal)
```

When systemd stops the service, Python receives `SIGTERM`. Our handler requests a shutdown, the server stops accepting new work, and the application exits instead of relying on an abrupt kill.

The watchdog in this tutorial demonstrates the protocol; its heartbeat checks that the HTTP server thread remains alive. A production application should monitor meaningful progress and dependencies as well, since a live thread does not necessarily mean every request is healthy.

## 4. Create the environment file

This file contains application-specific configuration that you can change without editing the Python source code.

Create `/etc/demo-python/demo-python.env`:

Bash

```
INSTANCE_NAME=demo-python-01
APP_MESSAGE="Hello from the systemd environment"
```

These variables are read by systemd and passed to the Python process as environment variables. The file uses systemd's environment-file format; it is not a shell script, so you do not write `export APP_MESSAGE=...`.

For example, the Python application reads:

Python

Run

```
instance_name = os.getenv("INSTANCE_NAME", "local-instance")
app_message = os.getenv("APP_MESSAGE", "Hello from Python!")
```

If you change `APP_MESSAGE` in the file, restart the service to apply the new value.

## 5. Create the systemd service file

Now we tell Linux how to run the application.

Create a file named:

`/etc/systemd/system/demo-python.service`

Add the following configuration.

INI

```
[Unit]
Description=Demo Python HTTP Service
After=network.target
StartLimitIntervalSec=60s
StartLimitBurst=5

[Service]
# Wait until Python announces that startup is complete.
Type=notify
NotifyAccess=main

# Run as a dedicated, unprivileged account.
User=pyapp
Group=pyapp

# Directory from which the Python process runs.
WorkingDirectory=/opt/demo-python

# Application environment and defaults.
Environment=APP_ENV=production
Environment=APP_HOST=127.0.0.1
Environment=APP_PORT=8088
Environment=LOG_LEVEL=INFO

# Additional application configuration.
EnvironmentFile=-/etc/demo-python/demo-python.env

# systemd-managed directories.
StateDirectory=demo-python
StateDirectoryMode=0750
RuntimeDirectory=demo-python
RuntimeDirectoryMode=0750

# Validate the application file before starting.
ExecStartPre=/usr/bin/test -r /opt/demo-python/app.py

# Start Python and pass application configuration as arguments.
ExecStart=/usr/bin/python3 /opt/demo-python/app.py --host ${APP_HOST} --port ${APP_PORT} --log-level ${LOG_LEVEL}

# Process supervision.
Restart=on-failure
RestartSec=3s
TimeoutStartSec=30s
TimeoutStopSec=15s
KillSignal=SIGTERM
WatchdogSec=30s

# Logging and filesystem permissions.
UMask=0027
StandardOutput=journal
StandardError=journal
SyslogIdentifier=demo-python

# Basic security hardening.
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true

[Install]
WantedBy=multi-user.target
```

This is our central configuration file. Let's understand every directive used here.

## 6. Understand every parameter in the service file

### A. `[Unit]` — dependencies and startup rules

| Directive                   | Meaning                                                                                     |
| --------------------------- | ------------------------------------------------------------------------------------------- |
| `Description=`              | Human-readable service description.                                                         |
| `After=network.target`      | Orders startup after `network.target`; it does not guarantee external network connectivity. |
| `StartLimitIntervalSec=60s` | Defines the interval used for limiting startup attempts.                                    |
| `StartLimitBurst=5`         | Allows at most five starts within that interval before the start limit is enforced.         |

`After=` is an ordering relationship, not a dependency by itself. `Wants=` and `Requires=` express different dependency relationships.

![](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

### B. `[Service]` — how the application runs

| Directive           | Meaning                                                             |
| ------------------- | ------------------------------------------------------------------- |
| `Type=notify`       | Waits for a readiness notification from the application.            |
| `NotifyAccess=main` | Allows the service's main process to send notifications to systemd. |
| `User=pyapp`        | Runs the service under the `pyapp` Linux user.                      |
| `Group=pyapp`       | Sets the service's primary group.                                   |
| `WorkingDirectory=` | Sets the process's current working directory.                       |
| `Environment=`      | Defines environment variables.                                      |
| `EnvironmentFile=`  | Loads additional environment variables from a file.                 |
| `ExecStartPre=`     | Runs a check before the main application starts.                    |
| `ExecStart=`        | Defines the executable and arguments used to start the application. |

One subtle but important point: `ExecStart` is not normally executed by a shell. Do not assume shell features such as pipes, `&&`, or `>` redirection will work there. systemd performs its own command-line parsing and environment expansion.

![](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1

### C. Process lifecycle

| Directive             | Meaning                                                                                                         |
| --------------------- | --------------------------------------------------------------------------------------------------------------- |
| `Restart=on-failure`  | Restarts the service following an unsuccessful exit or qualifying failure.                                      |
| `RestartSec=3s`       | Waits three seconds before an automatic restart.                                                                |
| `TimeoutStartSec=30s` | Limits how long systemd waits for startup to complete; with `Type=notify`, this includes waiting for readiness. |
| `TimeoutStopSec=15s`  | Gives the application time to stop before systemd forcefully terminates remaining processes.                    |
| `KillSignal=SIGTERM`  | Specifies the initial signal used to stop the service.                                                          |
| `WatchdogSec=30s`     | Requires watchdog notifications at regular intervals after startup.                                             |

The interaction between these directives is what makes systemd more than a command launcher. It supervises the service's lifecycle.

![](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

For example, if the Python process crashes:

1. systemd detects that the process has failed.

2. It waits three seconds.

3. It attempts to restart the service.

4. Repeated failures eventually encounter the configured start limit.

If you explicitly run `systemctl stop demo-python`, systemd does not normally restart the service just because it has stopped. `Restart=on-failure` is for failures, not an intentional administrative stop.

### D. Directories and logging

| Directive                      | Meaning                                                       |
| ------------------------------ | ------------------------------------------------------------- |
| `StateDirectory=demo-python`   | Creates persistent storage at `/var/lib/demo-python`.         |
| `RuntimeDirectory=demo-python` | Creates a temporary runtime directory at `/run/demo-python`.  |
| `StateDirectoryMode=0750`      | Sets the requested permissions for the state directory.       |
| `RuntimeDirectoryMode=0750`    | Sets the requested permissions for the runtime directory.     |
| `UMask=0027`                   | Restricts permissions on newly created files and directories. |
| `StandardOutput=journal`       | Sends standard output to the system journal.                  |
| `StandardError=journal`        | Sends standard error to the system journal.                   |
| `SyslogIdentifier=demo-python` | Sets the identifier used for log messages.                    |

systemd also makes the paths of the managed directories available through the `STATE_DIRECTORY` and `RUNTIME_DIRECTORY` environment variables. The Python program uses `STATE_DIRECTORY` to save `last-start.json`.

![](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

### E. Security settings

| Directive              | Meaning                                                                                                                       |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `NoNewPrivileges=true` | Prevents the process and its descendants from gaining additional privileges through mechanisms such as set-user-ID execution. |
| `PrivateTmp=true`      | Gives the service private temporary directories rather than sharing the host's normal `/tmp` and `/var/tmp`.                  |
| `ProtectSystem=strict` | Makes the filesystem hierarchy read-only for the service, except for permitted writable locations.                            |
| `ProtectHome=true`     | Restricts access to the usual home-directory locations.                                                                       |

These settings work alongside the dedicated service account and the directories systemd manages. They reduce the damage a compromised application could cause. They do not replace application-level security controls.

## 7. What actually gets passed from systemd to Python?

This is the key concept behind your question.

1. Command-line arguments

systemd runs:

Bash

```
/usr/bin/python3 /opt/demo-python/app.py \
  --host 127.0.0.1 --port 8088 --log-level INFO
```

Python parses these with `argparse`. The resulting values are `args.host`, `args.port` and `args.log_level`.

2. Environment variables

`Environment=` and `EnvironmentFile=` populate the process environment.

Python reads them with:

Python

Run

```
os.getenv("APP_ENV")
os.getenv("APP_MESSAGE")
os.getenv("INSTANCE_NAME")
```

3. systemd-generated environment variables

Because our service declares managed directories, readiness notifications and a watchdog, Python can read:

Python

Run

```
os.getenv("STATE_DIRECTORY")
os.getenv("RUNTIME_DIRECTORY")
os.getenv("INVOCATION_ID")
os.getenv("NOTIFY_SOCKET")
os.getenv("WATCHDOG_USEC")
```

Some of these are conditional on the service configuration and systemd version. Our code handles missing values.

4. Settings that are not ordinary parameters

`User=`, `Group=`, `Restart=`, `TimeoutStopSec=`, `ProtectSystem=` and `After=` are interpreted by systemd. They affect the process environment, lifecycle or execution context rather than appearing as application arguments.

The application demonstrates the first three mechanisms. systemd enforces the fourth.

There is no finite list of "all parameters passed by systemd" because it has many directives and supports additional mechanisms, including file descriptors and credentials. The example implements the commonly useful configuration, readiness, watchdog, directories, and signal-handling mechanisms.

## 8. Install and run the application

The following commands assume an Ubuntu or Debian-style Linux installation with systemd and Python 3.

### Step 1: Create a dedicated service user and directories

Bash

```
sudo useradd --system --user-group \
  --home-dir /opt/demo-python \
  --shell /usr/sbin/nologin pyapp

sudo install -d -o root -g root -m 0755 /opt/demo-python

sudo install -d -o root -g root -m 0750 /etc/demo-python
```

The `pyapp` user has no normal login shell. The application code remains owned by root so the service cannot modify its own executable code.

### Step 2: Save the files

Save the Python code as:

`/opt/demo-python/app.py`

Save the environment file as:

`/etc/demo-python/demo-python.env`

Then ensure the application code has the appropriate permissions:

Bash

```
sudo chown root:root /opt/demo-python/app.py
sudo chmod 0644 /opt/demo-python/app.py

sudo chown root:root /etc/demo-python/demo-python.env
sudo chmod 0640 /etc/demo-python/demo-python.env
```

Save the service definition as:

`/etc/systemd/system/demo-python.service`

### Step 3: Load and start the service

Tell systemd to read the unit file, enable the application at boot, and start it now:

Bash

```
sudo systemd-analyze verify /etc/systemd/system/demo-python.service

sudo systemctl daemon-reload

sudo systemctl enable --now demo-python.service
```

Here is what each command does:

* `systemd-analyze verify` checks the unit configuration for errors.

* `systemctl daemon-reload` makes systemd reload unit definitions.

* `systemctl enable` configures the service to start at boot.

* `systemctl --now` also starts it immediately.

## 9. Test the running Python application

Check the status:

Bash

```
systemctl status demo-python
```

Test the health endpoint:

Bash

```
curl http://127.0.0.1:8088/health
```

Expected response:

JSON

```
{
  "status": "ok",
  "instance": "demo-python-01"
}
```

Test the application's message:

Bash

```
curl http://127.0.0.1:8088/
```

Expected response:

JSON

```
{
  "message": "Hello from the systemd environment",
  "instance": "demo-python-01",
  "environment": "production"
}
```

Finally, inspect the configuration passed to Python:

Bash

```
curl http://127.0.0.1:8088/config
```

The response includes values such as the application's port, `STATE_DIRECTORY`, `RUNTIME_DIRECTORY`, the notification socket's availability, the watchdog interval, and the invocation ID when available.

This is a useful way to see how the service definition affects a real process. The `/config` endpoint is for this local demonstration; remove or restrict it in production.

## 10. Learn to operate and troubleshoot the service

These are the commands you should become comfortable with as a platform or DevOps engineer.

| Task                             | Command                                              |
| -------------------------------- | ---------------------------------------------------- |
| Start                            | `sudo systemctl start demo-python`                   |
| Stop                             | `sudo systemctl stop demo-python`                    |
| Restart                          | `sudo systemctl restart demo-python`                 |
| Check current status             | `systemctl status demo-python`                       |
| Read recent logs                 | `journalctl -u demo-python -n 100`                   |
| Follow live logs                 | `journalctl -u demo-python -f`                       |
| See restart count and process ID | `systemctl show demo-python -p MainPID -p NRestarts` |
| Inspect service dependencies     | `systemctl list-dependencies demo-python`            |
| Check security exposure          | `systemd-analyze security demo-python`               |

Remember the distinction between reloads:

* After editing a `.service` file, run `systemctl daemon-reload`, then restart the service if you want the new settings applied.

* After changing the environment file, restart the service to make it read the new environment.

* After changing Python code, restart the service so the new process loads the updated code.

The application does not automatically reload its process environment simply because you edit a file on disk.

## 11. The most important concepts to remember

Starting

`ExecStart` runs the application. `Type=notify` waits for `READY=1`, confirming that the app has completed its startup.

Recovery

`Restart=on-failure` and `RestartSec=3s` govern automatic recovery following failures.

Monitoring

The watchdog checks for regular heartbeats. Missing heartbeats cause systemd to treat the service as failed and, under our restart policy, attempt recovery.

Security

A dedicated Linux user, managed directories, filesystem protections and restricted privileges establish the process's execution context.

Observability

Application logs go to the journal, while `systemctl status` exposes the service's state and exit information.

My recommendation: work through this service in stages. First, understand `ExecStart`, `User`, `WorkingDirectory` and environment variables. Next, learn restart policies and journald. Finally, focus on `Type=notify`, watchdogs, managed directories and security hardening. Those are the concepts that turn a basic process into a well-managed Linux service.
