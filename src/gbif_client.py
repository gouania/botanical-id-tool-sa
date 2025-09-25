import pygbif.species as gbif_species
import pygbif.occurrences as gbif_occ
import math
import time
from tqdm.auto import tqdm

CACHE = {'gbif_taxa': {}} # Cache for avoiding redundant GBIF calls

def get_species_list_from_gbif(latitude, longitude, radius_km, taxon_name, limit=1000):
    """
    Queries GBIF for a list of species recorded within a specific area,
    now supporting any taxonomic rank and restricted to the plant kingdom.
    """
    print(f"\\n📍 Searching GBIF for '{taxon_name}' within {radius_km}km of ({latitude:.4f}, {longitude:.4f})")
    cache_key = f"{taxon_name}_{latitude}_{longitude}_{radius_km}"
    if cache_key in CACHE['gbif_taxa']:
        print("   ✓ Using cached GBIF data for this location.")
        return CACHE['gbif_taxa'][cache_key]

    try:
        print(f"   > Looking up '{taxon_name}' in the GBIF backbone (Kingdom: Plantae)...")
        taxon_info = gbif_species.name_backbone(name=taxon_name, kingdom='Plantae', verbose=False)

        if 'usageKey' not in taxon_info or taxon_info.get('matchType') == 'NONE':
            print(f"   ❌ Taxon '{taxon_name}' could not be matched within Kingdom Plantae in the GBIF backbone.")
            print("      Please check the spelling or try a different taxonomic name.")
            return []

        found_name = taxon_info.get('scientificName', 'N/A')
        found_rank = taxon_info.get('rank', 'N/A').title()
        classification = " -> ".join(filter(None, [
            taxon_info.get('kingdom'), taxon_info.get('phylum'), taxon_info.get('class'),
            taxon_info.get('order'), taxon_info.get('family'), taxon_info.get('genus')
        ]))
        print(f"   ✓ GBIF matched '{found_name}' (Rank: {found_rank})")
        print(f"     Classification: {classification}")
        taxon_key = taxon_info['usageKey']

    except Exception as e:
        print(f"   ❌ An error occurred while contacting the GBIF backbone API: {e}")
        return []

    lat_offset = radius_km / 111.32
    lon_offset = radius_km / (111.32 * abs(math.cos(math.radians(latitude))))
    params = {'taxonKey': taxon_key, 'decimalLatitude': f'{latitude - lat_offset},{latitude + lat_offset}',
              'decimalLongitude': f'{longitude - lon_offset},{longitude + lon_offset}',
              'hasCoordinate': True, 'hasGeospatialIssue': False, 'limit': 300}

    all_records, offset = [], 0
    pbar = tqdm(total=limit, desc="   Fetching records", unit="rec", leave=False)
    while offset < limit:
        params['offset'] = offset
        try:
            response = gbif_occ.search(**params)
            batch = response.get('results', [])
            if not batch: break
            all_records.extend(batch)
            pbar.update(len(batch))
            if len(batch) < 300: break
            offset += len(batch)
            time.sleep(0.1)
        except Exception: break
    pbar.close()

    species_dict = {}
    for record in all_records:
        species_name = record.get('species')
        if species_name:
            if species_name not in species_dict:
                species_dict[species_name] = {'name': species_name, 'count': 0, 'family': record.get('family', 'Unknown')}
            species_dict[species_name]['count'] += 1
    species_list = sorted(species_dict.values(), key=lambda x: x['count'], reverse=True)

    print(f"\\n   ✓ Found {len(species_list)} unique species from {len(all_records)} records.")
    CACHE['gbif_taxa'][cache_key] = species_list
    return species_list