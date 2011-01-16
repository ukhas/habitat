function(doc) {
    // Emit a row per current listener_info document containing their callsign
    // and the time this LISTENER_INFO document was uploaded.
    if(doc.type == "listener_info") {
        emit([doc.data.callsign, doc.uploaded_time], null);
    }
}
