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
        console.log("Cache: " + JSON.stringify(config_image)) //TODO debug only, remove
    } catch (error) {
        //Decoding Failed, Not Properly Formatted
        console.log("Attempt at stringify FAILED: " + JSON.stringify(jsonObj)) //TODO debug only, remove
    }

    //Update page by element
    updateStartButton()
    updateStopButton()
    updateTurn()
    updateAccel()

    //Check for end event flag
    if (jsonObj.endFlag) {
        console.log("Flag detected: " + jsonObj.endFlag)
        //client.end() TODO re-vist, is it needed?
        //Redirect
        //Send request to reset config_image AND server side variables
        fetch('/reset_config_image', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ action: 'redirect' })
        })
        .then(response => {
            if (response.redirected) {
                window.location.href = response.url
                console.log("config_image reset, disconnected");
            } else {
                console.error("Failed to reset config_image", response.statusText);
            }
        })
        .catch(error => {
            console.error("Error during fetch: ", error);
        });
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
        } else if (jsonObj.timerRunning) { //States match and timer running
            //TODO state catch? reverse
        } else { //Timer not running
            if (jsonObj.timerInternalTime !== watch.getTime()) {
                watch.stopAt(jsonObj.timerInternalTime)
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

function loadPrevTables() {
    //NOTE only for use on initial creation
    if(config_image && config_image.tables) {
        //Load Turns
        for (let i = 0; i < config_image.tables.turnStarts.length; i++) {
            watch.loadCustomTurn(config_image.tables.turnStarts[i], config_image.tables.turnStops[i])
        }
        //Load Accels
        for (let i = 0; i < config_image.tables.accelStarts.length; i++) {
            watch.loadCustomAccel(config_image.tables.accelStarts[i], config_image.tables.accelStops[i])
        }
        console.log("DONE Loading Prev Tables") //TODO remove, debug only
    }
}