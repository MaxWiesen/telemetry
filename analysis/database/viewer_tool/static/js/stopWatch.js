function Stopwatch(elem) {
  let time = 0;
  let interval;
  let offset;

  function update() {
    if (this.isOn) {
      time += delta();
    }
    let formattedTime = timeFormatter(time);
    elem.textContent = formattedTime;
  }

  function delta() {
    let now = Date.now();
    let timePassed = now - offset;
    offset = now;
    return timePassed;
  }

  function timeFormatter(timeInMS) {
    let time = new Date(timeInMS);
    let minutes = time.getMinutes().toString();
    let seconds = time.getSeconds().toString();
    let ms = time.getMilliseconds().toString();

    if (minutes.length < 2) {
      minutes = "0" + minutes;
    }

    if (seconds.length < 2) {
      seconds = "0" + seconds;
    }

    while (ms.length < 3) {
      ms = "0" + ms;
    }
    return minutes + ":" + seconds + "." + ms;
  }

  function loadTable(turn, time_start, time_stop, notes, table) {
    let row = table.insertRow(-1);
    let participantCell = row.insertCell(0);
    let timeStartCell = row.insertCell(1);
    let timeStopCell = row.insertCell(2);
    let notesCell = row.insertCell(3);
    notesCell.contentEditable = "true";
    notesCell.innerHTML = notes;
    participantCell.innerHTML = turn;
    timeStartCell.innerHTML = time_start;
    timeStopCell.innerHTML = time_stop;
  }

  this.tableToStateJSON = function (name, table, add) {
    let data = [];
    for (var i = 1; i < table.rows.length; i++) {
      let tableRow = table.rows[i];
      let rowData = [];
      for (var j = 0; j < tableRow.cells.length; j++) {
        rowData.push(tableRow.cells[j].innerHTML);
      }
      data.push(rowData);
    }
    let xhr = new XMLHttpRequest();
    xhr.open("POST", add, true);
    xhr.setRequestHeader("Content-Type", "application/json", "charset=UTF-8");
    if (name === "accels") {
      data = { accels: data };
      data["accel"] = accel;
    } else if (name === "turns") {
      data = { turns: data };
      data["turn"] = turn;
    }
    xhr.send(JSON.stringify(data));
  };

  this.tableToJSON = function (table, add) {
    let data = [];
    for (var i = 1; i < table.rows.length; i++) {
      let tableRow = table.rows[i];
      let rowData = [];
      for (var j = 0; j < tableRow.cells.length; j++) {
        rowData.push(tableRow.cells[j].innerHTML);
      }
      data.push(rowData);
    }
    let xhr = new XMLHttpRequest();
    xhr.open("POST", add, true);
    xhr.setRequestHeader("Content-Type", "application/json", "charset=UTF-8");
    xhr.send(JSON.stringify(data));
  };

  this.isOn = false;

  this.start = function () {
    if (!this.isOn) {
      interval = setInterval(update.bind(this), 10);
      offset = Date.now();
      this.isOn = true;

      let data = new Object();
      data.offset = offset;
      data.isOn = true;
      let xhr = new XMLHttpRequest();
      xhr.open("POST", getURL() + "stop_watch_state");
      xhr.setRequestHeader("Content-Type", "application/json", "charset=UTF-8");
      xhr.send(JSON.stringify(data));
    }
  };

  this.stop = function () {
    if (this.isOn) {
      clearInterval(interval);
      interval = null;
      this.isOn = false;

      let data = new Object();
      data.offset = offset;
      data.time = time;
      data.isOn = false;
      let xhr = new XMLHttpRequest();
      xhr.open("POST", getURL() + "stop_watch_state");
      xhr.setRequestHeader("Content-Type", "application/json", "charset=UTF-8");
      xhr.send(JSON.stringify(data));
    }
  };

  var turn = 1;
  var isTurning = false;
  var startTime;

  this.turn = function () {
    if (isTurning) {
      loadTable(
        turn,
        startTime,
        document.getElementById("timer").textContent,
        "",
        document.getElementById("turn-table")
      );
      turn++;
      isTurning = false;

      this.tableToStateJSON(
        "turns",
        document.getElementById("turn-table"),
        getURL()+ "stop_watch_state"
      );

      document.getElementById("turnButton").textContent = "Start Turn";
    } else {
      startTime = document.getElementById("timer").textContent;
      isTurning = true;
      document.getElementById("turnButton").textContent = "End Turn";
    }
  };

  var accel = 1;
  var isAccel = false;
  var startAccelTime;

  this.accel = function () {
    if (isAccel) {
      loadTable(
        accel,
        startAccelTime,
        document.getElementById("timer").textContent,
        "",
        document.getElementById("accel-table")
      );
      accel++;
      isAccel = false;

      this.tableToStateJSON(
        "accels",
        document.getElementById("accel-table"),
        getURL() + "stop_watch_state"
      );

      document.getElementById("accelButton").textContent = "Start Acceleration";
    } else {
      startAccelTime = document.getElementById("timer").textContent;
      isAccel = true;
      document.getElementById("accelButton").textContent = "End Acceleration";
    }
  };

  this.recoverState = function (state) {
    if ("offset" in state) {
    }
    if ("isOn" in state) {
      if (state["isOn"]) {
        time = state["time"] + (Date.now() - state["offset"]);
        interval = setInterval(update.bind(this), 10);
        offset = Date.now();
        this.isOn = true;
      } else {
        if ("time" in state) time = state["time"];
        this.isOn = false;
        clearInterval(interval);
        interval = null;
      }
    }
    if ("turn" in state) {
      turn = state["turn"];
    }
    if ("turns" in state) {
      for (cell in state["turns"]) {
        let a = JSON.stringify(state["turns"][cell]);
        a = a.substring(1, a.length - 1).split(",");
        loadTable(
          a[0].substring(1, a[0].length - 1),
          a[1].substring(1, a[1].length - 1),
          a[2].substring(1, a[2].length - 1),
          a[3].substring(1, a[3].length - 1),
          document.getElementById("turn-table")
        );
      }
    }
    if ("accel" in state) {
      accel = state["accel"];
    }
    if ("accels" in state) {
      for (cell in state["accels"]) {
        let a = JSON.stringify(state["accels"][cell]);
        a = a.substring(1, a.length - 1).split(",");
        loadTable(
          a[0].substring(1, a[0].length - 1),
          a[1].substring(1, a[1].length - 1),
          a[2].substring(1, a[2].length - 1),
          a[3].substring(1, a[3].length - 1),
          document.getElementById("accel-table")
        );
      }
    }
    update();
  };
}

function getURL() { 
  var arr = window.location.href.split("/"); 
  delete arr[arr.length - 1]; 
  return arr.join("/"); 
}