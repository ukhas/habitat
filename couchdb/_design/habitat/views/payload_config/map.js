/*
 * Copyright 2010 (C) Adam Greig
 *
 * This file is part of habitat.
 *
 * habitat is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * habitat is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with habitat.  If not, see <http://www.gnu.org/licenses/>.
 */
function(doc) {
    // Emit a row per payload per flight document, giving the end time
    // of that flight document and the payload name.
    //
    // Typically queried with
    //     startkey=["payload",NOW]&limit=1&include_docs=true
    // to obtain the correct configuration for a given payload.
    if(doc.type == "flight" || doc.type == "sandbox") {
        var payload;
        for(payload in doc.payloads) {
            if(doc.type == "flight")
                emit([payload, doc.end], null);
            else
                emit([payload, "sandbox"], null);
        }
    }
}
