/* Copyright 2011 (C) Daniel Richman; GNU GPL 3 */

function (doc) {
    // payload_telemetry sorted by flight, then payload, then calculated
    //      estimated received time

    // _sentence is used as the value if present to speed up the most common
    // use case.

    if (doc.type != "payload_telemetry")
        return;

    if (!doc.data || !doc.data._parsed || !doc.receivers)
        return;

    // Calculate the "estimated received time"
    var sum_x = 0, sum_x2 = 0, n = 0;

    for (var callsign in doc.receivers)
    {
        var x = doc.receivers[callsign].time_created;
        sum_x += x;
        sum_x2 += (x * x);
        n++;
    }

    var mean = sum_x / n;
    var std_dev = Math.sqrt((sum_x2 / n) - (mean * mean));

    var new_sum_x = 0, new_n = 0;

    for (var callsign in doc.receivers)
    {
        var x = doc.receivers[callsign].time_created;

        if (Math.abs(x - mean) > std_dev)
            continue;

        new_sum_x += x;
        new_n++;
    }

    var estimated_received_time;
    if (new_n != 0)
        estimated_received_time = (new_sum_x / new_n);
    else
        estimated_received_time = mean;

    // emit key: [flight id, payload name, estimated received time]
    //      value: _sentence, if present.
    var value = null;
    if (doc.data._sentence)
        value = doc.data._sentence;

    emit([doc.data._flight, doc.data.payload, estimated_received_time],
         value);
}
