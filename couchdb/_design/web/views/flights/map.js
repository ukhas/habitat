/* Copyright 2011 (C) Daniel Richman; GNU GPL 3 */

function(doc) {
    //Emit a list of flight docs, sorted by their launch time.

    if(doc.type == "flight") {
        if (doc.launch && doc.launch.time) {
            emit(doc.launch.time, doc);
        } else {
            emit(doc.start, doc);
        }
    }
}

