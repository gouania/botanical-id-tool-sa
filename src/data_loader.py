import os
import pandas as pd
from tqdm.auto import tqdm

# --- 1. Define Public Data URLs ---

# --- Files on GitHub (for small files) ---
GITHUB_BASE_URL = "https://raw.githubusercontent.com/Gouania/botanical-id-tool-sa/main/"

# --- File on Google Drive (for the large description.txt) ---
FILE_ID = "1eqLf_WrdZOZj6yxxq0018feKuJIqIQcc"
DESCRIPTION_FILE_URL = f"https://drive.google.com/uc?export=download&id={FILE_ID}"

FILES_TO_DOWNLOAD = {
    "taxon.txt": GITHUB_BASE_URL + "taxon.txt",
    "vernacularname.txt": GITHUB_BASE_URL + "vernacularname.txt",
    "description.txt": DESCRIPTION_FILE_URL
}

def download_data_files():
    """Downloads the required data files from public repositories."""
    print("📂 Downloading required e-Flora data files...")
    for filename, url in FILES_TO_DOWNLOAD.items():
        print(f"   -> Downloading {filename}...")
        if filename == "description.txt":
            os.system(f"wget -q --load-cookies /tmp/cookies.txt \"https://docs.google.com/uc?export=download&confirm=$(wget --quiet --save-cookies /tmp/cookies.txt --keep-session-cookies --no-check-certificate 'https://docs.google.com/uc?export=download&id={FILE_ID}' -O- | sed -rn 's/.*confirm=([0-9A-Za-z_]+).*/\\1\\n/p')&id={FILE_ID}\" -O {filename} && rm -rf /tmp/cookies.txt")
        else:
            os.system(f"wget -q -O {filename} {url}")

def load_dwca_data_from_local():
    """
    Loads the downloaded text files into a pandas DataFrame.
    """
    if not all(os.path.exists(f) for f in FILES_TO_DOWNLOAD.keys()):
        print("\\n❌ ERROR: One or more data files failed to download. Please run the download function again.")
        return None

    try:
        print("\\n🔄 Processing downloaded files... (This may take a moment)")
        taxa_df = pd.read_csv('taxon.txt', sep='\\t', header=0, usecols=['id', 'scientificName'], dtype={'id': str})
        desc_df = pd.read_csv('description.txt', sep='\\t', header=0, usecols=['id', 'description', 'type'], dtype={'id': str})
        vernacular_df = pd.read_csv('vernacularname.txt', sep='\\t', header=0, usecols=[0, 1], names=['taxonID', 'vernacularName'], dtype={'id': str})

        taxa_df.rename(columns={'id': 'taxonID'}, inplace=True)
        desc_df.rename(columns={'id': 'taxonID'}, inplace=True)
        taxa_df['cleanScientificName'] = taxa_df['scientificName'].apply(lambda x: ' '.join(str(x).split()[:2]))
        desc_agg = desc_df.groupby('taxonID').apply(lambda x: x.set_index('type')['description'].to_dict()).reset_index(name='descriptions')
        vernacular_agg = vernacular_df.groupby('taxonID')['vernacularName'].apply(lambda x: list(set(x))).reset_index()
        eflora_data = pd.merge(taxa_df, desc_agg, on='taxonID', how='left')
        eflora_data = pd.merge(eflora_data, vernacular_agg, on='taxonID', how='left')
        eflora_data.set_index('cleanScientificName', inplace=True)

        if eflora_data.index.has_duplicates:
            print(f"   ⚠️ Found {eflora_data.index.duplicated().sum()} duplicate names after cleaning. Keeping first entry for each.")
            eflora_data = eflora_data[~eflora_data.index.duplicated(keep='first')]

        print(f"\\n✅ Successfully loaded and processed data for {len(eflora_data)} taxa.")
        return eflora_data

    except Exception as e:
        print(f"\\n❌ An error occurred during data loading: {e}")
        return None