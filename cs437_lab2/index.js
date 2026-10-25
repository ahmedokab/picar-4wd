var server_port = 65432;
var server_addr = "192.168.1.203";      

const net = require('net');

// Send one command to the car, then show the JSON stats it sends back.
function send(cmd) {
    const client = net.createConnection({ port: server_port, host: server_addr }, () => {
        client.write(`${cmd}\r\n`);
    });

    client.on('data', (data) => {
        const stats = JSON.parse(data.toString());
        if (stats.error) {
            document.getElementById("status").innerHTML = stats.error;
        } else {
            show(stats);
        }
        client.end();
    });

    client.on('error', () => {
        document.getElementById("status").innerHTML = "Cannot reach car";
    });
}

function show(stats) {
    document.getElementById("status").innerHTML = "Connected";
    document.getElementById("temperature").innerHTML = stats.temperature;
    document.getElementById("battery").innerHTML = stats.battery;
    document.getElementById("direction").innerHTML = stats.direction;
    document.getElementById("speed").innerHTML = stats.speed;
    document.getElementById("distance").innerHTML = stats.distance;
}

// Arrow keys and space do the same as the buttons.
const KEYS = { ArrowUp: "forward", ArrowDown: "backward", ArrowLeft: "left", ArrowRight: "right", " ": "stop" };

document.addEventListener('keydown', (e) => {
    if (e.repeat || !KEYS[e.key]) return;
    e.preventDefault();
    send(KEYS[e.key]);
});

// Ask the car for fresh stats once a second.
setInterval(() => send("stats"), 1000);