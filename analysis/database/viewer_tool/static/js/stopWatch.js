class Stopwatch {
  constructor(elem) {
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
      var now = Date.now();
      var timePassed = now - offset;
      offset = now;
      return timePassed;
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

    this.isOn = false;

    this.start = function () {
      if (!this.isOn) {
        interval = setInterval(update.bind(this), 10);
        offset = Date.now();
        this.isOn = true;
      }
    };

    this.stop = function () {
      if (this.isOn) {
        clearInterval(interval);
        interval = null;
        this.isOn = false;
      }
    };

  }
}