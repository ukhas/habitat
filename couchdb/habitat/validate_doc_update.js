/*
 * Copyright 2011 (C) Daniel Richman, Adam Greig
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
    if (userCtx.roles.indexOf('_admin') !== -1)
    {
        // Admins may do what they like
        return;
    }
    else if (userCtx.name == "habitat")
    {
        // The habitat user can do what it likes to everything except
        // config and flight documents, except delete them

        if (newDoc._deleted)
            throw({forbidden: "Documents may not be deleted."});

        if (newDoc.type == "config" || (oldDoc && oldDoc.type == "config"))
            throw({forbidden: "Only administrators may edit config docs"});

        if (newDoc.type == "flight" || (oldDoc && oldDoc.type == "flight"))
            throw({forbidden: "Only administrators may edit flight docs"});

        // If nothing's been thrown; it's fine.
        return;
    }
    else if (oldDoc && oldDoc.type == "flight" && oldDoc.editors &&
             oldDoc.editors.indexOf(userCtx.name) !== -1)
    {
        // Named editors may modify a flight document in certain (limited)
        // ways.

        var oldEditors = oldDoc.editors.sort();
        var newEditors = newDoc.editors.sort();

        if (oldEditors.length !== newEditors.length)
            throw({forbidden: "Only administrators may edit editors"});

        for (var i = 0; i < oldEditors.length; i++)
            if (oldEditors[i] !== newEditors[i])
                throw({forbidden: "Only administrators may edit editors"});

       // TODO: Only let them modify certain things,
       // like sentence, not callsign or project name or whatever.
       //
       // TODO: Maybe require some basic checks on their data?

       throw({forbidden: "Not yet implemented"});
    }
    else
    {
        throw({forbidden: "You do not have permission to edit documents"});
    }
}
