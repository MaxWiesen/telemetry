//Decodes information from .json file and updates the client's instances
function decodeValues(jsonObj) {
    console.log("Decoder Triggered w Obj: " + jsonObj) //TODO remove, DEBUG only

    //Decode string to actual JSON object
    jsonObj = JSON.parse(jsonObj)
    console.log("Converted to JSON")

    //Pull all relevant on-screen elements to be updated
    //let startButton = document.getElementById('startButton');
    //let stopButton = document.getElementById('stopButton');
    //let clock = document.getElementById('timer');
    //TODO more elements here later...

    //Update page by button elements
    updateStartButton()
    //updateStopButton()

    function updateStartButton() {
        console.log("Considering updating start.")
        console.log(jsonObj.timerRunning + " " + startButton.getAttribute("isRunning"))
        //If timer is running but this object is not, update this object
        if (jsonObj.timerRunning && (startButton.getAttribute("isRunning") === "false")) {
            console.log("Starting this instance's timer.")

            //Set local attributes
            startButton.setAttribute("isRunning", true)
            saveButton.setAttribute("disabled", true)
            watch.startAt(jsonObj.unixTimerStarted);

            //Alert database about changes
            let xhr = new XMLHttpRequest()
            xhr.open('POST', host_ip + ':5000/set_event_time', true)
            xhr.setRequestHeader("Content-Type", "application/json; charset=UTF-8")
            xhr.send(JSON.stringify({
                event_id: event_id,
                status: 1}))
        }
    }

    function updateStopButton() {
        //Check if states do NOT match
        if (jsonObj.stopStatus !== startButton.getAttribute("isRunning")) {
            //Update states to match by stopping TODO finish state check
            stopButton.click();
        }
    }
}

//TODO remove testing data
//Data to be invoked for testing
const jsonDataTest1 = {
    "startStatus": false,
    "stopStatus": false,
    "unixTime": 1729457473500
};

const jsonDataTest2 = {
    "startStatus": true,
    "stopStatus": false,
    "unixTime": 1729457473500
}

const jsonDataTest3 = {
    "startStatus": true,
    "stopStatus": true,
    "unixTime": 1729457473500
}
