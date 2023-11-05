function Stopwatch(elem) {

  var time = 0;
  var interval;
  var offset;

  function update() {
  if (this.isOn) {
    time += delta();
  }
  var formattedTime = timeFormatter(time);
  elem.textContent = formattedTime;
  }

  function delta() {
    var now = Date.now()
    var timePassed = now - offset;
    offset = now;
    return timePassed
  }

  function timeFormatter(timeInMS) {
    var time = new Date(timeInMS);
    var minutes = time.getMinutes().toString();
    var seconds = time.getSeconds().toString();
    var ms = time.getMilliseconds().toString();

    if (minutes.length < 2) {
      minutes = '0' + minutes;
    }

    if (seconds.length < 2) {
      seconds = '0' + seconds;
    }

    while (ms.length < 3) {
      ms = '0' + ms;
    }
    return minutes + ':' + seconds + '.' + ms;
  };

  function loadTable(turn, time_start, time_stop) {
      var table = document.getElementById('turn-table');
      var row = table.insertRow(-1);
      var participantCell = row.insertCell(0);
      var timeStartCell = row.insertCell(1);
      var timeStopCell = row.insertCell(2);
      var notesCell = row.insertCell(3);
      notesCell.contentEditable = "true";
      participantCell.innerHTML = turn;
      timeStartCell.innerHTML = time_start;
      timeStopCell.innerHTML = time_stop;
  };

  this.tableToJSON = function(table){
    var data = [];
    for (var i = 1; i < table.rows.length; i++) { 
        var tableRow = table.rows[i]; 
        var rowData = []; 
        for (var j = 0; j < tableRow.cells.length; j++) { 
            rowData.push(tableRow.cells[j].innerHTML);
        } 
        data.push(rowData); 
    } 
    var xhr = new XMLHttpRequest();
    xhr.open('POST', 'http://127.0.0.1:5001/data');
    xhr.setRequestHeader('Content-Type', 'application/json', 'charset=UTF-8');
    xhr.send("name=" + JSON.stringify(data));
}


function downloadCSVFile(csv_data) {
  CSVFile = new Blob([csv_data], { type: "text/csv" });
  var temp_link = document.createElement('a');
  temp_link.download = "GfG.csv";
  var url = window.URL.createObjectURL(CSVFile);
  temp_link.href = url;
  temp_link.style.display = "none";
  document.body.appendChild(temp_link);
  temp_link.click();
  document.body.removeChild(temp_link);
}

  this.isOn = false;

  this.start = function() {
    if (!this.isOn) {
      interval = setInterval(update.bind(this), 10);
      offset = Date.now();
      this.isOn = true;
    }
  };

  this.stop = function() {
    if (this.isOn) {
      clearInterval(interval);
      interval = null;
      this.isOn = false;
    }
  };

  var turn = 1;
  var isTurning = false;
  var startTime;

  this.turn = function() {
    if(isTurning){
      loadTable(turn, startTime, document.getElementById('timer').textContent);
      document.getElementById('turnButton').textContent = 'Start Turn'
      turn++;
      isTurning = false;
    }else{
      startTime = document.getElementById('timer').textContent;
      isTurning = true;
      document.getElementById('turnButton').textContent = 'End Turn'
    }
  };

  
}