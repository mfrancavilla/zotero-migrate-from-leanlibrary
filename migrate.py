import json
import os
import re
import shutil
from collections import defaultdict
import xml.etree.ElementTree as ET

def load_hierarchy_by_name(json_path="sciwheel_hierarchy.json"):
    """
    Reads the hierarchy JSON and maps subcollection names back to their 
    full parent-child path lists using structural text matching.
    """
    name_to_path = {}
    if not os.path.exists(json_path):
        print(f"⚠️ Warning: '{json_path}' not found. Defaulting fallback naming logic.")
        return name_to_path

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    def walk(node, current_path):
        node_name = node.get("name", "").strip()
        if not node_name:
            return
            
        new_path = current_path + [node_name]
        name_to_path[node_name.lower()] = new_path
            
        for child in node.get("children", []):
            walk(child, new_path)

    for root_node in data:
        walk(root_node, [])

    return name_to_path

def parse_ris_raw(path):
    entries = []
    current_lines = []
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
            if len(parts) == 2:
                values.append(parts[1].strip())
    return values

def clean_for_matching(text):
    if not text:
        return ""
    return re.sub(r'[^a-z0-9]', '', text.lower())

def escape_xml(text):
    if not text:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;")

def process_migration():
    input_path = "input.ris"
    pdf_dir = "files"

    if not os.path.exists(input_path):
        print(f"❌ Error: Cannot find {input_path}")
        return

    # 1. Protect input source
    shutil.copy2(input_path, "input_backed_up.ris")
    print("💾 Created safety copy: input_backed_up.ris")

    # 2. Compile text path lookup table
    name_to_path = load_hierarchy_by_name()

    # 3. Catalog local file pool
    pdf_pool = {}
    if os.path.exists(pdf_dir):
        for f in os.listdir(pdf_dir):
            if f.lower().endswith(".pdf"):
                base_name = os.path.splitext(f)[0]
                parts = base_name.split("-")
                title_snippet = "-".join(parts[:-5]).rstrip("-") if len(parts) > 5 else base_name
                normalized_snippet = clean_for_matching(title_snippet)
                if normalized_snippet:
                    pdf_pool[f] = normalized_snippet

    # 4. Parse RIS entries
    raw_entries = parse_ris_raw(input_path)
    
    migrated_items = []
    leftover_ris_entries = []
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

        # Sift out non-PDF entries
        if not matched_pdf:
            leftover_ris_entries.append(lines)
            continue

        item_id = f"item_{idx}"
        
        # Build raw metadata dict
        item = {
            "id": item_id,
            "title": title,
            "creators": [],
            "pdf_path": os.path.join(pdf_dir, matched_pdf),
            "pdf_name": title + ".pdf"
        }
        
        authors = extract_field_from_raw(lines, "AU")
        for author in authors:
            if "," in author:
                last, first = author.split(",", 1)
                item["creators"].append({"last": last.strip(), "first": first.strip()})
            else:
                item["creators"].append({"last": author, "first": ""})
                
        py_date = extract_field_from_raw(lines, "PY")
        if py_date: item["date"] = py_date[0]
        
        pub_title = extract_field_from_raw(lines, "T2") or extract_field_from_raw(lines, "JF")
        if pub_title: item["publication"] = pub_title[0]
        
        volume = extract_field_from_raw(lines, "VL")
        if volume: item["volume"] = volume[0]
        
        issue = extract_field_from_raw(lines, "IS")
        if issue: item["issue"] = issue[0]
        
        doi = extract_field_from_raw(lines, "DO")
        if doi: item["doi"] = doi[0]
        
        abstract = extract_field_from_raw(lines, "AB")
        if abstract: item["abstract"] = abstract[0]

        migrated_items.append(item)
        matched_count += 1

        # Resolve paths
        collection_tags = extract_field_from_raw(lines, "U1")
        assigned = False
        for tag in collection_tags:
            tag_lookup = tag.strip().lower()
            if tag_lookup in name_to_path:
                path_tuple = tuple(name_to_path[tag_lookup])
                active_paths_to_items[path_tuple].append(item_id)
                assigned = True
        
        if not assigned:
            fallback_label = collection_tags[0] if collection_tags else "Unsorted SciWheel Imports"
            active_paths_to_items[(fallback_label,)].append(item_id)
            
        del pdf_pool[matched_pdf]

    # 5. Generate Zotero-compliant XML RDF String
    print("Building Zotero RDF structural schema tree...")
    rdf = []
    rdf.append('<?xml version="1.0" encoding="utf-8"?>')
    rdf.append('<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"')
    rdf.append('         xmlns:z="http://www.zotero.org/namespaces/export#"')
    rdf.append('         xmlns:dc="http://purl.org/dc/elements/1.1/"')
    rdf.append('         xmlns:bib="http://purl.org/net/biblio#"')
    rdf.append('         xmlns:dcterms=\"http://purl.org/dc/terms/\">')

    # Add reference records
    for it in migrated_items:
        rdf.append(f'  <bib:Article rdf:about="#item_{it["id"]}">')
        rdf.append(f'    <dc:title>{escape_xml(it["title"])}</dc:title>')
        if "date" in it: rdf.append(f'    <dc:date>{escape_xml(it["date"])}</dc:date>')
        if "publication" in it: rdf.append(f'    <dcterms:isPartOf><bib:Journal><dc:title>{escape_xml(it["publication"])}</dc:title></bib:Journal></dcterms:isPartOf>')
        if "volume" in it: rdf.append(f'    <bib:volume>{escape_xml(it["volume"])}</bib:volume>')
        if "issue" in it: rdf.append(f'    <bib:number>{escape_xml(it["issue"])}</bib:number>')
        if "doi" in it: rdf.append(f'    <dc:identifier>DOI {escape_xml(it["doi"])}</dc:identifier>')
        if "abstract" in it: rdf.append(f'    <dcterms:abstract>{escape_xml(it["abstract"])}</dcterms:abstract>')
        
        # Add Authors
        if it["creators"]:
            rdf.append('    <bib:authors><rdf:Seq>')
            for auth in it["creators"]:
                rdf.append('      <rdf:li><foaf:Person xmlns:foaf="http://xmlns.com/foaf/0.1/">')
                rdf.append(f'        <foaf:surname>{escape_xml(auth["last"])}</foaf:surname>')
                rdf.append(f'        <foaf:givenname>{escape_xml(auth["first"])}</foaf:givenname>')
                rdf.append('      </foaf:Person></rdf:li>')
            rdf.append('    </rdf:Seq></bib:authors>')

        # Add File Attachment Link
        rdf.append(f'    <link:link xmlns:link="http://purl.org/rss/1.0/modules/link/" rdf:resource="{escape_xml(it["pdf_path"])}"/>')
        rdf.append('  </bib:Article>')
        
        # Define exact file attachment target metadata link block
        rdf.append(f'  <z:Attachment rdf:about="{escape_xml(it["pdf_path"])}">')
        rdf.append(f'    <z:itemType>attachment</z:itemType>')
        rdf.append(f'    <dc:title>{escape_xml(it["pdf_name"])}</dc:title>')
        rdf.append(f'    <z:linkMode>imported_file</z:linkMode>')
        rdf.append('  </z:Attachment>')

    # Map paths to Collections
    # Generate unified numeric subcollection IDs to preserve paths tracking
    path_to_col_id = {}
    for c_idx, path in enumerate(active_paths_to_items.keys()):
        path_to_col_id[path] = f"collection_{c_idx}"

    for path, item_ids in active_paths_to_items.items():
        col_id = path_to_col_id[path]
        folder_name = path[-1]
        
        rdf.append(f'  <z:Collection rdf:about="# {col_id}">')
        rdf.append(f'    <dc:title>{escape_xml(folder_name)}</dc:title>')
        
        # Map item documents straight inside this target subfolder node
        for item_id in item_ids:
            rdf.append(f'    <dcterms:hasPart rdf:resource="#item_{item_id}"/>')
            
        # Scan to see if this item acts as a structural parent to an active nested subpath
        for subpath, sub_col_id in path_to_col_id.items():
            if len(subpath) == len(path) + 1 and subpath[:-1] == path:
                rdf.append(f'    <dcterms:hasPart rdf:resource="# {sub_col_id}"/>')
                
        rdf.append('  </z:Collection>')

    rdf.append('</rdf:RDF>')

    # 6. Save Data Files
    with open("zotero_import.rdf", "w", encoding="utf-8") as f:
        f.write("\n".join(rdf))

    with open("remaining_no_pdf.ris", "w", encoding="utf-8") as f:
        for entry_lines in leftover_ris_entries:
            f.writelines(entry_lines)

    print("\n📊 Processing Results:")
    print(f" - Total original records: {len(raw_entries)}")
    print(f" - Migrating with PDFs:   {matched_count} (written to zotero_import.rdf)")
    print(f" - Leftover missing PDFs: {len(leftover_ris_entries)} (written to remaining_no_pdf.ris)")

if __name__ == "__main__":
    process_migration()