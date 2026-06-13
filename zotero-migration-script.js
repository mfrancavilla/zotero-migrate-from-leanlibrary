async function migrateItemsByTag() {
    const itemIDs = await Zotero.Items.getAllIDs(Zotero.Libraries.userLibraryID);

    await Zotero.DB.executeTransaction(async () => {
        for (let id of itemIDs) {
            let item = await Zotero.Items.getAsync(id);
            if (!item.isRegularItem()) continue;

            let tags = item.getTags();
            let modified = false;

            for (let tag of tags) {
                if (tag.tag.startsWith("ZOTEROMIGRATE:")) {
                    // Extract path: e.g., "US/Intussusception"
                    let path = tag.tag.replace("ZOTEROMIGRATE:", "").trim();
                    let pathParts = path.split('/');
                    
                    let collection = await findNestedCollection(pathParts);
                    
                    if (collection) {
                        await collection.addItem(item.id);
                        await item.removeTag(tag.tag);
                        modified = true;
                    } else {
                        Zotero.debug("Could not find collection path: " + path);
                    }
                }
            }
            if (modified) await item.save();
        }
    });
    return "Migration complete.";
}

// Helper: Traverse hierarchy based on path array
async function findNestedCollection(pathParts) {
    let currentCollection = null;
    let parentID = null;

    for (let part of pathParts) {
        let collections = parentID 
            ? await Zotero.Collections.getAsync(parentID).then(c => c.getChildCollections())
            : await Zotero.Collections.getByLibrary(Zotero.Libraries.userLibraryID);
        
        currentCollection = collections.find(c => c.name === part);
        if (!currentCollection) return null; // Path broken
        parentID = currentCollection.id;
    }
    return currentCollection;
}

await migrateItemsByTag();
