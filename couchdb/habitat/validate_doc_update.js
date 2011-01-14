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

