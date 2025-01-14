//Decodes information from .json file and updates the client's instances
function decodeValues(jsonObj) {
    console.log("Decoder Triggered\nPayload: " + jsonObj) //TODO remove, DEBUG only

    //Screen for undefined messages
    if (jsonObj === undefined) {
        console.log("Attempted to decode undefined")
        //Use encoder to populate the config image
        encodeValues(false, true, true, false, false, false)
        return
    }

    //Ensure Argument is Valid JSON object
    try {
        //Decode string to actual JSON object
        jsonObj = JSON.parse(jsonObj)
        //Cache the incoming data
        config_image = jsonObj
        console.log("Here's the cache: " + JSON.stringify(config_image)) //TODO debug only, remove
    } catch (error) {
        //Decoding Failed, Not Properly Formatted
        console.log("Attempt at stringify FAILED: " + JSON.stringify(jsonObj)) //TODO debug only, remove
    }

    //Update page by element
    updateStartButton()
    updateStopButton()
    updateTurn()
    updateAccel()

    //Check flags
    if (jsonObj.flag !== undefined) {
        client.end()
        //End flag
        if (jsonObj.flag === "END") {
            console.log("ENDING EVENT METHOD STUB")
            fetch('/', {
                method: 'GET',
                headers: {
                    'Content-Type': 'TODO'
                }
            })
            //client.end()
        }
    }

    function updateStartButton() {
        //If timer is running but this object is not, update this object
        if (jsonObj.timerRunning && (startButton.getAttribute("isRunning") === "false")) {
            //Set local attributes
            startButton.disabled = true
            stopButton.disabled = false
            endButton.disabled = true
            accelButton.disabled = false
            turnButton.disabled = false
            startButton.setAttribute("isRunning", true)
            watch.startAt(jsonObj.timerEventTime, jsonObj.timerInternalTime);
            console.log("waffle start at") //TODO remove, debug only
        } else if (jsonObj.timerRunning) { //States match and timer running
            //TODO state catch? reverse
        } else { //Timer not running
            if (jsonObj.timerInternalTime !== watch.getTime()) {
                console.log("Resolving timer") //TODO remove, debug only
                watch.stopAt(jsonObj.timerInternalTime)
                console.log("waffle stop at")  //TODO remove, debug only
            }
        }
    }

    function updateStopButton() {
        //If timer is not running but this object is, update object
        if (!jsonObj.timerRunning && (startButton.getAttribute("isRunning") === "true")) {
            //Update states to match by stopping
            startButton.disabled = false
            stopButton.disabled = true
            endButton.disabled = false
            accelButton.disabled = true
            turnButton.disabled = true
            startButton.setAttribute("isRunning", false)
            watch.stopAt(jsonObj.timerInternalTime)
        }
    }

    function updateTurn() {
        //If turn is running but this object's is not, update local
        if (jsonObj.turnRunning && !watch.isTurning()) {
            //Start the turn
            watch.turnAt(jsonObj.turnStamp)
        //If turn is not running but this object's is, update local
        } else if (!jsonObj.turnRunning && watch.isTurning()) {
            //Stop the turn
            watch.turnAt(jsonObj.turnStamp)
        } //Else states match, do nothing
    }

    function updateAccel() {
        //If accel is running but this object's is not, update local
        if (jsonObj.accelRunning && !watch.isAccel()) {
            //Start the accel
            watch.accelAt(jsonObj.accelStamp)

        //If accel is not running but this object's is, update local
        } else if (!jsonObj.accelRunning && watch.isAccel()) {
            //Stop the accel
            watch.accelAt(jsonObj.accelStamp)
        } //Else states match, do nothing
    }
}