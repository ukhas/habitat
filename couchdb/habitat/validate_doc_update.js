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
function(newDoc, oldDoc, userCtx) {
    // Forbid deleting documents
    if(newDoc._deleted)
        throw({forbidden: "Documents may not be deleted."});

    // Forbid changing/creating documents such as telemetry
    // or listener information unless you are the habitat user
    // (all such documents should go through the habitat backend)
    if(newDoc.type != "flight" && userCtx.name != "habitat")
        throw({forbidden:
                "Only the habitat user may create non-flight documents"});
}

