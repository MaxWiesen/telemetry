//Encodes information into a .json file and publishes the data to mqtt
function encodeValues(runStatus, timerTime, turnStatus, accelStatus) {
    console.log("Encoder Triggered") //TODO remove, debug

    //Create json object reflecting current state to be published
    const jsonData = {
        "timerRunning": runStatus,
        "timerEventTime": (timerTime != null) ? timerTime : 0, //TODO consider revising 0 later
        "timerInternalTime": watch.getTime(),
        "turnRunning" : turnStatus,
        "accelRunning" : accelStatus
    }

    //Publish changes to MQTT state topic
    let message = new Paho.MQTT.Message(JSON.stringify(jsonData))
    message.destinationName = "event_sync"
    client.send(message)
}