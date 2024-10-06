#!/bin/zsh

echo "Welcome to the Telemetry Server CLI Devtool. Please pick from the following methods to start the server:"
echo -e "\t1) Start the server (ONLY)"
echo -e "\t2) Delete the existing images"
echo -e "\t3) Delete the existing images and telemetry_db volume"
echo -e "\t4) Delete the existing images and both volumes (INCLUDING GRAFANA DASHBOARDS!)"
echo -e "\tQ) Run Processor in background and start server"
echo -e "\tW) Delete the existing server and processors images"
echo

while :
do
    read -k 1 opt
    echo
    echo
    cd $(find . -name "ingest") || (echo "Failed to find ingest" && exit)
    id "postgres" > /dev/null 2>&1 && sudo pkill -u postgres
    case $opt in
        1)
            sudo docker compose down
            sudo docker compose up
            break
            ;;
        2)
            sudo docker compose down
            sudo docker rmi "$(sudo docker image ls | grep telemetry_backend | awk '{print $3}')"
            sudo docker compose up
            break
            ;;
        3)
            sudo docker compose down
            sudo docker rmi "$(sudo docker image ls | grep telemetry_backend | awk '{print $3}')"
            sudo docker volume rm telemetry_db && sudo docker volume create telemetry_db
            sudo docker compose up
            break
            ;;
        4)
            while :
            do
                echo "You are about to delete the Grafana dashboards saves on this computer. Are you sure you intend to delete this? [Y/n]"
                read -k 1 yn
                echo
                echo
                case $yn in
                    Y|y)
                        sudo docker compose down
                        sudo docker rmi "$(sudo docker image ls | grep telemetry_backend | awk '{print $3}')"
                        sudo docker volume rm telemetry_db && sudo docker volume create telemetry_db
                        sudo docker volume rm grafana_storage && sudo docker volume create grafana_storage
                        sudo docker compose up
                        break
                        ;;
                    N|n)
                        echo "Crisis Averted!"
                        break
                        ;;
                    *)
                        echo "Invalid input, please try again."
                        ;;
                esac
            done
            break
            ;;
        q|Q)
            sudo docker compose down
            sudo docker compose up -d
            cd ../processors || (echo "Failed to find processors" && exit)
            sudo docker compose down
            sudo docker compose up -d
            echo "Processor container ID: $(sudo docker container ls | grep telemetry_processors | awk '{print $1}')"
            cd ../ingest
            sudo docker compose logs -f
            break
            ;;
        w|W)
            sudo docker compose down
            sudo docker rmi "$(sudo docker image ls | grep telemetry_backend | awk '{print $3}')"
            sudo docker rmi "$(sudo docker image ls | grep telemetry_processors | awk '{print $3}')"
            sudo docker compose up -d
            cd ../processors || (echo "Failed to find processors" && exit)
            sudo docker compose down
            sudo docker compose up -d
            echo "Processor container ID: $(sudo docker container ls | grep telemetry_processors | awk '{print $1}')"
            cd ../ingest
            sudo docker compose logs -f
            break
            ;;
        *)
            echo "Invalid input, please try again."
            ;;
    esac
done