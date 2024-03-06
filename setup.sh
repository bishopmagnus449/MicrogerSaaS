#!/bin/bash

export DEBIAN_FRONTEND=noninteractive
export GNUTLS_CPUID_OVERRIDE=0x1

if ! command -v docker compose >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y ca-certificates curl git
  sudo install -m 0755 -d /etc/apt/keyrings
  sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  sudo chmod a+r /etc/apt/keyrings/docker.asc

  echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
  sudo apt-get update

  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

if [ -d "MicrogerSaaS" ]; then
  cd MicrogerSaaS || exit 1
else
  git clone https://github.com/realSamy/MicrogerSaaS && cd MicrogerSaaS || exit 1
fi

clear

sudo docker compose up