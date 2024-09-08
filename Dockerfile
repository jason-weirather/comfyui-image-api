FROM mambaorg/micromamba:1-jammy-cuda-12.6.0

# Set environment variables for NVIDIA
ENV NVIDIA_VISIBLE_DEVICES all
ENV NVIDIA_DRIVER_CAPABILITIES compute,utility

# Install Python 3.11 in the base environment globally for all users
RUN micromamba install -n base python=3.11 git -c conda-forge && \
    micromamba clean --all --yes

# Install PyTorch with CUDA using micromamba run (so we don’t need to activate the base environment manually)
RUN micromamba run -n base pip install \
    torch \
    torchvision \
    torchaudio --extra-index-url https://download.pytorch.org/whl/cu124

# Switch to root to perform privileged operations
USER root

# Create /opt/ComfyUI directory and give permissions
RUN mkdir -p /opt/ComfyUI && \
    chmod -R 777 /opt/ComfyUI
RUN mkdir -p /opt/comfy-cli && \
    chmod -R 777 /opt/comfy-cli

# Switch back to the default user for micromamba
USER mambauser


# Clone ComfyUI repo and install dependencies
RUN micromamba run -n base git clone https://github.com/comfyanonymous/ComfyUI.git /opt/ComfyUI && \
    micromamba run -n base pip install -r /opt/ComfyUI/requirements.txt

# Clone your fork of comfy-cli instead of installing from pip
RUN micromamba run -n base git clone --branch fixhangbug https://github.com/jason-weirather/comfy-cli.git /opt/comfy-cli

# Install comfy-cli
ENV COMFYUI_PATH=/opt/ComfyUI
RUN cd /opt/comfy-cli && micromamba run -n base pip install -e .

# Run for first time and disable tracking
RUN micromamba run -n base comfy \
        --workspace $COMFYUI_PATH \
        --skip-prompt \
        --no-enable-telemetry tracking disable
# && \
#    echo "Tracking disabled, running comfy env..." && \
#    micromamba run -n base comfy \
#        --workspace $COMFYUI_PATH \
#        --skip-prompt --no-enable-telemetry env

USER root
# Copy the entire repository into the container
ADD . /opt/comfyui-image-api
# Set permissions for the copied files
RUN chmod -R 777 /opt/comfyui-image-api

USER mambauser
RUN cd /opt/comfyui-image-api && micromamba run -n base pip install -e .

RUN mkdir -p /home/mambauser/.config/comfy-cli && \
    chmod -R 777 /home/mambauser

EXPOSE 8888
EXPOSE 8188
# Command to start comfy-api
CMD ["comfy-api", "--port","8888","--model-path","/opt/ComfyUI/models/diffusers"]
