
var label = function (id, name) {
    window.location.replace("/label/" + id + "?token={{token}}" + "&name=" + name);
}
var c = document.getElementById("canvas");
var ctx = c.getContext("2d");
var drawLabels = function (id, xMin, xMax, yMin, yMax) {
    ctx.fillStyle = "#20DFDF40";
    ctx.fillRect(xMin, yMin, xMax - xMin, yMax - yMin);
    ctx.strokeStyle = "black";
    //ctx.fillStyle = "red";
    ctx.rect(xMin, yMin, xMax - xMin, yMax - yMin);
    ctx.lineWidth = "4";

    ctx.stroke();
    ctx.font = "30px Arial";
    ctx.fillText("id: " + id, xMin, yMin - 10);
};

//load and display image
var image = new Image();
image.onload = function (e) {
    ctx.canvas.width = image.width;
    ctx.canvas.height = image.height;
    c.width = image.width;
    c.height = image.height;
    ctx.drawImage(image, 0, 0);
    console.log(labels);
    for (i = 0; i < labels.length; i++) {
        drawLabels(labels[i].id, labels[i].xMin, labels[i].xMax, labels[i].yMin, labels[i].yMax);
    }
};
image.style.display = "block";
image.src = "image/{{ image }}";

// this flage is true when the user is dragging the mouse
var isDown = false;
// these vars will hold the starting mouse position
var startX, startY, mouseX, mouseY, endX, endY;

function calcPoints(startX, startY, endX, endY) {
    var temp = 0;
    if (startX > endX) {
        temp = startX;
        startX = endX;
        endX = temp;
    }
    if (startY > endY) {
        temp = startY;
        startY = endY;
        endY = temp;
    }
    return [startX, startY, endX, endY]
}

function handleMouseDown(e) {
    e.preventDefault();
    e.stopPropagation();
    // save the starting x/y of the rectangle

    startX = parseInt((image.width / c.scrollWidth) * e.offsetX);
    startY = parseInt((image.height / c.scrollHeight) * e.offsetY);
    // set a flag indicating the drag has begun
    isDown = true;
}

function handleMouseUp(e) {
    e.preventDefault();
    e.stopPropagation();
    // the drag is over, clear the dragging flag
    if (isDown) {
        endX = parseInt((image.width / c.scrollWidth) * e.offsetX);
        endY = parseInt((image.height / c.scrollHeight) * e.offsetY);
        [startX, startY, endX, endY] = calcPoints(startX, startY, endX, endY)
        window.location.replace("/add/" + (labels.length + 1) + "?token={{token}}" +
            "&xMin=" + startX +
            "&xMax=" + endX +
            "&yMin=" + startY +
            "&yMax=" + endY
        );
        isDown = false;
    }
}

function handleMouseOut(e) {
    e.preventDefault();
    e.stopPropagation();
    // the drag is over, clear the dragging flag
    if (isDown) {
        endX = parseInt((image.width / c.scrollWidth) * e.offsetX);
        endY = parseInt((image.height / c.scrollHeight) * e.offsetY);
        [startX, startY, endX, endY] = calcPoints(startX, startY, endX, endY)
        window.location.replace("/add/" + (labels.length + 1) +
            "?token=" + token +
            "&xMin=" + startX +
            "&xMax=" + endX +
            "&yMin=" + startY +
            "&yMax=" + endY);
        isDown = false;
    }
}

function handleMouseMove(e) {
    e.preventDefault();
    e.stopPropagation();
    // if we're not dragging, just return
    if (!isDown) { return; }
    // get the current mouse position
    mouseX = parseInt((image.width / c.scrollWidth) * e.offsetX);
    mouseY = parseInt((image.height / c.scrollHeight) * e.offsetY);
    ctx.strokeStyle = "red";
    ctx.lineWidth = "4";
    ctx.stroke();
    // clear the canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(image, 0, 0);
    // calculate the rectangle width/height based
    // on starting vs current mouse position
    var width = mouseX - startX;
    var height = mouseY - startY;

    // draw a new rect from the start position 
    // to the current mouse position
    ctx.strokeRect(startX, startY, width, height);
}
// listen for mouse events
$("#canvas").mousedown(function (e) { handleMouseDown(e); });
$("#canvas").mousemove(function (e) { handleMouseMove(e); });
$("#canvas").mouseup(function (e) { handleMouseUp(e); });
$("#canvas").mouseout(function (e) { handleMouseOut(e); });