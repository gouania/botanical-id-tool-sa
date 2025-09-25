import google.generativeai as genai
from IPython.display import display, Markdown

MODEL_NAME = "models/gemini-2.5-flash"

def analyze_with_gemini(combined_descriptions, user_input, failed_list, species_metadata):
    """Sends the collected data to the Gemini AI for analysis."""
    display(Markdown("--- \\n" + "🤖 **Analyzing with Gemini AI...** (This may take 10-30 seconds, please wait)"))

    safety_settings = [{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
    metadata_summary = "\\n**Species Occurrence Data from GBIF (Top 10):**\\n" + "".join([f"- {sp['name']} (Family: {sp['family']}, Records: {sp['count']})\\n" for sp in species_metadata[:10]])
    failed_summary = f"**Species without local descriptions:** {', '.join(failed_list) if failed_list else 'None'}"
    if user_input and user_input.strip():
        prompt = f\"\"\"You are an expert field botanist. Your task is to identify a user's specimen based on their description, comparing it against a list of candidate species found in the area.
**USER'S SPECIMEN DESCRIPTION:**
{user_input}
**CANDIDATE SPECIES DATA (from local e-Flora):**
{combined_descriptions}
**CONTEXTUAL DATA:**
{metadata_summary}
{failed_summary}
**YOUR TASK:**
Provide a systematic identification analysis in this exact structure:
## 🎯 TOP CANDIDATES
List the 3 most likely species. For each, provide a **Match Confidence** percentage. Justify your choice by listing key **Matching Features** and any **Discrepancies**. Consider the GBIF record count as an indicator of how common a species is.
## 🔍 DIAGNOSTIC COMPARISON
Create a markdown table comparing the most important diagnostic features (e.g., leaves, flowers, habit) of the user's specimen against your top candidates.
## ⚠️ CRITICAL OBSERVATIONS & NEXT STEPS
What single, key feature would best confirm the identification? What should the user look for or photograph next to be certain?
\"\"\"
    else:
        prompt = f\"\"\"You are creating a practical field guide for botanists based on species known to occur in a specific area.
**AVAILABLE SPECIES DATA (from local e-Flora):**
{combined_descriptions}
**CONTEXTUAL DATA:**
{metadata_summary}
{failed_summary}
**YOUR TASK:**
Create a practical field guide using this exact structure, focusing only on the species for which descriptions were provided.
## 🌿 QUICK IDENTIFICATION MATRIX
Create a markdown table comparing the most diagnostic features (e.g., Habit, Leaf Shape, Flower Color, Habitat) for all available species. Use the GBIF record count to hint at which species are more commonly encountered.
## 🔑 SIMPLE DICHOTOMOUS KEY
Create a simple, practical dichotomous key to help differentiate between these species.
**CRITICAL FORMATTING RULES:**
1.  Each lead of a couplet (e.g., `1a` and `1b`) **MUST** be on its own, separate line. **NEVER** combine `...a` and `...b` leads onto the same line.
2.  Do not use dot leaders (`.......`).
3.  Use an arrow `->` to point to the result.
4.  Bold the species name or the "Go to" instruction.
**EXAMPLE OF PERFECT FORMAT:**
1a. Flowers yellow -> **Go to 2**
1b. Flowers white or pink -> **Go to 3**
2a. Leaves needle-like -> ***Species A***
2b. Leaves broad -> ***Species B***
3a. Shrub over 1m tall -> ***Species C***
3b. Shrub under 1m tall -> ***Species D***
## 👀 KEY FIELD MARKS
For each species, list the 2-3 most distinctive "at-a-glance" features that a botanist in the field could use for rapid identification.
\"\"\"
    try:
        model = genai.GenerativeModel(MODEL_NAME, safety_settings=safety_settings)
        response = model.generate_content(prompt)
        if response.parts:
            return response.text
        elif response.prompt_feedback and response.prompt_feedback.block_reason:
            reason = response.prompt_feedback.block_reason
            return f\"⚠️ **Gemini Analysis Error:** The request was blocked by the API's safety filters (Reason: **{reason}**). Try reducing `MAX_SPECIES_TO_PROCESS`.\"
        else:
            return \"⚠️ **Gemini Analysis Error:** The AI returned an empty response. This might be a temporary issue.\"
    except Exception as e:
        return f\"⚠️ **Gemini Analysis Error:** An exception occurred during the API call. **Details:** {str(e)}\"