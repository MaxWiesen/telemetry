  this.recoverState = function (state) {
    if ("offset" in state) {
      alert(state[offset]);
      // offset = state[offset];
      // time += delta();
    }
    // if("isOn" in state){
    //   this.isOn = state[offset];
    //   if(state[offset])
    //     interval = null;
    //   else
    //     interval = setInterval(update.bind(this), 10);

    // }
  };

  this.start = function () {
    if (!this.isOn) {
      interval = setInterval(update.bind(this), 10);
      offset = Date.now();
      this.isOn = true;

      let data = new Object();
      data.offset = offset;
      data.isOn = true;
      xhr.open('POST', 'http://127.0.0.1:5001/stop_watch_state');
      xhr.setRequestHeader('Content-Type', 'application/json', 'charset=UTF-8');
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
      data.isOn = false;
      xhr.open('POST', 'http://127.0.0.1:5001/stop_watch_state');
      xhr.setRequestHeader('Content-Type', 'application/json', 'charset=UTF-8');
      xhr.send(JSON.stringify(data));
    }
  }