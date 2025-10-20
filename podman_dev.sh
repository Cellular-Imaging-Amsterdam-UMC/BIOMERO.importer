#!/bin/bash

# Stop and remove the container if it exists
podman stop biomero-importer >/dev/null 2>&1 || true
podman rm biomero-importer >/dev/null 2>&1 || true

echo "Starting biomero-importer container..."
# Run the container with OMERO environment variables and network settings
podman run -d --rm --name biomero-importer \
    --privileged \
    --device /dev/fuse \
    --security-opt label=disable \
    -e OMERO_HOST=omeroserver \
    -e OMERO_USER=root \
    -e OMERO_PASSWORD=omero \
    -e OMERO_PORT=4064 \
    --network omero \
    --volume /mnt/datadisk/omero:/OMERO \
    --volume /mnt/L-Drive/basic/divg:/data \
    --volume /opt/omero/logs/biomero-importer:/auto-importer/logs:Z \
    --volume /opt/omero/config:/auto-importer/config \
    --volume /opt/omero/BIOMERO.importer/biomero_importer:/auto-importer/biomero_importer \
    --volume /opt/omero/BIOMERO.importer/tests:/auto-importer/tests \
    --volume /opt/omero/BIOMERO.importer/db:/auto-importer/db \
    --userns=keep-id:uid=1000,gid=1000 \
    localhost/biomero-importer:local  