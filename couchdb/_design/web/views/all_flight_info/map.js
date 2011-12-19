/* Copyright 2011 (C) Daniel Richman; GNU GPL 3 */

function(doc, req) {
    // Select all listener_telem, listener_info and payload_telemetry documents
    // that are involved or associated in any way with a certain flight.

    if (doc.type == "payload_telemetry" && doc.data._flight)
    {
        emit(doc.data._flight, doc);
    }
    else if (doc.type == "listener_telem" || doc.type == "listener_info" &&
             doc.relevant_flights)
    {
        for (var i = 0; i < doc.relevant_flights; i++)
        {
            emit(doc.relevant_flights[i], doc);
        }
    }
}
