# Zotero Migration Suite for Lean Library
This suite of utilities automates the extraction, formatting, and organization of reference libraries migrating from Lean Library to Zotero. It ensures that active projects, folder structures, and archived data are accurately preserved and correctly categorized during the transition.

# Suite Components
* auto_exporter.js: An automation script run in the browser console to extract raw bibliographic data and folder structures from the Lean Library workspace interface.
* migrate.py: A Python engine that normalizes the raw browser export, standardizes citation keys, cleans digital object identifiers, and formats the output into a Zotero-compatible schema.
* zotero-migration-script.js: A Zotero API script that reads the parsed output to automatically reconstruct your folder hierarchy inside Zotero for active, unshared projects.
* zotero-handle-archived-leanlibrary-collections: A targeted script running within Zotero to explicitly capture, process, and organize the archived collections that are skipped by the primary active-project script.

# Prerequisites
* Python 3.8 or higher installed on your machine.
* Access to the Lean Library workspace account holding the targets for migration.
* The Zotero desktop application with the Run JavaScript utility enabled.

# Step-by-Step Execution Workflow
## Phase 1: Data Extraction
1. Navigate to your Lean Library workspace library page in your web browser.
2. Open the browser developer tools console.
3. Paste and run the contents of auto_exporter.js to download the raw data export file.

## Phase 2: File Normalization
Run the Python script from your terminal to convert the raw export file into an optimized schema ready for Zotero.
```bash
python migrate.py --input path/to/lean_library_export.json --output path/to/zotero_ready_import.json
```
## Phase 3: Primary Database Import
1. Launch the Zotero desktop application.
2. Select File from the application menu, choose Import, and select the file generated during Phase 2.

## Phase 4: Active Collection Organization
1. Go to Tools in the Zotero menu and open the Developer window, then choose Run JavaScript.
2. Load the contents of zotero-migration-script.js into the editor window.
3. Execute the script to sort active, unshared references back into their original nested folder hierarchies.

## Phase 5: Archived Collection Processing
1. While still inside the Zotero JavaScript execution environment, load the contents of zotero-handle-archived-leanlibrary-collections.
2. Run this script to parse out and organize the remaining archived data streams, ensuring no legacy reference material is left unsorted in the root library directory.
