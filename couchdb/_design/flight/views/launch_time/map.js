/* Copyright 2011 (C) Daniel Richman; GNU GPL 3 */

function (doc) {
    // flights sorted by launch time

    if(doc.type == "flight") {
        if (doc.launch && doc.launch.time) {
            emit(doc.launch.time, null);
        } else {
            /* TODO: Remove this, once validation exists and all flight docs
             * therefore have a launch time. */
            emit(doc.start, null);
        }
    }
}
