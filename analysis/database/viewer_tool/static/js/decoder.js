//Decodes information from .json file and updates the client's instances
function decodeValues(jsonObj) {
    console.log("Decoder Triggered\nPayload: " + jsonObj) //TODO remove, DEBUG only

    //Decode string to actual JSON object
    jsonObj = JSON.parse(jsonObj)

    //Update page by element
    updateStartButton()
    updateStopButton()
    updateTurn()
    updateAccel()

    function updateStartButton() {
        //If timer is running but this object is not, update this object
        if (jsonObj.timerRunning && (startButton.getAttribute("isRunning") === "false")) {
            //Set local attributes
            startButton.setAttribute("isRunning", true)
            watch.startAt(jsonObj.timerEventTime);
            //TODO database push?
        }
    }

    function updateStopButton() {
        //If timer is not running but this object is, update object
        if (!jsonObj.timerRunning && (startButton.getAttribute("isRunning") === "true")) {
            //Update states to match by stopping
            startButton.setAttribute("isRunning", false)
            watch.stopAt(jsonObj.timerInternalTime)
            //TODO database push?
        }
    }

    function updateTurn(qualifiedName, value) {
        //If turn is running but this object's is not, update local
        if (jsonObj.turnRunning && !watch.isTurning()) {
            //Start the turn
            watch.turnAt(jsonObj.timerInternalTime)

        //If turn is not running but this object's is, update local
        } else if (!jsonObj.turnRunning && watch.isTurning()) {
            //Stop the turn
            watch.turnAt(jsonObj.timerInternalTime)
        } //Else states match, do nothing

        //If the timer is running, enable the button, otherwise disable
        // if (jsonObj.timerRunning) {
        //     turnButton.setAttribute("disabled", false)
        // } else {
        //     turnButton.setAttribute("disabled", true)
        // }
    }

    function updateAccel() {
        //If accel is running but this object's is not, update local
        if (jsonObj.accelRunning && !watch.isAccel()) {
            //Start the accel
            watch.accelAt(jsonObj.timerInternalTime)

        //If accel is not running but this object's is, update local
        } else if (!jsonObj.accelRunning && watch.isAccel()) {
            //Stop the accel
            watch.accelAt(jsonObj.timerInternalTime)
        } //Else states match, do nothing

        //If the timer is running, enable the button, otherwise disable
        // if (jsonObj.timerRunning) {
        //     accelButton.setAttribute("disabled", false)
        // } else {
        //     accelButton.setAttribute("disabled", true)
        // }
    }
}