/* Copyright 2010 Adam Greig; Licensed under the GNU GPL v3, see LICENSE */
function(doc) {
    // Emit a row per current listener_info document containing their callsign
    // and the time this LISTENER_INFO document was created by the listener.
    if(doc.type == "listener_info") {
        emit([doc.time_created, doc.data.callsign], null);
    }
}
