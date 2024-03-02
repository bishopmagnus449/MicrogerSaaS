#!/bin/bash
public_ip=$(curl -s https://api.ipify.org)

echo "http://$public_ip:8000/" > /var/log/deployment.log

length=21-${#public_ip}
spaces=""
for ((i=0; i<length; i++)); do
  spaces+=" "
done

local_spaces=""
for ((i=0; i<13; i++)); do
  local_spaces+=" "
done

printf "\u250C"
for ((i=0; i<44; i++)); do
  printf "\u2500"
done

printf "\u2510\n"
printf "\u2502 \e[0;36mAccess SaaS panel using following address:\e[0m \u2502\n"
printf "\u2502 Local: \e[0;32mhttp://localhost:8000/\e[0m %s\u2502\n" "$local_spaces"
printf "\u2502 Server: \e[0;32mhttp://%s:8000/\e[0m %s\u2502\n" "$public_ip" "$spaces"

printf "\u2514"
for ((i=0; i<44; i++)); do
  printf "\u2500"
done

printf "\u2518\n"
