//Encodes information into a .json file and publishes the data to mqtt
function encodeValues() {
    console.log("Encoder Triggered")

    //TODO Pull all relevant elements if necessary?

    //Create json object reflecting current state to be published
    const jsonData = {
        "timerRunning": startButton.getAttribute("isRunning"),
        "stopStatus": !stopButton.hasAttribute("disabled"),
        "unixTimerStarted": Date.now()
    }

    //Publish changes to MQTT state topic
    let message = new Paho.MQTT.Message(JSON.stringify(jsonData))
    message.destinationName = "page_sync"
    client.send(message)
}