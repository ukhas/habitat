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

    function required(field, type, inside_path=null) {
        inside = newDoc;
        inside_name = "Top level"
        if(inside_path != null) {
            inside_name = inside_path;
            parts = inside_path.split(".");
            for(index in parts) {
                inside = inside[parts[index]];
            }
        }
        if(!inside[field]) {
            message = inside_name + " must contain a `" + field + "` field.";
            throw({forbidden: message});
        }
        if(type && typeof(inside[field]) != type) {
            message = "In " + inside_name + ", `" + field + "` field has ";
            message += "type " + typeof(inside[field]) + " but must be ";
            message += type + ".";
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

    required('callsign', 'string', 'data');
    required('latitude', 'number', 'data');
    required('longitude', 'number', 'data');
    required('time', 'object', 'data');
    required('hour', 'number', 'data.time');
    required('minute', 'number', 'data.time');
    required('second', 'number', 'data.time');
}
