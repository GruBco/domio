ARG BUILD_FROM=ghcr.io/home-assistant/base-debian:bookworm
FROM ${BUILD_FROM}

ARG BUILD_VERSION=0.1.1
ARG BUILD_ARCH
LABEL io.hass.name="Domio" \
      io.hass.description="Cybro PLC connectivity for Home Assistant" \
      io.hass.version="${BUILD_VERSION}" \
      io.hass.type="addon" \
      io.hass.arch="${BUILD_ARCH}"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:${PATH}"

COPY requirements-addon.txt /tmp/requirements-addon.txt
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv python3-dev build-essential \
    && python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements-addon.txt \
    && apt-get purge -y --auto-remove python3-dev build-essential \
    && rm -rf /var/lib/apt/lists/* /tmp/requirements-addon.txt

WORKDIR /opt/domio
COPY CybroEdgeToolkit/app/lib ./lib
COPY CybroEdgeToolkit/app/scgi_server ./scgi_server
COPY CybroEdgeToolkit/app/mqtt_client ./mqtt_client
COPY CybroEdgeToolkit/app/tls ./tls
COPY CybroEdgeToolkit/app/config.ini /opt/domio-defaults/config.ini
COPY rootfs /

RUN ln -s /config/config.ini /opt/domio/config.ini \
    && ln -s /data/alc /opt/domio/alc \
    && ln -s /data/log /opt/domio/log \
    && find /etc/s6-overlay/s6-rc.d /usr/local/bin/domio-init -type f -exec sed -i 's/\r$//' {} + \
    && chmod 755 /usr/local/bin/domio-init \
       /etc/s6-overlay/s6-rc.d/domio-scgi/run \
       /etc/s6-overlay/s6-rc.d/domio-mqtt/run \
    && python -m compileall -q /opt/domio \
    && python -c "from scgi_server import main; from mqtt_client import main"

ENTRYPOINT ["/init"]
