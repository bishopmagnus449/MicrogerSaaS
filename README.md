# MicrogerSaaS


This project provides a SaaS (Software As A Service) to deploy one of my private projects [Microger].

## Prerequisites

- **Docker Engine** (version 25 or above) installed on your system.

You can install Docker Engine on Ubuntu by following the official instructions:
- https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository

Or simply run the following commands:
```bash
# Add Docker's official GPG key:
sudo apt-get update
sudo apt-get install ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
echo \
"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
$(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update

# Install the latest version:
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

## Running the Project

1. **Clone the repo:**

   ```bash
   git clone https://github.com/realSamy/MicrogerSaaS && cd MicrogerSaaS
   ```
2. **Let the docker do the rest:**
    ```bash
    sudo docker compose up -d
    ```