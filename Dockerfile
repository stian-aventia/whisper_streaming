##
## This code and all components (c) Copyright 2006 - 2025, Wowza Media Systems, LLC. All rights reserved.
## This code is licensed pursuant to the Wowza Public License version 1.0, available at www.wowza.com/legal.
##
FROM python:3.12-slim

# Install only the project requirements (sentence tokenizer deps already pruned)
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Install these for GPU, increases image size by ~5GB
# RUN pip install torch 
# RUN pip install "triton>=2.0.0; platform_machine=='x86_64' and (sys_platform=='linux' or sys_platform=='linux2')"
# RUN wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
# RUN dpkg -i cuda-keyring_1.1-1_all.deb
# RUN apt update && apt install cudnn9-cuda-12 -y
#

RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

## Dependencies installed via requirements.txt

# create a working directory
RUN mkdir /app
WORKDIR /app

COPY *.py .
COPY entrypoint.sh .

# Normalize potential Windows line endings and ensure executable bit for entrypoint
RUN sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh

EXPOSE 3000

CMD ["/app/entrypoint.sh"]
