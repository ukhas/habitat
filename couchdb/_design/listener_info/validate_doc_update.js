/* Copyright 2010 Adam Greig; Licensed under the GNU GPL v3, see LICENSE */
function(newDoc, oldDoc, userCtx) {
    if(newDoc.type != "listener_info") return;
    
    function user_is(role) {
        return userCtx.roles.indexOf(role) >= 0;
    }

    if(oldDoc && !user_id('admin')) {
        throw({unauthorized:
                "Only administrators may edit listener_info docs."});
    }

    function required(field, type) {
        if(!newDoc[field]) {
            message = "Document must have a `" + field + "` field.";
            throw({forbidden: message});
        }
        if(type && typeof(newDoc[field]) != type) {
            message = "Wrong type for `" + field + "` ("
            message += typeof(newDoc[field]) + "), should be " + type + ".";
            throw({forbidden: message});
        }
    }

    required('time_created', 'number');
    required('time_uploaded', 'number');

    if(newDoc['time_created'] >= newDoc['time_uploaded']) {
        throw({forbidden:
                "Document cannot be created after it was uploaded."});
    }

    required('data', object);
    
    if(!newDoc['data']['callsign']) {
        throw({forbidden: "`data` must contain at least `callsign`."});
    }

    if(typeof(newDoc['data']['callsign'] != 'string') {
        throw({forbidden: "`callsign` must be a string."});
    }
}
