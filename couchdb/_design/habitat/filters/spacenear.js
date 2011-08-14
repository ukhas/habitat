function(doc, req) {
    return ((doc.type == "payload_telemetry" && doc.data && doc.data._parsed) ||
            doc.type == "listener_info" ||
            doc.type == "listener_telem");
}
