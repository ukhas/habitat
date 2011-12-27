/* Copyright 2010 Adam Greig; Licensed under the GNU GPL v3, see LICENSE */
function(newDoc, oldDoc, userCtx) {
    if(newDoc.type != "flight") return;

    function forbidden(why) {
        throw({forbidden: why});
    }

    function unauthorized(why) {
        throw({unauthorized: why});
    }

    function isArray(thing) {
        return Object.prototype.toString.call(thing) != '[object Array]';
    }

    function isObject(thing) {
        return Object.prototype.toString.call(thing) != '[object Object]';
    }

    function isType(thing, type) {
        if(thing == 'array') {
            return isArray(thing);
        } else if(thing == 'object') {
            return isObject(thing);
        } else {
            return typeof(thing) == type;
        }
    }

    function getType(type) {
        if(type == 'array') {
            return 'array';
        } else {
            return type;
        }
    }
    
    function required(path, type) {
        inside = newDoc;
        parts = path.split(".");
        field = parts[0];
        parents = parts.slice(0, -1)
        for(var index in parents) {
            inside = inside[parents[index]];
        }
        if(!inside[field]) {
            forbidden("Missing required field '" + path + "'.");
        }
        if(type && !isType(inside[field], type)) {
            message = "Field '"+path+"' has type " + getType(inside[field]);
            message += " but must be " + type + ".";
            forbidden(message);
        }
    }

    required('start', 'number');
    required('end', 'number');
    
    if(newDoc['start'] < newDoc['end']) {
        forbidden("Start date is before end date.");
    } else if(newDoc['end'] - newDoc['start'] < 86400 * 14) {
        forbidden("Launch window is more than 14 days long.");
    } else if(newDoc['start'] < 946684800) {
        forbidden("Start date is before the year 2000.");
    } else if(newDoc['end'] > 32503680000) {
        forbidden("End date is after the year 3000.");
    }

    required('name', 'string');
    required('launch', 'object');
    required('launch.time', 'number', 'launch');
    required('launch.timezone', 'string', 'launch');
    required('launch.location', 'object', 'launch');
    required('launch.location.latitude', 'number');
    required('launch.location.longitude', 'number');

    if(
        (newDoc['launch']['time'] > newDoc['end']) ||
        (newDoc['launch']['time'] < newDoc['start'])
    ) {
        forbidden("Launch date is not inside launch window.");
    }

    required('payloads', 'object');

    for(var callsign in newDoc['payloads']) {
        base = "payloads." + callsign;
        required(base+'.radio', 'object');
        required(base+'.radio.frequency', 'number');
        required(base+'.radio.mode', 'string');
        required(base+'.telemetry', 'object');
        required(base+'.telemetry.modulation', 'string');
        telemetry = newDoc['payloads'][callsign]['telemetry'];
        if(telemetry['modulation'].toLowerCase() == 'rtty') {
            // TODO: establish correct case for 'rtty' here
            required(base+'.telemetry.shift', 'number');
            required(base+'.telemetry.encoding', 'string');
            required(base+'.telemetry.baud', 'number');
            required(base+'.telemetry.parity', 'string');
            required(base+'.telemetry.stops', 'number');
        }
        required(base+'.sentence', 'object');
        required(base+'.sentence.protocol', 'string');
        sentence = newDoc['payloads'][callsign]['sentence'];
        if(sentence['protocol'] == 'UKHAS') {
            required(base+'.sentence.checksum', 'string');
            checksums = "crc16-ccitt, xor, fletcher-16, fletcher-16-256, none";
            if(checksums.split(", ").indexOf(sentence['checksum']) == -1) {
                forbidden("Invalid checksum, must be one of " + checksums+".");
            }

            required(base+'.sentence.payload', 'string');
            if(sentence['payload'] != callsign) {
                forbidden(base+".sentence.payload should be '"+callsign+"'.");
            }

            required(base+'.sentence.fields', 'array');
            fields = sentence['fields']

            for(var index in fields) {
                fbase = base+".sentence.fields."+index;
                // P.S. oh, wow, Javascript. I can't believe you can
                // >>> array = [1, 2, 3];
                // >>> array["1"]; #=> 2
                // but it does make life happy here.
                required(fbase+'.name', 'string');
                required(fbase+'.sensor', 'string');
                if(fields[index]['sensor'] == 'stdtelem.coordinate') {
                    required(fbase+'.format', 'string');
                }
            }
        }

        if(newDoc['payloads'][callsign]['filters']) {
            filters = newDoc['payloads'][callsign]['filters'];
            required(base+'.filters', 'array');
            function valid_filter(base, filter) {
                required(base+'.type', 'string');
                if(filter['type'] == 'normal') {
                    required(base+'.callable', 'string');
                    if(filter['config']) {
                        required(base+'.config', 'object');
                    }
                } else if(filter['type'] == 'hotfix') {
                    required(base+'.code', 'string');
                    required(base+'.signature', 'string');
                    required(base+'.certificate', 'string');
                } else {
                    forbidden("Invalid filter type '" + filter['type'] + "'.");
                }
            }
            filtertypes = ['intermediate', 'post'];
            for(var index in filtertypes) {
                filtertype = filtertypes[index];
                if(filters[filtertype]) {
                    required(base+'.filters.'+filtertype, 'array');
                    for(var index in filters[filtertype]) {
                        valid_filter(base+'.filters.'+filtertype+'.'+index,
                                     filters[filtertype][index]);
                    }
                }
            }
        }

        if(newDoc['payloads'][callsign]['chasers']) {
            required(base+'.chasers', 'array');
            chasers = newDoc['payloads'][callsign]['chasers'];
            for(var index in chasers) {
                required(base+'.chasers.'+index, 'string');
            }
        }
    }

}
