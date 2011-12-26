/* Copyright 2010 Adam Greig; Licensed under the GNU GPL v3, see LICENSE */
function(newDoc, oldDoc, userCtx) {
    allowed_types = [
        "flight", "listener_info", "listener_telemetry", "payload_telemetry"
    ];

    if(oldDoc && newDoc.type != oldDoc.type)
        throw({forbidden: "Cannot change document type."});

    for(var i in allowed_types) {
        if(newDoc.type == allowed_types[i])
            return;
    }

    throw({forbidden: "Invalid document type."});
}
