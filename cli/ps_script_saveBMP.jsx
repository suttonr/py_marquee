// Photoshop Script: Save current document as 24-bit Windows BMP
function getTimestamp() {
    var now = new Date();
    var y = now.getFullYear();
    // Months are 0-indexed, so we add 1 and pad with a leading zero
    var m = ("0" + (now.getMonth() + 1)).slice(-2);
    var d = ("0" + now.getDate()).slice(-2);
    var h = ("0" + now.getHours()).slice(-2);
    var min = ("0" + now.getMinutes()).slice(-2);
    var s = ("0" + now.getSeconds()).slice(-2);

    return y + m +  d + "T" + h + min + s;
}

if (app.documents.length > 0) {
    var doc = app.activeDocument;
    
    // Define the file destination (Defaults to Desktop)
    var desktopPath = "/Users/ryan/scoreboard";
    var fileName = doc.name.split('.')[0]; // Remove existing extension
    var saveFile = new File(desktopPath + "/" + fileName + "_" + getTimestamp() + ".bmp");

    // Configure BMP Save Options
    var bmpOptions = new BMPSaveOptions();
    bmpOptions.alphaChannels = false;
    bmpOptions.depth = BMPDepthType.TWENTYFOUR; // Enforces 24-bit
    bmpOptions.osType = OperatingSystem.WINDOWS; // Enforces Windows format
    bmpOptions.rleCompression = false;

    // Execute Save
    doc.saveAs(saveFile, bmpOptions, true, Extension.LOWERCASE);
    var userAnswer = confirm("File is saved, display?");
    if (userAnswer) {
        app.system("/Users/ryan/git/py_marquee/venv/bin/python3 /Users/ryan/git/py_marquee/cli/matrix-cli.py  clear");
        app.system("/Users/ryan/git/py_marquee/venv/bin/python3 /Users/ryan/git/py_marquee/cli/matrix-cli.py  send --file-name " + saveFile);
    }
    alert("Saved to Desktop: " + fileName + ".bmp");
} else {
    alert("No active document found!");
}