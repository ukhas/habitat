/* Copyright 2011 Adam Greig; Licensed under the GNU GPL v3, see LICENSE */
function(doc, req) {
    return (doc.type == "payload_telemetry" && doc.data && !doc.data._parsed);
}
