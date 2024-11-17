//Decodes information from .json file and updates the client's instances
function decodeValues(jsonObj) {
    console.log("Decoder Triggered\nPayload: " + jsonObj) //TODO remove, DEBUG only

    //Screen for undefined messages
    if (jsonObj === undefined) {
        console.log("Attempted to decode undefined")
        return
    }

    //Ensure Argument is Valid JSON object
    try {
        //Decode string to actual JSON object
        jsonObj = JSON.parse(jsonObj)
    } catch (error) {
        //Decoding Failed, Not Properly Formatted
        startButton.setAttribute("tempStore", jsonObj)
        console.log("Breakaway Error")
        console.log("Attempt at stringify: " + JSON.stringify(jsonObj))
    }

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
            watch.startAt(jsonObj.timerEventTime, jsonObj.timerInternalTime);
            console.log("waffle start at")
        } else { //Timer not running, ensure states match
            if (jsonObj.timerInternalTime !== watch.getTime()) {
                console.log("Resolving timer") //TODO remove, debug only
                watch.stopAt(jsonObj.timerInternalTime)
                console.log("waffle stop at")
            }
        }
    }

    function updateStopButton() {
        //If timer is not running but this object is, update object
        if (!jsonObj.timerRunning && (startButton.getAttribute("isRunning") === "true")) {
            //Update states to match by stopping
            startButton.setAttribute("isRunning", false)
            watch.stopAt(jsonObj.timerInternalTime)
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
    }
}