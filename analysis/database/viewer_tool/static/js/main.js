$( document ).ready(function() {
    console.log("This is a message");
    var timer = document.getElementById("timer");
    var startButton = document.getElementById("start");
    var stopButton = document.getElementById("end");

    var watch = new Stopwatch(timer);

    startButton.addEventListener('click', function() {
        // watch.start();
    });

    stopButton.addEventListener('click', function() {
        // watch.stop();
    });
});

