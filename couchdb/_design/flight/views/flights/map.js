/* Copyright 2011 (C) Daniel Richman; GNU GPL 3 */
function (doc) {
    if (doc.type == "flight")
        emit(doc.end, null);
}
