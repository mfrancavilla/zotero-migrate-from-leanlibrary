import json
import os
import re
import shutil

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

def process_migration():
    input_path = "input.ris"
    pdf_dir = "files"
    output_path = "zotero_ready.ris"

    if not os.path.exists(input_path):
        print(f"❌ Error: Cannot find {input_path}")
        return

    shutil.copy2(input_path, "input_backed_up.ris")
    name_to_path = load_hierarchy_by_name()

    # Index available loose PDFs inside the files folder
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

    raw_entries = parse_ris_raw(input_path)
    output_lines = []
    matched_count = 0
    missing_count = 0

    for lines in raw_entries:
        titles = extract_field_from_raw(lines, "TI") or extract_field_from_raw(lines, "T1")
        title = titles[0] if titles else ""
        normalized_full_title = clean_for_matching(title)
        
        matched_pdf = None
        for filename, snippet in pdf_pool.items():
            if normalized_full_title.startswith(snippet) or snippet in normalized_full_title:
                matched_pdf = filename
                break

        # Reconstruct the reference block line by line
        new_entry_lines = []
        for line in lines:
            cleaned = line.strip()
            if cleaned.startswith("ER "):  # We inject fields right before the End Record marker
                
                # 1. Inject PDF attachment if located
                if matched_pdf:
                    # Construct an absolute-ready path using current system structure layout paths
                    full_pdf_path = os.path.abspath(os.path.join(pdf_dir, matched_pdf))
                    new_entry_lines.append(f"L1 - {full_pdf_path}\n")
                    matched_count += 1
                    del pdf_pool[matched_pdf] # Drop to prevent collision matching
                else:
                    missing_count += 1
                
                # 2. Inject structural folder paths into Zotero custom folder parameters 
                collection_tags = extract_field_from_raw(lines, "U1")
                for tag in collection_tags:
                    tag_lookup = tag.strip().lower()
                    if tag_lookup in name_to_path:
                        # Reconstruct explicit hierarchical folder structure mapping using standard Zotero structural delimiters
                        path_string = " > ".join(name_to_path[tag_lookup])
                        new_entry_lines.append(f"DP - {path_string}\n")
            
            new_entry_lines.append(line)
        
        output_lines.extend(new_entry_lines)

    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(output_lines)

    print(f"\n📊 Extraction Complete:\n - Total records processed: {len(raw_entries)}")
    print(f" - Successfully matched PDFs: {matched_count}")
    print(f" - Missing document links: {missing_count}")
    print(f" -> Saved clean file package directly to: {output_path}")

if __name__ == "__main__":
    process_migration()
