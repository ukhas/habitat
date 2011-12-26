/* Copyright 2010 Adam Greig; Licensed under the GNU GPL v3, see LICENSE */
function(newDoc, oldDoc, userCtx) {
    if(newDoc.type != "listener_telemetry") return;
    
    function user_is(role) {
        return userCtx.roles.indexOf(role) >= 0;
    }

    if(oldDoc && !user_is('admin')) {
        throw({unauthorized:
            "Only administrators may edit listener_telemetry docs."});
    }

    function required(field, type, inside=newDoc, inside_name=null) {
        if(!inside[field]) {
            message = "Must have a `" + field + "` field";
            if(inside_name != null) {
                message += " inside " + inside_name + ".";
            } else if(inside != newDoc) {
                message += " inside unknown container (FIXME).";
            } else {
                message += " at the top level.";
            }
            throw({forbidden: message});
        }
        if(type && typeof(inside[field]) != type) {
            message = "Wrong type for `" + field + "` (is "
            message += typeof(inside[field]) + ", should be " + type + ").";
            throw({forbidden: message});
        }
    }
    
    required('time_created', 'number');
    required('time_uploaded', 'number');

    if(newDoc['time_created'] >= newDoc['time_uploaded']) {
        throw({forbidden:
                "Document creation date is after upload date."});
    }

    required('data', 'object');

    required('callsign', 'string', newDoc['data'], 'data');
    required('latitude', 'number', newDoc['data'], 'data');
    required('longitude', 'number', newDoc['data'], 'data');
    required('time', 'object', newDoc['data'], 'data');
    required('hour', 'number', newDoc['data']['time'], 'data.time');
    required('minute', 'number', newDoc['data']['time'], 'data.time');
    required('second', 'number', newDoc['data']['time'], 'data.time');
}
