#!/bin/bash
##################################
###       LHR DATA STACK       ###
###    FIRST-TIME TELEGRAF     ###
###       CONFIGURATION        ###
###     DOCKER DEPLOYMENT      ###
###   Author: Max Wiesenfeld   ###
##################################

# Step 1: Installing curl to the container
echo "Installing curl..."
apt update && apt install curl -y

# Step 2: Creating service account on grafana container and retrieving its ID
# (with some black magic fuckery--it has been several months and I have no clue what I did with
# the "2>&1" or regex to make this work. Sorry if you have to rework this, but it works as is.)
echo "Creating and Retrieving Service Account ID..."
service_account_id=$(curl -X POST http://admin:admin@grafana:3000/api/serviceaccounts \
                      -H 'Content-Type: application/json' \
                      -d '{"name":"telegraf","role":"Admin","isDisabled":false}' 2>&1 \
                      | grep -oPa -m 1 '"id":\K[\d]+')

# Step 3: Creating and retrieving plaintext API Token (same sorcery as aforementioned)
echo "Creating and Retrieving API Token..."
token=$(curl -X POST http://admin:admin@grafana:3000/api/serviceaccounts/"${service_account_id}"/tokens \
        -H 'Content-Type: application/json' \
        -d '{"name":"telegraf","role":"Admin"}' 2>&1 \
        | grep -oPa -m 1 '"key":"\K[\w\d]+')

# Step 4: Creating telegraf.conf file and outputting to bind mounted permanent storage
echo "Creating telegraf.conf file..."

# Remove old conf file if there was one
if [[ -f /LHR/telegraf_conf_gen/telegraf.conf ]]
then
  rm -f /LHR/telegraf_conf_gen/telegraf.conf
fi

echo -n "[agent]
  interval = \"10ms\"
  flush_interval = \"10ms\"
  omit_hostname = true

[[outputs.file]]
  files = [\"stdout\", \"/tmp/metrics.out\"]

[[outputs.postgresql]]
  connection = \"dbname=telemetry host=db user=electric password=2fast2quick\"

[[outputs.websocket]]
  url = \"ws://grafana:3000/api/live/push/telemetry\"
  data_format = \"influx\"
  [outputs.websocket.headers]
    Authorization = \"Bearer " >> /LHR/telegraf_conf_gen/telegraf.conf

printf "%s" "$token" >> /LHR/telegraf_conf_gen/telegraf.conf

echo -e '"\n
[[inputs.mqtt_consumer]]
  servers = ["tcp://mosquitto:1883"]
  topics = ["#"]
  connection_timeout = "30s"
  persistent_session = true
  client_id = "telegraf"
  data_format = "json"
  json_time_key = "creation_time"
  json_time_format = "unix_us"

[[processors.converter]]
  [processors.converter.tags]
    measurement = ["topic"]
' >> /LHR/telegraf_conf_gen/telegraf.conf

echo "Processes Finished."
echo "Service Account ID: $service_account_id"
echo "API Token: $token"

cp /LHR/telegraf_conf_gen/telegraf.conf /etc/telegraf/telegraf.conf

# Step 5: Run telegraf command to resume normal startup
telegraf