import os
import re
import uuid
from gtts import gTTS

ENGLISH_TO_TELUGU_MAP = {
    # Full Action Sentences
    "Scout leaves for secondary symptom signs or insect pests.": "ఆకుల అడుగు భాగాన్ని మరియు కాండాన్ని నిశితంగా పరిశీలించండి.",
    "Ensure adequate drainage and avoid over-watering.": "పొలంలో నీరు నిల్వ ఉండకుండా తగినంత డ్రైనేజీ ఏర్పాటు చేయండి.",
    "Take additional photos under bright, clear daylight and resubmit.": "మంచి వెలుతురు ఉన్న సమయంలో ఆకు ఫోటోను స్పష్టంగా తీసి మళ్లీ విశ్లేషించండి.",
    "Inspect lower and middle foliage for visible lesion progression.": "కింది మరియు మధ్య ఆకులపై వ్యాధి మచ్చల వ్యాప్తిని పరిశీలించండి.",
    "Ensure drip irrigation or morning watering to prevent prolonged evening leaf moisture.": "సాయంత్రం వేళల్లో ఆకులపై తేమ నిల్వ ఉండకుండా ఉదయపు వేళల్లో మాత్రమే నీరు పారించండి.",
    "Maintain adequate plant spacing to encourage canopy ventilation.": "మొక్కల మధ్య తగినంత గాలి వెలుతురు ప్రసరించేలా ప్లాంట్ స్పేసింగ్ నిర్వహించండి.",
    "Consult local extension officer or agricultural authority for registered regional treatments.": "అధీకృత రసాయన మందుల కోసం స్థానిక వ్యవసాయ విస్తరణ అధికారిని సంప్రదించండి.",
    "Avoid overhead sprinkler irrigation during high humidity periods.": "అధిక తేమ ఉన్న సమయాల్లో పైనుండి నీరు చిలకరించడం నివారించండి.",
    "Do not apply unverified chemical sprays without checking local product labels.": "స్థానిక ఉత్పత్తి లేబుల్స్ పరిశీలించకుండా ధృవీకరించని రసాయనాలను స్ప్రే చేయకండి.",
    "Low confidence screening result. Safe general crop care recommended.": "ఆకు వ్యాధిని ఖచ్చితంగా గుర్తించడానికి తగినంత నమ్మకం లేదు. సాధారణ పంట సంరక్షణ పాటించండి.",
    "The model cannot confirm a specific disease class with sufficient certainty.": "మోడల్ వ్యాధి రకాన్ని ఖచ్చితంగా నిర్ధారించలేకపోతోంది.",
    "No verified chemical pesticide recommendation is available for unconfirmed screening results. Consult your local agricultural officer.": "ఈ వ్యాధికి నిర్దిష్ట పురుగుమందు సూచన ఇవ్వడానికి ధృవీకరించిన సమాచారం అందుబాటులో లేదు. స్థానిక వ్యవసాయ అధికారిని సంప్రదించండి.",

    # Crops
    "Tomato": "టమాటా",
    "Rice": "వరి",
    "Corn": "మొక్కజొన్న",
    "Maize": "మొక్కజొన్న",
    "Potato": "బంగాళాదుంప",
    "Cotton": "ప్రత్తి",
    "Chilli": "మిరప",
    "Chili": "మిరప",
    "Wheat": "గోధుమ",

    # Diseases
    "Early Blight": "ప్రారంభ ఆకు ఎండుతెగులు",
    "Late Blight": "లేట్ బ్లైట్ ఎండుతెగులు",
    "Leaf Mold": "ఆకు బూజు తెగులు",
    "Septoria Leaf Spot": "సెప్టోరియా ఆకు మచ్చల తెగులు",
    "Spider Mites": "ఎర్ర నల్లి తెగులు",
    "Target Spot": "టార్గెట్ స్పాట్ మచ్చల తెగులు",
    "Yellow Leaf Curl Virus": "ఆకు ముడుత వైరస్ తెగులు",
    "Mosaic Virus": "మోజాయిక్ వైరస్ తెగులు",
    "Bacterial Spot": "బ్యాక్టీరియల్ మచ్చల తెగులు",
    "Healthy": "ఆరోగ్యకరమైన పంట",
    "Blast": "అగ్గి తెగులు",
    "Brown Spot": "గోధుమ రంగు మచ్చల తెగులు",
    "Common Rust": "తుప్పు తెగులు",
    "Gray Leaf Spot": "బూడిద రంగు మచ్చ తెగులు",
    "Northern Leaf Blight": "నార్తర్న్ ఆకు ఎండుతెగులు",
    "Low Confidence": "నమ్మకం తక్కువ",

    # Common agronomic terms & words
    "scout": "పరిశీలించండి",
    "scouting": "పరిశీలించడం",
    "leaves": "ఆకులు",
    "leaf": "ఆకు",
    "pests": "తెగుళ్లు",
    "pest": "పురుగు",
    "insects": "కీటకాలు",
    "insect": "కీటకం",
    "drainage": "నీటి పారుదల",
    "watering": "నీరు పారించడం",
    "water": "నీరు",
    "over-watering": "అధిక నీటి పారుదల",
    "photos": "ఫోటోలు",
    "photo": "ఫోటో",
    "chemical": "రసాయన",
    "chemicals": "రసాయనాలు",
    "sprays": "పిచికారీ",
    "spray": "స్ప్రే",
    "pesticides": "పురుగుమందులు",
    "pesticide": "పురుగుమందు",
    "fungicides": "శిలీంధ్ర నాశినులు",
    "fungicide": "శిలీంధ్ర నాశిని",
    "fertilizer": "ఎరువులు",
    "fertilizers": "ఎరువులు",
    "humidity": "తేమ",
    "temperature": "ఉష్ణోగ్రత",
    "weather": "వాతావరణం",
    "crop": "పంట",
    "crops": "పంటలు",
    "disease": "వ్యాధి",
    "diseases": "వ్యాధులు",
    "health": "ఆరోగ్యం",
    "confidence": "నమ్మక స్థాయి",
    "officer": "వ్యవసాయ అధికారి",
    "expert": "వ్యవసాయ నిపుణుడు",
    "avoid": "నివారించండి",
    "treatment": "చికిత్స",
    "notice": "హెచ్చరిక",
    "warning": "నోటీసు",
    "actions": "చర్యలు",
    "action": "చర్య"
}

def clean_text_for_telugu_tts(text):
    if not text:
        return ""
    
    # First, replace full known English phrase matches
    for eng, tel in ENGLISH_TO_TELUGU_MAP.items():
        if " " in eng:
            text = re.sub(re.escape(eng), tel, text, flags=re.IGNORECASE)
            
    # Second, replace individual English words
    for eng, tel in ENGLISH_TO_TELUGU_MAP.items():
        if " " not in eng:
            text = re.sub(r'\b' + re.escape(eng) + r'\b', tel, text, flags=re.IGNORECASE)

    # Strip any remaining ASCII English letters (A-Z, a-z) so gTTS speaks ONLY Telugu
    text = re.sub(r'[A-Za-z]', '', text)
    # Remove special punctuation parens, brackets, quotes
    text = re.sub(r'[\(\)\[\]\{\}"\']', '', text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def make_telugu_audio(advisory_telugu, output_dir="outputs"):
    """
    Generates pure Telugu speech MP3 audio from Telugu advisory using gTTS.
    Ensures 100% pure Telugu pronunciation without any English words.
    """
    os.makedirs(output_dir, exist_ok=True)
    filename = f"advisory_telugu_{uuid.uuid4().hex[:8]}.mp3"
    filepath = os.path.join(output_dir, filename)

    try:
        if isinstance(advisory_telugu, dict):
            summary = advisory_telugu.get("summary", "")
            actions = advisory_telugu.get("actions", [])
            actions_text = " ".join(actions) if isinstance(actions, list) else str(actions)
            treatment = advisory_telugu.get("treatment", "")
            
            full_text = f"పంట ఆరోగ్య సమాచారం. {summary}. ఇప్పుడు చేయవలసిన పనులు: {actions_text}."
            if treatment:
                full_text += f" చికిత్స వివరాలు: {treatment}"
        else:
            full_text = str(advisory_telugu)

        # Sanitize text to ensure 100% pure Telugu characters for gTTS
        pure_telugu_text = clean_text_for_telugu_tts(full_text)

        if not pure_telugu_text.strip() or len(pure_telugu_text.strip()) < 5:
            pure_telugu_text = "పంట ఆరోగ్య సలహా సమాచారం సిద్ధంగా ఉంది. దయచేసి పొలంలో ఆకుల పరిస్థితిని రోజూ గమనించండి."

        tts = gTTS(text=pure_telugu_text, lang="te", slow=False)
        tts.save(filepath)
        print(f"[TTS Tool] Pure Telugu MP3 audio successfully generated: {filepath}")
        return filepath
    except Exception as e:
        print(f"[TTS Tool] Warning: Telugu TTS generation encountered an issue: {e}")
        return None

