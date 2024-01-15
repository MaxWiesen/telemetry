#!/bin/bash

compose_path=$(find . -name "docker-compose.yml")

while :
do
    read -n 1 -p $'Please choose an option from those below:\n\t1) Launch server without any reset.\n\t2) Launch server with compose down.\n\t3) Launch server with container + volume removal.\n\t4) Launch server with container + volume removal and python_image rewrite.\n' launch_option
    case $launch_option in
        1)
            break
            ;;
        2)
            sudo docker compose -f ${compose_path} down
            break
            ;;
        3)
            sudo docker compose -f ${compose_path} down && sudo docker volume rm grafana_storage && sudo docker volume rm telemetry_db && sudo docker volume create grafana_storage && sudo docker volume create telemetry_db
            break
            ;;
        4)
            sudo docker compose -f ${compose_path} down && sudo docker build -t telemetry_backend $(find . -type d -name 'ingest') && sudo docker volume rm grafana_storage && sudo docker volume rm telemetry_db && sudo docker volume create grafana_storage && sudo docker volume create telemetry_db
            break
            ;;
        *)
            echo -e "\nInvalid input, please try again.\n"
            ;;
    esac
done

sh -c ". $(find . -name 'activate') && python $(find . -name 'index.py' | grep 'viewer_tool') -s > /dev/null 2>&1 &"
sudo docker compose -f ${compose_path} up