/* Copyright 2010 Adam Greig; Licensed under the GNU GPL v3, see LICENSE */
function(doc) {
    // listener_telemetry sorted by time created, then callsign
    if(doc.type == "listener_telemetry") {
        emit([doc.time_created, doc.data.callsign], null);
    }
}
