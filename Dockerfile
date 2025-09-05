FROM python:3.12-slim

# OS-level dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget ca-certificates \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# create a working directory
RUN mkdir /app
WORKDIR /app

RUN pip install "triton>=2.0.0; platform_machine=='x86_64' and (sys_platform=='linux' or sys_platform=='linux2')"
RUN wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
RUN dpkg -i cuda-keyring_1.1-1_all.deb
RUN apt update && \
    apt-get install -y --no-install-recommends \
    cuda-cudart-12-6 \
    libcublas-12-6 \
    libnccl2 \
    libcurand-12-6 \
    libcusparse-12-6 \
    libcufft-12-6 \
    libcudnn9-cuda-12 \
    libsndfile1 && \
    rm -rf /var/lib/apt/lists/*


# Installer prosjektavhengigheter via pyproject.toml
COPY pyproject.toml /app/pyproject.toml
RUN pip install --no-cache-dir .

COPY *.py .
COPY entrypoint.sh .

# Normalize potential Windows line endings and ensure executable bit for entrypoint
RUN sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]
