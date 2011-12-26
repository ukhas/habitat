/* Copyright 2010 Adam Greig; Licensed under the GNU GPL v3, see LICENSE */
function(doc) {
    // listener_info sorted by time created, then callsign
    if(doc.type == "listener_info") {
        emit([doc.time_created, doc.data.callsign], null);
    }
}
