/* Copyright 2010 Adam Greig; Licensed under the GNU GPL v3, see LICENSE */
function(doc) {
    if(doc.type == "flight" || doc.type == "sandbox") {
        var payload;
        for(payload in doc.payloads) {
            if(doc.type == "flight")
                emit([payload, doc.end], null);
            else
                emit([payload, "sandbox"], null);
        }
    }
}
