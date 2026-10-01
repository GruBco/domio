# Domio

*Cybro PLC connectivity for Home Assistant*

> **Trademark and affiliation disclaimer:** Cybrotech and Cybro Edge Toolkit
> are names and trademarks of their respective owners. The author of this
> project does not own these names or trademarks. This is an independent,
> unofficial project and is not affiliated with, endorsed by or sponsored by
> their owners. References to these names identify the third-party toolkit
> and compatible products; they do not imply ownership or endorsement.

> **Codex collaboration disclosure:** This project was developed with the
> assistance of OpenAI Codex, including contributions to code and documentation.
> This assistance does not constitute review, certification or endorsement
> by OpenAI. Responsibility for reviewing and validating the project remains
> with its maintainers.

This add-on runs the Cybrotech toolkit's `scgi_server/start.py` and
`mqtt_client/start.py` as two processes supervised by s6-overlay. The original
sources and bundled `config.ini` remain unchanged. Web SCADA and the data
logger are not included.

The official Home Assistant Debian Bookworm base includes s6-overlay and uses
glibc: the toolkit explicitly loads `libc.so.6` for Linux timers. Python 3.11
is installed from Debian packages; the three application dependencies retain
the manufacturer's versions. WMI is only needed on Windows and is not installed.

## Local installation in Home Assistant

| Item | Name or path |
|---|---|
| Add-on display name | `Domio` |
| Add-on slug | `domio` |
| Local installation folder | `/addons/domio/` |
| Local configuration file | `/addon_configs/local_domio/config.ini` |
| Docker image | `domio:0.1.1` |
| s6 services | `domio-scgi`, `domio-mqtt` |

The project folder can be renamed to `domio`. Keep the bundled
`CybroEdgeToolkit` directory name: it identifies the manufacturer's toolkit
and is used by the Docker build.

1. Copy this folder to `/addons/domio` on the Home Assistant
   machine, including `CybroEdgeToolkit/app`, `rootfs`, `Dockerfile`,
   `requirements-addon.txt`, `.dockerignore`, `config.yaml`, `README.md` and
   `CHANGELOG.md`.
2. Reload the app/add-on store and install **Domio** from the
   local section. The image is built on the device.
3. Start the add-on and check the Log tab.

The declared architectures are amd64 and aarch64. Host networking allows UDP
broadcasts for PLC discovery; SCGI uses the port specified in `config.ini`
(4000 in the original file), directly on the host network. Privileged mode
and access to the Home Assistant API are not required.

The add-on slug is `domio`. Home Assistant treats this as a separate
add-on from earlier releases. Before switching, back up the previous add-on's
configuration and persistent data, stop it, and copy `config.ini` into
`/addon_configs/local_domio/config.ini`. Restore any required ALC files
and logs into the new add-on's private data directory. Keep the previous
installation until the new one has been verified; do not run both on the
same SCGI port. The new add-on cannot automatically access the old add-on's
private data. For standalone Docker, reuse the existing data volume and
configuration mount instead of creating empty replacements.

## Configuration and persistence

Configuration is available through Home Assistant's dedicated add-on folder.
For a locally installed add-on, the file is:

```text
/addon_configs/local_domio/config.ini
```

Use an editor, terminal or file share with access to `addon_configs`. The
displayed path may vary between tools; this is not Home Assistant Core's
`/config` folder. For repository installations, the repository identifier
replaces the `local` prefix.

1. Start the add-on once to create the file if it is missing.
2. Stop the add-on from its Home Assistant page.
3. Edit or replace `config.ini` in the folder above. Adjust the broker address,
   credentials and PLC parameters for your installation.
4. Start the add-on and check the logs. No image rebuild is needed.

The folder is mounted read/write as `/config` inside the container;
`/opt/domio/config.ini` is a symlink to `/config/config.ini`. An existing file
always takes precedence and is preserved across restarts and updates.

When reusing a data volume from version 0.1.0, if the new file is missing, the add-on copies
`/data/config.ini` to the new folder and keeps the old file as a backup. Once
the new file exists, the old copy is no longer read: edit only the new file.
If neither file exists, the manufacturer's original INI is used.

The standard paths `/opt/domio/alc` and `/opt/domio/log` point to the private
persistent directories `/data/alc` and `/data/log`. Custom paths in a future
INI will require adjustments.

Production configuration migration is deferred. The add-on's Configuration
tab does not expose toolkit parameters; edit them directly in the INI. The
original file uses MQTT at `localhost:1883`; the client cannot connect without
a broker reachable with those settings. Home Assistant entities and discovery
are not configured.

s6 starts SCGI before the MQTT client and restarts each process when it exits.
Startup ordering does not check port readiness: if SCGI or the broker is not
ready, the client may exit and be restarted. Shutdown signals reach Python
directly through `exec`. Both services use `python -u` for unbuffered output.
Standard output and error logs are visible in Home Assistant; file logging
follows the toolkit settings.

## Build and manual verification with Docker on Linux

```sh
docker build -t domio:0.1.1 .
mkdir -p domio-config
docker run -d --name domio --network host \
  -v domio-data:/data \
  --mount type=bind,src="$(pwd)/domio-config",dst=/config \
  domio:0.1.1
docker logs -f domio
docker exec domio s6-svstat /run/service/domio-scgi
docker exec domio s6-svstat /run/service/domio-mqtt
docker stop domio
```

The build checks compilation and imports for both modules, including their
Linux dependencies. Full integration testing requires an MQTT broker, a PLC
and the corresponding INI. To test service restarts in a test container:

```sh
docker exec domio s6-svc -k /run/service/domio-scgi
docker exec domio s6-svstat /run/service/domio-scgi
```

The PID must change; repeat for `domio-mqtt`. Also verify that
`domio-config/config.ini` remains unchanged after stopping, starting and
recreating the container with the same folder mounted. Do not start a second
instance on the same SCGI port.

Previously verified on Docker Desktop Linux/amd64: build, imports, service
startup, automatic restart of both services, shutdown with exit code 0 and
INI persistence. The aarch64 build and integration with Home Assistant and
the physical PLC still require on-site verification using the production
configuration.

References: [Home Assistant base images](https://github.com/home-assistant/docker-base),
[add-on configuration](https://developers.home-assistant.io/docs/apps/configuration/),
[s6-overlay services](https://github.com/just-containers/s6-overlay#writing-a-service-script).
