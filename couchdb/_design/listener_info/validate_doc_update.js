/* Copyright 2010 Adam Greig; Licensed under the GNU GPL v3, see LICENSE */
function(newDoc, oldDoc, userCtx) {
    if(newDoc.type != "listener_info") return;
    
    function user_is(role) {
        return userCtx.roles.indexOf(role) >= 0;
    }

    if(oldDoc && !user_is('admin')) {
        throw({unauthorized:
                "Only administrators may edit listener_info docs."});
    }

    function required(path, type) {
        inside = newDoc;
        parts = path.split(".");
        field = parts[0];
        parents = parts.slice(0, -1)
        for(index in parents) {
            inside = inside[parents[index]];
        }
        if(!inside[field]) {
            forbidden("Missing required field '" + path + "'.");
        }
        if(type && typeof(inside[field]) != type) {
            message = "Field '" + path + "' has type " + typeof(inside[field]);
            message += " but must be " + type + ".";
            forbidden(message);
        }
    }

    required('time_created', 'number');
    required('time_uploaded', 'number');

    if(newDoc['time_created'] >= newDoc['time_uploaded']) {
        throw({forbidden:
                "Document creation date is after upload date."});
    }

    required('data', 'object');
    
    required('data.callsign', 'string');
}
