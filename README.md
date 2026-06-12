```markdown
# SciWheel-to-Zotero Hierarchical Migration Toolkit

This repository provides a reliable, two-part automated framework to migrate a massive reference library out of **SciWheel** and into **Zotero** while fully preserving:
1. **Multi-level nested collection folder hierarchies** (which standard `.ris` and `.bib` file exports flatten and destroy).
2. **Local PDF attachments**, safely cross-referenced, linked, and matched back to their respective database entries without duplication errors.

---

## 📋 The Migration Problem

When exporting references from SciWheel, the web platform completely detaches folders from documents or collapses nested collections into flat text labels hidden inside metadata tags (such as `U1` blocks). Furthermore, mass-downloading thousands of associated PDFs is restricted by the platform to small manual batch packages. 

This toolkit solves those limitations using a **Browser-Side Scraping/Automation Pipeline** combined with a **Local Python Data Engine**.

---

## 🛠️ Step 1: Extract Your Structural Folder Hierarchy

Before running any file exports, you must scrape your actual live nested folder configuration from the SciWheel dashboard.

1. Open your browser and log into your **SciWheel Dashboard**.
2. Open the **Web Developer Console** (`F12` or `Cmd + Option + K` on macOS).
3. Select the **Network Tab**, find any internal API request initializing your dashboard layout, and look at the response payload structure.
4. Alternatively, use standard DOM scraping or fetch requests to capture your hierarchy array, and save it in your local working directory exactly as `sciwheel_hierarchy.json`.

### Expected JSON Layout Sample:
```json
[
  {
    "name": "US",
    "id": "400886",
    "children": [
      {
        "name": "Intussusception",
        "id": "771207"
      },
      {
        "name": "Cardiac MR",
        "id": "717474"
      }
    ]
  }
]

```

---

## 🤖 Step 2: Automated Batch PDF Exporter

SciWheel restricts PDF bulk-downloads to 25 items per page. The JavaScript automation script below runs directly in your browser console, reading dynamic DOM elements to calculate the total library volume, auto-naming zip batches sequentially (`SciWheel_Batch_001.zip`), waiting for the server to compile each package, and advancing pages automatically.

### ⚠️ Critical Browser Configuration

Before executing, prevent your browser from stopping the script with file-save confirmation popups:

* Go to **Browser Settings > Downloads**.
* Toggle **OFF** *"Ask you where to save each file"* / *"Ask whether to open or save files"*.
* Force all downloads to point silently to your native system Downloads directory.

### Execution Script (`auto_exporter.js`)

Navigate to the first page of your reference list, paste this code into your **Developer Console**, and hit **Enter**:

```javascript
(async function() {
    let startPage = 1; // Change this if resuming a disconnected session
    const DELAY_BETWEEN_STEPS = 1200; 

    console.log(`🚀 Starting dynamic SciWheel Auto-Exporter from page ${startPage}...`);
    const sleep = ms => new Promise(res => setTimeout(res, ms));

    async function waitForElement(selector, timeout = 10000) {
        const startTime = Date.now();
        while (Date.now() - startTime < timeout) {
            const el = document.querySelector(selector);
            if (el && el.getBoundingClientRect().width > 0) return el;
            await sleep(100);
        }
        return null;
    }

    let batchNum = startPage;
    let totalPages = batchNum;

    while (batchNum <= totalPages) {
        const counterEl = document.querySelector('span.counter.ng-binding');
        if (counterEl) {
            const parsedTotal = parseInt(counterEl.textContent.replace(/[^0-9]/g, ''), 10);
            if (!isNaN(parsedTotal) && parsedTotal > 0) totalPages = parsedTotal;
        }

        console.log(`=== PROCESSING BATCH ${batchNum} OF ${totalPages} ===`);

        const pageInput = document.querySelector('input[data-test-id="page-number"]');
        if (pageInput) {
            const currentUIDashboardPage = parseInt(pageInput.value, 10);
            if (currentUIDashboardPage !== batchNum) batchNum = currentUIDashboardPage;
        }

        console.log("➡️ Selecting all items on page...");
        const selectAllBtn = await waitForElement('.select-all');
        if (!selectAllBtn) break;
        
        if (selectAllBtn.classList.contains('none')) {
            selectAllBtn.click();
            await sleep(DELAY_BETWEEN_STEPS);
        }

        console.log("➡️ Opening Action Menu...");
        const actionMenuBtn = await waitForElement('[data-test-id="open-selected-refs-contextmenu-bttn"]');
        if (!actionMenuBtn) break;
        actionMenuBtn.click();
        await sleep(1500); 

        console.log("➡️ Clicking 'Download PDFs...' options panel...");
        const downloadOption = await waitForElement('[data-test-id="download-selected-refs-pdfs-bttn"]');
        if (!downloadOption) {
            let fallbackFound = false;
            const elements = document.querySelectorAll('li');
            for (const el of elements) {
                if (el.textContent.includes("Download PDFs")) {
                    el.click();
                    fallbackFound = true;
                    break;
                }
            }
            if (!fallbackFound) break;
        } else {
            downloadOption.click();
        }
        
        console.log("➡️ Waiting for Download Modal...");
        const nameInput = await waitForElement('input.mdc-textfield__input');
        if (!nameInput) break;

        const customFileName = `SciWheel_Batch_${String(batchNum).padStart(3, '0')}`;
        nameInput.value = customFileName;
        nameInput.dispatchEvent(new Event('input', { bubbles: true }));
        await sleep(800);

        const submitBtn = document.querySelector('button[ng-click="exportReferences()"]');
        console.log(`💾 Triggering download package for: ${customFileName}`);
        submitBtn.click();
        await sleep(1500);

        console.log("⏳ SciWheel server compiling zip package. Waiting...");
        let attempts = 0;
        while (attempts < 90) { 
            const spans = Array.from(document.querySelectorAll('span'));
            const isPreparing = spans.some(el => el.textContent.includes("Preparing file for download"));
            if (!isPreparing) {
                console.log("✅ Download dispatched successfully!");
                break;
            }
            await sleep(1000);
            attempts++;
        }

        await sleep(2500); 

        console.log("➡️ Deselecting current page items...");
        if (selectAllBtn && !selectAllBtn.classList.contains('none')) {
            selectAllBtn.click();
            await sleep(DELAY_BETWEEN_STEPS);
        }

        if (batchNum < totalPages) {
            console.log("➡️ Navigating forward to next page index...");
            const nextArrow = document.querySelector('[data-test-id="arrow-next-button"]');
            if (nextArrow && !nextArrow.classList.contains('is-disabled')) {
                nextArrow.click();
                await sleep(5000); 
                batchNum++;        
            } else {
                break;
            }
        } else {
            console.log("🎉 ALL BATCHES EXPORTED SUCCESSFULLY!");
            break;
        }
    }
})();

```

---

## 🐍 Step 3: Reconstruct and Migrate to Zotero via Python

Standard Zotero JSON/CSL utilities do not support folder nesting or localized asset attachments during raw file imports. To bypass this limitations, the Python engine below processes your standard SciWheel `input.ris` export file, strings matches the text references, resolves structural paths, and outputs a compliant **Zotero RDF Schema (XML)** package.

### Local Directory Organization

Ensure your workspace directory layout is set up exactly like this before initializing the script:

```text
📁 Migration-Workspace/
│
├── 📄 migrate.py                # The script provided below
├── 📄 sciwheel_hierarchy.json  # Scraped hierarchy metadata map from Step 1
├── 📄 input.ris                # Your complete master reference export from SciWheel
└── 📁 files/                   # Unzip ALL your downloaded batches straight into here
    ├── StudyOnCardiology-2024.pdf
    └── PulmonaryImaging-2025.pdf

```

### Compiler Engine (`migrate.py`)

```python
import json
import os
import re
import shutil
from collections import defaultdict

def load_hierarchy_by_name(json_path="sciwheel_hierarchy.json"):
    name_to_path = {}
    if not os.path.exists(json_path):
        print(f"⚠️ Warning: '{json_path}' not found. Defaulting fallback naming logic.")
        return name_to_path

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    def walk(node, current_path):
        node_name = node.get("name", "").strip()
        if not node_name: return
        new_path = current_path + [node_name]
        name_to_path[node_name.lower()] = new_path
        for child in node.get("children", []):
            walk(child, new_path)

    for root_node in data:
        walk(root_node, [])
    return name_to_path

def parse_ris_raw(path):
    entries, current_lines = [], []
    with open(path, encoding="utf-8") as f:
        for line in f:
            current_lines.append(line)
            if line.strip().startswith("ER "):
                entries.append(current_lines)
                current_lines = []
    return entries

def extract_field_from_raw(raw_lines, tag_prefix):
    values = []
    for line in raw_lines:
        cleaned = line.strip()
        if cleaned.startswith(tag_prefix):
            parts = cleaned.split(" - ", 1)
            if len(parts) == 2: values.append(parts[1].strip())
    return values

def clean_for_matching(text):
    if not text: return ""
    return re.sub(r'[^a-z0-9]', '', text.lower())

def escape_xml(text):
    if not text: return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;")

def process_migration():
    input_path = "input.ris"
    pdf_dir = "files"

    if not os.path.exists(input_path):
        print(f"❌ Error: Cannot find {input_path}")
        return

    shutil.copy2(input_path, "input_backed_up.ris")
    name_to_path = load_hierarchy_by_name()

    pdf_pool = {}
    if os.path.exists(pdf_dir):
        for f in os.listdir(pdf_dir):
            if f.lower().endswith(".pdf"):
                base_name = os.path.splitext(f)[0]
                parts = base_name.split("-")
                title_snippet = "-".join(parts[:-5]).rstrip("-") if len(parts) > 5 else base_name
                normalized_snippet = clean_for_matching(title_snippet)
                if normalized_snippet: pdf_pool[f] = normalized_snippet

    raw_entries = parse_ris_raw(input_path)
    migrated_items, leftover_ris_entries = [], []
    active_paths_to_items = defaultdict(list)
    matched_count = 0

    for idx, lines in enumerate(raw_entries):
        titles = extract_field_from_raw(lines, "TI") or extract_field_from_raw(lines, "T1")
        title = titles[0] if titles else "Untitled Item"
        normalized_full_title = clean_for_matching(title)
        matched_pdf = None
        
        for filename, snippet in pdf_pool.items():
            if normalized_full_title.startswith(snippet) or snippet in normalized_full_title:
                matched_pdf = filename
                break

        if not matched_pdf:
            leftover_ris_entries.append(lines)
            continue

        item_id = f"item_{idx}"
        item = {"id": item_id, "title": title, "creators": [], "pdf_path": os.path.join(pdf_dir, matched_pdf), "pdf_name": title + ".pdf"}
        
        authors = extract_field_from_raw(lines, "AU")
        for author in authors:
            if "," in author:
                last, first = author.split(",", 1)
                item["creators"].append({"last": last.strip(), "first": first.strip()})
            else:
                item["creators"].append({"last": author, "first": ""})
                
        for tag, key in [("PY", "date"), ("T2", "publication"), ("JF", "publication"), ("VL", "volume"), ("IS", "issue"), ("DO", "doi"), ("AB", "abstract")]:
            val = extract_field_from_raw(lines, tag)
            if val: item[key] = val[0]

        migrated_items.append(item)
        matched_count += 1

        collection_tags = extract_field_from_raw(lines, "U1")
        assigned = False
        for tag in collection_tags:
            tag_lookup = tag.strip().lower()
            if tag_lookup in name_to_path:
                active_paths_to_items[tuple(name_to_path[tag_lookup])].append(item_id)
                assigned = True
        
        if not assigned:
            fallback = collection_tags[0] if collection_tags else "Unsorted SciWheel Imports"
            active_paths_to_items[(fallback,)].append(item_id)
            
        del pdf_pool[matched_pdf]

    rdf = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<rdf:RDF xmlns:rdf="[http://www.w3.org/1999/02/22-rdf-syntax-ns#](http://www.w3.org/1999/02/22-rdf-syntax-ns#)"',
        '         xmlns:z="[http://www.zotero.org/namespaces/export#](http://www.zotero.org/namespaces/export#)"',
        '         xmlns:dc="[http://purl.org/dc/elements/1.1/](http://purl.org/dc/elements/1.1/)"',
        '         xmlns:bib="[http://purl.org/net/biblio#](http://purl.org/net/biblio#)"',
        '         xmlns:dcterms="[http://purl.org/dc/terms/](http://purl.org/dc/terms/)">'
    ]

    for it in migrated_items:
        rdf.append(f'  <bib:Article rdf:about="#item_{it["id"]}">')
        rdf.append(f'    <dc:title>{escape_xml(it["title"])}</dc:title>')
        if "date" in it: rdf.append(f'    <dc:date>{escape_xml(it["date"])}</dc:date>')
        if "publication" in it: rdf.append(f'    <dcterms:isPartOf><bib:Journal><dc:title>{escape_xml(it["publication"])}</dc:title></bib:Journal></dcterms:isPartOf>')
        if "volume" in it: rdf.append(f'    <bib:volume>{escape_xml(it["volume"])}</bib:volume>')
        if "issue" in it: rdf.append(f'    <bib:number>{escape_xml(it["issue"])}</bib:number>')
        if "doi" in it: rdf.append(f'    <dc:identifier>DOI {escape_xml(it["doi"])}</dc:identifier>')
        if "abstract" in it: rdf.append(f'    <dcterms:abstract>{escape_xml(it["abstract"])}</dcterms:abstract>')
        
        if it["creators"]:
            rdf.append('    <bib:authors><rdf:Seq>')
            for auth in it["creators"]:
                rdf.append('      <rdf:li><foaf:Person xmlns:foaf="[http://xmlns.com/foaf/0.1/](http://xmlns.com/foaf/0.1/)">')
                rdf.append(f'        <foaf:surname>{escape_xml(auth["last"])}</foaf:surname>')
                rdf.append(f'        <foaf:givenname>{escape_xml(auth["first"])}</foaf:givenname>')
                rdf.append('      </foaf:Person></rdf:li>')
            rdf.append('    </rdf:Seq></bib:authors>')

        rdf.append(f'    <link:link xmlns:link="[http://purl.org/rss/1.0/modules/link/](http://purl.org/rss/1.0/modules/link/)" rdf:resource="{escape_xml(it["pdf_path"])}"/>')
        rdf.append('  </bib:Article>')
        rdf.append(f'  <z:Attachment rdf:about="{escape_xml(it["pdf_path"])}">')
        rdf.append(f'    <z:itemType>attachment</z:itemType>')
        rdf.append(f'    <dc:title>{escape_xml(it["pdf_name"])}</dc:title>')
        rdf.append(f'    <z:linkMode>imported_file</z:linkMode>')
        rdf.append('  </z:Attachment>')

    path_to_col_id = {path: f"collection_{c_idx}" for c_idx, path in enumerate(active_paths_to_items.keys())}

    for path, item_ids in active_paths_to_items.items():
        col_id = path_to_col_id[path]
        rdf.append(f'  <z:Collection rdf:about="# {col_id}">')
        rdf.append(f'    <dc:title>{escape_xml(path[-1])}</dc:title>')
        for item_id in item_ids:
            rdf.append(f'    <dcterms:hasPart rdf:resource="#item_{item_id}"/>')
        for subpath, sub_col_id in path_to_col_id.items():
            if len(subpath) == len(path) + 1 and subpath[:-1] == path:
                rdf.append(f'    <dcterms:hasPart rdf:resource="# {sub_col_id}"/>')
        rdf.append('  </z:Collection>')

    rdf.append('</rdf:RDF>')

    with open("zotero_import.rdf", "w", encoding="utf-8") as f: f.write("\n".join(rdf))
    with open("remaining_no_pdf.ris", "w", encoding="utf-8") as f:
        for entry_lines in leftover_ris_entries: f.writelines(entry_lines)

    print(f"\n📊 Processing Complete:\n - Total records: {len(raw_entries)}\n - Migrated: {matched_count} -> zotero_import.rdf\n - Missing PDFs: {len(leftover_ris_entries)} -> remaining_no_pdf.ris")

if __name__ == "__main__":
    process_migration()

```

---

## 📥 Step 4: Import Into Zotero

1. Open desktop **Zotero**.
2. Select **File > Import** from the top menu system.
3. Click **"A file (BibTeX, RIS, Zotero RDF, etc.)"** and choose Next.
4. Open your generated workspace directory and select **`zotero_import.rdf`**.

Zotero will natively map the XML namespaces to construct nested multi-level collection folders, map your reference entries to their specific targets, and embed the local document attachments into its database repository. Any references currently missing a local document are safely siloed inside `remaining_no_pdf.ris` for future processing batches.
