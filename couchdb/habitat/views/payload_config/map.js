function(doc) {
    // Emit a row per payload per flight document, giving the end time
    // of that flight document and the payload name.
    //
    // Typically queried with
    //     startkey=["payload",NOW]&limit=1&include_docs=true
    // to obtain the correct configuration for a given payload.
    if(doc.type == "flight") {
        var payload;
        for(payload in doc.payloads) {
            emit([payload, doc.end], null);
        }
    }
}
