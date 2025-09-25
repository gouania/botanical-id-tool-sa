import pandas as pd
from tqdm.auto import tqdm
from src.gbif_client import get_species_list_from_gbif
from src.gemini_client import analyze_with_gemini

EFLORA_DATA = None

def set_eflora_data(data):
    """Sets the global e-Flora data."""
    global EFLORA_DATA
    EFLORA_DATA = data

def format_species_name(name):
    """Clean and format species names to 'Genus species' for matching."""
    if not name: return None
    parts = name.split()
    return f"{parts[0]} {parts[1]}" if len(parts) >= 2 else name

def get_localeflora_description(scientific_name, eflora_data):
    """Retrieves botanical descriptions from the pre-loaded e-Flora DataFrame."""
    if scientific_name not in eflora_data.index:
        return (False, "Species not found in local database.")
    record = eflora_data.loc[scientific_name]
    descriptions = record.get('descriptions')
    vernacular_names = record.get('vernacularName')
    full_scientific_name = record.get('scientificName')
    if not isinstance(descriptions, dict): return (False, "No description data available.")
    priority_sections = ["Morphological description", "Diagnostic characters", "Habitat", "Distribution", "Morphology", "Diagnostic"]
    extracted_data = [f"**Scientific Name:** {full_scientific_name}"]
    if isinstance(vernacular_names, list) and not pd.isna(vernacular_names).all():
        valid_names = [name for name in vernacular_names if pd.notna(name)]
        if valid_names: extracted_data.append(f"**Common Names:** {', '.join(valid_names)}")
    for section in priority_sections:
        if section in descriptions and pd.notna(descriptions[section]):
            extracted_data.append(f"**{section}:**\\n{descriptions[section]}")
    return (True, "\\n\\n".join(extracted_data)) if len(extracted_data) > 2 else (False, "No relevant sections found.")

def run_analysis(latitude, longitude, radius_km, taxon_name, user_input, max_species=20):
    """The main workflow that orchestrates data collection and analysis."""
    if EFLORA_DATA is None:
        print("\\n❌ e-Flora data not loaded. Please load the data first.")
        return None, None, None, None
    gbif_species_list = get_species_list_from_gbif(latitude, longitude, radius_km, taxon_name)
    if not gbif_species_list:
        print("\\n❌ No species found in the specified area according to GBIF.")
        return None, None, None, None
    print(f"\\n📚 Collecting local e-Flora descriptions for up to {max_species} most common species...")
    successful_lookups, failed_species = [], []
    species_to_process = gbif_species_list[:max_species]
    for species_info in tqdm(species_to_process, desc="   Processing species", unit="taxa"):
        name = species_info['name']
        clean_name = format_species_name(name)
        success, desc = get_localeflora_description(clean_name, EFLORA_DATA)
        if success:
            successful_lookups.append({'name': name, 'description': desc, 'family': species_info['family'], 'gbif_count': species_info['count']})
        else:
            failed_species.append(name)
    print("\\n" + "─" * 60 + "\\n📊 Data Collection Summary:")
    print(f"   • Descriptions found: {len(successful_lookups)} / {len(species_to_process)}")
    if not successful_lookups:
        print("\\n⚠️ No descriptions found for any of the most common species. Cannot perform analysis.")
        return None, None, failed_species, gbif_species_list
    combined_descriptions = "\\n\\n".join([f"### {s['name']} (Family: {s['family']}, GBIF Records in Area: {s['gbif_count']})\\n{s['description']}" for s in successful_lookups])
    analysis_result = analyze_with_gemini(combined_descriptions, user_input, failed_species, gbif_species_list)
    return analysis_result, successful_lookups, failed_species, gbif_species_list