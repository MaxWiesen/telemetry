//Decodes information from .json file and updates the client's instances
function decodeValues(jsonObj) {
    //Decode string to actual JSON object
    jsonObj = JSON.parse(jsonObj)

    //Pull all relevant on-screen elements to be updated
    //let startButton = document.getElementById('startButton');
    //let stopButton = document.getElementById('stopButton');
    //let clock = document.getElementById('timer');

    //TODO more elements here later...

    //Update page by button elements
    //updateStartButton()
    //updateStopButton()
    updateLapTable()

    function updateStartButton() {
        //If timer is running but this object is not, update this object
        if (jsonObj.timerRunning && (startButton.getAttribute("isRunning") === "false")) {

            //Set local attributes
            startButton.setAttribute("isRunning", true)
            saveButton.setAttribute("disabled", true)
            watch.startAt(jsonObj.unixTimerStarted);

            //Alert database about changes
            let xhr = new XMLHttpRequest()
            xhr.open('POST', host_ip + ':3/set_event_time', true)
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
            let dateObject = new Date(parseInt(jsonObj.laps[i]) / 1000);
            time = `${dateObject.getHours()}:${dateObject.getMinutes()}:${dateObject.getSeconds()}.${dateObject.getMilliseconds()}`;
            timeHeader.textContent = time;

            // Append cells to the row
            row.appendChild(lapHeader);
            row.appendChild(timeHeader);
    
            // Append the row to the table
            thead.appendChild(row);
        }
        oldTable.parentNode.replaceChild(newTable, oldTable);
    }
}

//TODO remove testing data
//Data to be invoked for testing
const jsonDataTest0 = {
    "startStatus": false,
    "stopStatus": false,
    "unixTime": 1729457473500
};

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