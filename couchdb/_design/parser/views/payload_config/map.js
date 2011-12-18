/* Copyright 2010, 2011 Adam Greig; Licensed under the GNU GPL v3, see LICENSE */
function(doc) {
    if(doc.type == "flight") {
        var payload;
        for(payload in doc.payloads) {
            emit([payload, doc.end], null);
        }
    }
}
