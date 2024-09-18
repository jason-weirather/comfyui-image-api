#!/bin/bash
# /opt/comfyui-image-api/start.sh

# Source the micromamba activation script
source /etc/profile.d/activate_mamba.sh

# Run comfy-api with the provided arguments
exec comfy-api "$@"
