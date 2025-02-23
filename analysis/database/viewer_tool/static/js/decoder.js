//Decodes information from .json file and updates the client's instances
lap_times = []

function decodeValues(jsonObj) {
    console.log("Decoder Triggered.\nPayload: " + jsonObj) //TODO remove, DEBUG only

    //Screen for undefined messages
    if (jsonObj === undefined) {
        console.log("WARNING: Attempted to decode undefined")
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
    } catch (error) {
        //Decoding Failed, Not Properly Formatted
        console.log("Decoder Parsing JSON Failed with Error: " + error)
    }

    //Update page by element
    updateStartButton()
    updateStopButton()
    updateTurn()
    updateAccel()
    updateLapTable()

    //Check for end event flag
    if (jsonObj.endFlag) {
        console.log("End Flag Received: " + jsonObj.endFlag)
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
            } else {
                console.error("Reset Unnecessary OR Failed. Response: ", response.statusText);
            }
        })
        .catch(error => {
            console.error("Error during fetch: ", error);
        });
    }

    function updateStartButton() {
        //If timer is running but this object is not, update this object
        if (jsonObj.hasOwnProperty("timerRunning") && jsonObj.timerRunning && (startButton.getAttribute("isRunning") === "false")) {

            //Set local attributes
            startButton.disabled = true
            stopButton.disabled = false
            endButton.disabled = true
            accelButton.disabled = false
            turnButton.disabled = false
            startButton.setAttribute("isRunning", true)
            watch.startAt(jsonObj.timerEventTime, jsonObj.timerInternalTime);
        } else if (jsonObj.hasOwnProperty("timerRunning") && jsonObj.timerRunning) { //States match and timer running
            //TODO state catch? reverse?
        } else { //Timer not running
            if (jsonObj.hasOwnProperty("timerInternalTime") && jsonObj.timerInternalTime !== watch.getTime()) {
                watch.stopAt(jsonObj.hasOwnProperty("useInternalTime") && jsonObj.useInternalTime === true ? parseInt(watch.getTime()) : jsonObj.timerInternalTime)
            }
        }
    }

    function updateStopButton() {
        //If timer is not running but this object is, update object
        if (jsonObj.hasOwnProperty("timerRunning") && !jsonObj.timerRunning && (startButton.getAttribute("isRunning") === "true")) {
            //Update states to match by stopping
            startButton.disabled = false
            stopButton.disabled = true
            endButton.disabled = false
            accelButton.disabled = true
            turnButton.disabled = true
            startButton.setAttribute("isRunning", false)
            watch.stopAt(jsonObj.hasOwnProperty("useInternalTime") && jsonObj.useInternalTime === true ? parseInt(watch.getTime()) : jsonObj.timerInternalTime)
        }
    }

    function updateLapTable() {
        if (!jsonObj.hasOwnProperty("laps")) return;
        const newTable = document.createElement("table");
        newTable.classList.add("table");

        const oldTable = document.getElementById("lap-timer-table");
        newTable.id = "lap-timer-table"

        const thead = document.createElement("thead");
        thead.classList.add("thead-dark");

        newTable.appendChild(thead);

        const row = document.createElement("tr");

        // Create the "Lap #" header cell
        const lapHeader = document.createElement("th");
        lapHeader.scope = "col";
        lapHeader.textContent = "Lap #";

        // Create the "Time" header cell
        const timeHeader = document.createElement("th");
        timeHeader.scope = "col";
        timeHeader.textContent = "Time";

        row.appendChild(lapHeader);
        row.appendChild(timeHeader);

        // Append the row to the table
        thead.appendChild(row);

        for(let i = jsonObj.laps.length - 1; i >= 0; i--) {
            const row = document.createElement("tr");

            // Create the "Lap #" header cell
            const lapHeader = document.createElement("th");
            lapHeader.scope = "col";
            lapHeader.textContent = i + 1;

            // Create the "Time" header cell
            const timeHeader = document.createElement("th");
            timeHeader.scope = "col";
            // let dateObject = new Date(parseInt(jsonObj.laps[i]) / 1000);
            // time = `${dateObject.getHours()}:${dateObject.getMinutes()}:${dateObject.getSeconds()}.${dateObject.getMilliseconds()}`;
            console.log(jsonObj.laps)
            timeHeader.textContent = formatTime(parseInt(jsonObj.laps[i]));

            // Append cells to the row
            row.appendChild(lapHeader);
            row.appendChild(timeHeader);

            // Append the row to the table
            thead.appendChild(row);
        }
        oldTable.parentNode.replaceChild(newTable, oldTable);
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
        if (jsonObj.hasOwnProperty("accelRunning") && jsonObj.accelRunning && !watch.isAccel()) {
            //Start the accel
            watch.accelAt(jsonObj.accelStamp)

        //If accel is not running but this object's is, update local
        } else if (jsonObj.hasOwnProperty("accelRunning") && !jsonObj.accelRunning && watch.isAccel()) {
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
        console.log("Previous Tables Loaded") //TODO remove, debug only
    }
}

const formatTime = ms => {
    const [h, m, s, msRem] = [Math.floor(ms / 3600000), Math.floor(ms % 3600000 / 60000), Math.floor(ms % 60000 / 1000), ms % 1000];
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}::${String(msRem).padStart(3, '0')}`;
  };