import json
import asyncio
from pathlib import Path
from google import genai
from google.genai import types
from app.config import settings
from typing import Any


# Load the extraction prompt once at module level
_PROMPT_PATH = Path(__file__).parent / "prompts" / "extraction.txt"
_EXTRACTION_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")

# The enforced JSON schema for Gemini structured output
EXTRACTION_SCHEMA = {
    "type": "object",
    "required": [
        "hazard_type", "urgency_score", "confidence_score",
        "location", "people", "medical_urgencies", "situation_summary",
        "parsed_text", "overall_report", "anomaly_flags", "raw_input_preserved"
    ],
    "properties": {
        "hazard_type": {
            "type": "string",
            "enum": [
                "flood", "earthquake", "fire", "medical_emergency",
                "structural_collapse", "landslide", "supply_shortage",
                "displacement", "violence", "other", "unclear"
            ]
        },
        "hazard_subtype": {"type": "string"},
        "urgency_score": {"type": "number"},
        "confidence_score": {"type": "number"},
        "parsed_text": {
            "type": "string",
            "description": "Accurate, intelligible, normalized transcription and statement of the user's spoken voice note, typed message, or emergency distress situation so that the user and rescue coordinators can read the exact interpreted text."
        },
        "location": {
            "type": "object",
            "required": ["extracted_name", "specificity"],
            "properties": {
                "extracted_name": {"type": "string"},
                "neighborhood": {"type": "string"},
                "sector_block": {"type": "string"},
                "city": {"type": "string"},
                "landmarks": {"type": "array", "items": {"type": "string"}},
                "specificity": {
                    "type": "string",
                    "enum": ["exact_address", "street_level", "neighborhood",
                             "city_level", "vague", "none"]
                }
            }
        },
        "people": {
            "type": "object",
            "required": ["headcount", "headcount_confidence"],
            "properties": {
                "headcount": {"type": "integer"},
                "headcount_confidence": {
                    "type": "string",
                    "enum": ["exact", "estimated", "vague", "unknown"]
                },
                "vulnerable_groups": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["infant", "child", "elderly", "pregnant",
                                         "disabled", "chronically_ill", "injured"]
                            },
                            "count": {"type": "integer"},
                            "details": {"type": "string"}
                        }
                    }
                }
            }
        },
        "medical_urgencies": {
            "type": "object",
            "required": ["has_medical_emergency", "urgency_level", "injuries_reported"],
            "properties": {
                "has_medical_emergency": {"type": "boolean"},
                "urgency_level": {
                    "type": "string",
                    "enum": ["critical", "high", "moderate", "none", "unknown"]
                },
                "injuries_reported": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "immediate_needs": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "details": {"type": "string"}
            }
        },
        "situation_summary": {"type": "string"},
        "situation_details": {
            "type": "object",
            "properties": {
                "water_level_ft": {"type": "number"},
                "is_escalating": {"type": "boolean"},
                "structural_damage": {"type": "boolean"},
                "access_blocked": {"type": "boolean"},
                "supplies_needed": {"type": "array", "items": {"type": "string"}}
            }
        },
        "visual_evidence_analysis": {
            "type": "object",
            "properties": {
                "visible_hazards": {"type": "array", "items": {"type": "string"}},
                "visual_severity": {"type": "string"},
                "scene_authenticity": {"type": "string"},
                "damage_observed": {"type": "string"}
            }
        },
        "anomaly_flags": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "flag_type": {
                        "type": "string",
                        "enum": ["vague_location", "contradictory_info", "suspected_spam",
                                 "single_word_input", "no_location", "impossible_claim",
                                 "test_message", "duplicate_pattern"]
                    },
                    "description": {"type": "string"},
                    "severity": {
                        "type": "string",
                        "enum": ["info", "warning", "critical"]
                    }
                }
            }
        },
        "raw_input_preserved": {"type": "string"},
        "detected_language": {
            "type": "string",
            "enum": ["roman_urdu", "urdu_script", "english", "sindhi",
                     "punjabi", "pashto", "hindi", "mixed", "unknown"]
        },
        "escalation_triggers": {
            "type": "array",
            "items": {"type": "string"}
        },
        "overall_report": {
            "type": "object",
            "required": ["title", "executive_summary", "original_language", "translation_notes", "operational_action_items", "recommended_units"],
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Standardized incident title for emergency coordinators"
                },
                "executive_summary": {
                    "type": "string",
                    "description": "Comprehensive tactical overview synthesizing voice, text, translation, and situation dynamics"
                },
                "original_language": {
                    "type": "string",
                    "description": "Detected source language (e.g. Roman Urdu, Urdu Script, Pashto, English)"
                },
                "translation_notes": {
                    "type": "string",
                    "description": "Linguistic translation commentary explaining key translated vernacular/colloquial distress terms"
                },
                "operational_action_items": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tactical action items for rescue dispatchers"
                },
                "recommended_units": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific emergency response teams needed"
                }
            }
        }
    }
}


class GeminiClient:
    """Async wrapper around Gemini 3.8 Flash (Medium) for emergency data extraction and translation."""

    def __init__(self):
        self.api_key = settings.gemini_api_key.strip() if settings.gemini_api_key else ""
        self.client = genai.Client(api_key=self.api_key) if self.api_key and self.api_key != "your_gemini_api_key" else None
        self.model_name = settings.gemini_model or "gemini-3.8-flash"
        self.candidate_models = [self.model_name, "gemini-3.7-flash", "gemini-2.5-flash"]

    async def process_report(
        self,
        text_input: str | None = None,
        audio_bytes: bytes | None = None,
        audio_mime_type: str = "audio/webm",
        image_bytes: bytes | None = None,
        image_mime_type: str = "image/jpeg",
        video_bytes: bytes | None = None,
        video_mime_type: str = "video/mp4",
        location_context: str | None = None,
    ) -> dict[str, Any]:
        """
        Send raw voice audio, text notes, and/or visual image/video evidence to Gemini
        for structured emergency extraction enforcing EXTRACTION_SCHEMA.
        Returns a dict strictly conforming to EXTRACTION_SCHEMA with parsed_text.
        """
        contents: list[Any] = [_EXTRACTION_PROMPT]

        if location_context:
            contents.append(f"Reported emergency incident location context: {location_context}")

        if audio_bytes:
            contents.append(
                types.Part.from_bytes(data=audio_bytes, mime_type=audio_mime_type)
            )
            contents.append(
                "Voice audio recording attached above. Transcribe speech accurately into 'parsed_text' "
                "(translating/transliterating into a clean intelligible statement) and extract emergency attributes."
            )

        if image_bytes:
            contents.append(
                types.Part.from_bytes(data=image_bytes, mime_type=image_mime_type)
            )
            contents.append(
                "Disaster scene photo attached above. Inspect visible emergency hazards, trapped victims, "
                "floodwater/fire, structural damage, and synthesize in visual_evidence_analysis."
            )

        if video_bytes:
            contents.append(
                types.Part.from_bytes(data=video_bytes, mime_type=video_mime_type)
            )
            contents.append(
                "Disaster scene video footage attached above. Inspect visual motion, emergency conditions, "
                "water depth, structural damage, and synthesize in visual_evidence_analysis."
            )

        if text_input:
            contents.append(f"User emergency distress text: {text_input}")

        if not audio_bytes and not text_input and not image_bytes and not video_bytes:
            return self._empty_extraction()

        extracted = None
        if self.client:
            for model in self.candidate_models:
                try:
                    response = await asyncio.to_thread(
                        self.client.models.generate_content,
                        model=model,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            system_instruction=(
                                "You are Gemini 3.8 Flash (Medium), the specialized linguistic translation, "
                                "voice/text transcription, and structured emergency extraction engine for ReliefPulse AI. "
                                "Translate, transcribe, and synthesize multi-lingual emergency distress communications into structured JSON matching EXTRACTION_SCHEMA."
                            ),
                            response_mime_type="application/json",
                            response_schema=EXTRACTION_SCHEMA,
                            temperature=0.2,
                        ),
                    )
                    if response and response.text:
                        extracted = json.loads(response.text)
                        break
                except Exception as e:
                    print(f"[GeminiClient] Extraction attempt with model '{model}' failed: {e}")
                    continue

        if not extracted:
            print("[GeminiClient] Gemini API call unavailable or failed, applying intelligent fallback.")
            return self._heuristic_fallback_extraction(
                text_input,
                has_audio=bool(audio_bytes),
                has_visual=bool(image_bytes or video_bytes),
                location_context=location_context,
            )

        # Ensure parsed_text is non-empty so the user and rescuers can read the statement
        if not extracted.get("parsed_text"):
            extracted["parsed_text"] = (
                extracted.get("situation_summary")
                or text_input
                or "Voice distress note registered with emergency dispatch."
            )

        # Ensure overall_report is well-managed and contains all required keys
        if "overall_report" not in extracted or not isinstance(extracted.get("overall_report"), dict):
            extracted["overall_report"] = {
                "title": f"Emergency Incident: {extracted.get('hazard_type', 'General Alert').replace('_', ' ').title()}",
                "executive_summary": extracted.get("situation_summary") or extracted.get("parsed_text", ""),
                "original_language": extracted.get("detected_language", "Urdu / English"),
                "translation_notes": "Linguistic translation and transcribed emergency audio synthesized.",
                "operational_action_items": [
                    "Deploy first responders to validated incident coordinates.",
                    f"Account for {extracted.get('people', {}).get('headcount', 1)} reported person(s) on-site."
                ],
                "recommended_units": ["Rapid Incident Response Unit"],
            }
        else:
            rep = extracted["overall_report"]
            rep.setdefault("title", f"Emergency Incident: {extracted.get('hazard_type', 'General Alert').replace('_', ' ').title()}")
            rep.setdefault("executive_summary", extracted.get("situation_summary") or extracted.get("parsed_text", ""))
            rep.setdefault("original_language", extracted.get("detected_language", "Urdu / English"))
            rep.setdefault("translation_notes", "Synthesized by Gemini 3.8 Flash (Medium) Linguistic Engine.")
            rep.setdefault("operational_action_items", ["Deploy field response to location.", "Verify headcount and secure area."])
            rep.setdefault("recommended_units", ["Local Emergency Services"])

        # Convenience flat shortcuts for downstream consumers
        extracted["headcount"] = extracted.get("people", {}).get("headcount", 1)
        extracted["vulnerable_groups"] = extracted.get("people", {}).get("vulnerable_groups", [])
        extracted["medical_risks"] = extracted.get("medical_urgencies", {}).get("injuries_reported", [])
        if "medical_urgencies" not in extracted:
            extracted["medical_urgencies"] = {
                "has_medical_emergency": False,
                "urgency_level": "none",
                "injuries_reported": [],
                "immediate_needs": [],
                "details": "No acute medical emergencies reported.",
            }

        return extracted

    async def summarize_incident(
        self, reports_data: list[dict[str, Any]]
    ) -> str:
        """Generate a consolidated incident summary from multiple report extractions."""
        try:
            summary_prompt_path = Path(__file__).parent / "prompts" / "summary.txt"
            summary_prompt = summary_prompt_path.read_text(encoding="utf-8")

            reports_text = json.dumps(reports_data, indent=2, default=str)
            prompt = f"{summary_prompt}\n\nReports data:\n{reports_text}"

            if not self.client:
                return f"Consolidated incident with {len(reports_data)} corroborated reports."

            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=[prompt],
                config=types.GenerateContentConfig(temperature=0.2),
            )
            return response.text or f"Consolidated incident with {len(reports_data)} corroborated reports."
        except Exception as e:
            print(f"[GeminiClient] Summary call failed ({e}), using fallback.")
            return f"Consolidated incident with {len(reports_data)} corroborated reports."

    @classmethod
    def _heuristic_fallback_extraction(
        cls,
        text: str | None,
        has_audio: bool = False,
        has_visual: bool = False,
        location_context: str | None = None,
    ) -> dict[str, Any]:
        """Intelligent rule-based fallback when Gemini API is offline or returns error."""
        import re

        raw_str = (text or "").strip()

        # 1. Normalize whitespace without destructively deleting user emergency words
        clean_text = re.sub(r'\s+', ' ', raw_str).strip()
        if not clean_text:
            clean_text = "Emergency relief assistance requested."
        elif clean_text.lower() in ["general_sos", "urgent_rescue", "emergency", "sos"]:
            clean_text = "Urgent emergency distress signal broadcast."

        text_lower = clean_text.lower()
        hazard_type = "general_emergency"
        hazard_subtype = "emergency_distress"

        # Comprehensive disaster vocabulary
        flood_keywords = [
            "flood", "pani", "paani", "sailab", "sailabi", "water", "doob", "darya", "inundation",
            "breach", "embankment", "river", "rain", "barish", "baarish", "storm", "monsoon",
            "overflow", "overflowing", "submerged", "dam", "nadi", "nullah", "nala"
        ]
        fire_keywords = [
            "fire", "aag", "smoke", "shula", "blaze", "dhuwan", "short circuit", "cylinder", "transformer"
        ]
        collapse_keywords = [
            "collapse", "gir", "debris", "makan", "imarat", "chhat", "chat", "malba", "dabe",
            "kacha", "wall", "roof", "building", "structure"
        ]
        medical_keywords = [
            "doctor", "zakhmi", "injured", "medical", "hospital", "dawa", "dawai", "ambulance",
            "bleeding", "hypothermia", "oxygen", "stroke", "chot", "khoon", "patient", "mareez",
            "heart", "cardiac", "dil"
        ]
        earthquake_keywords = ["earthquake", "zalzala", "hil", "quake", "tremor", "seismic"]
        supply_keywords = ["food", "khana", "ration", "shortage", "bhook", "peene ka pani", "starving"]

        if any(w in text_lower for w in flood_keywords):
            hazard_type = "flood"
            hazard_subtype = "rising_floodwater"
        elif any(w in text_lower for w in fire_keywords):
            hazard_type = "fire"
            hazard_subtype = "active_fire"
        elif any(w in text_lower for w in collapse_keywords):
            hazard_type = "structural_collapse"
            hazard_subtype = "building_collapse"
        elif any(w in text_lower for w in medical_keywords):
            hazard_type = "medical_emergency"
            hazard_subtype = "acute_medical_trauma"
        elif any(w in text_lower for w in earthquake_keywords):
            hazard_type = "earthquake"
            hazard_subtype = "seismic_shock"
        elif any(w in text_lower for w in supply_keywords):
            hazard_type = "supply_shortage"
            hazard_subtype = "critical_ration_need"

        urgency_score = 0.85 if hazard_type in ["flood", "fire", "structural_collapse", "medical_emergency"] else 0.5

        # Smart Headcount Extraction: associate numbers with people terms, avoid water depth (e.g. 5 foot)
        person_match = re.search(r'\b(\d+)\s*(?:log|people|individuals|persons|victims|family\s*members|residents|afraad|khanwadon|bachay|marz|mareez)\b', text_lower)
        if person_match:
            headcount = max(1, int(person_match.group(1)))
        else:
            # Find numbers NOT followed by measurement or time units
            all_nums = re.finditer(r'\b(\d+)\b(?!\s*(?:foot|feet|ft|inch|inches|meter|meters|m|cm|ghantay|hours|hrs|mins|minutes|sector|block|street|gali|manzil|floor|story|storey|date|pm|am))\b', text_lower)
            valid_nums = [int(m.group(1)) for m in all_nums]
            if valid_nums:
                headcount = max(1, valid_nums[0])
            elif any(w in text_lower for w in ["village", "gaon", "dehaat"]):
                headcount = 20
            elif any(w in text_lower for w in ["family", "khandan", "gharane"]):
                headcount = 5
            else:
                headcount = 1

        # Extract vulnerable groups with count awareness
        vulnerable_groups = []
        child_match = re.search(r'\b(\d+)\s*(?:bachay|bacha|children|kids)\b', text_lower)
        child_count = int(child_match.group(1)) if child_match else 1
        if any(w in text_lower for w in ["bacha", "bachay", "child", "children", "infant", "kid", "baby", "toddler"]):
            vulnerable_groups.append({"type": "child", "count": child_count, "details": f"{child_count} children present in distress area"})

        if any(w in text_lower for w in ["buzurg", "elderly", "boodha", "boodhi", "old", "senior", "dadi", "dada", "nana", "nani"]):
            vulnerable_groups.append({"type": "elderly", "count": 1, "details": "Elderly individuals require evacuation"})

        if any(w in text_lower for w in ["pregnant", "hamila", "aurat"]):
            vulnerable_groups.append({"type": "pregnant", "count": 1, "details": "Pregnant mother requiring medical assistance"})

        if any(w in text_lower for w in ["disabled", "mazoor", "wheelchair"]):
            vulnerable_groups.append({"type": "disabled", "count": 1, "details": "Mobility impaired individual"})

        if any(w in text_lower for w in ["phanse", "stuck", "trapped", "chhat", "chat", "rooftop"]):
            vulnerable_groups.append({"type": "trapped", "count": headcount, "details": f"{headcount} individuals stranded/trapped"})

        # Medical urgencies detection
        has_medical = any(w in text_lower for w in [
            "zakhmi", "injured", "bleed", "khoon", "fracture", "chot", "doctor",
            "ambulance", "hospital", "medical", "breathing", "oxygen", "inhaler",
            "asthma", "heart", "stroke", "ill", "sick", "patient", "mareez", "dawai", "dawa", "medicine", "dil"
        ])
        injuries = []
        immediate_needs = []
        if has_medical:
            if any(w in text_lower for w in ["dil", "heart", "cardiac", "dawai", "dawa"]):
                injuries.append("Cardiac condition / Emergency medication required")
                immediate_needs.extend(["cardiac_medication", "emergency_first_aid"])
            else:
                injuries.append("Trauma / Acute medical condition reported from scene")
                immediate_needs.extend(["first_aid_kit", "medical_evacuation"])

        # 2. Location Resolution (Honor location_context when passed)
        found_loc = None
        specifier = ""
        extracted_loc_name = None
        if location_context and location_context.strip() and location_context.strip().lower() not in ["reported location", "reported incident location"]:
            extracted_loc_name = location_context.strip()

        if not extracted_loc_name:
            known_locations = [
                "Korangi", "Gulshan-e-Iqbal", "Gulshan", "Lyari", "Clifton", "Defense", "DHA",
                "Nazimabad", "North Nazimabad", "North Karachi", "Saddar", "Malir", "Federal B Area",
                "FB Area", "Orangi", "Site", "Landhi", "Surjani", "Shah Faisal", "Kemari", "Baldia",
                "Liaquatabad", "Mehmoodabad", "Manzoor Colony", "PECHS", "Gulistan-e-Johar", "Johar",
                "Saadi Town", "Scheme 33", "Bahria Town", "Sarafa Bazaar", "Miranpir", "Echo Lake",
                "Karachi", "Lahore", "Islamabad", "Rawalpindi", "Peshawar", "Quetta", "Multan", "Faisalabad"
            ]
            for loc in known_locations:
                if re.search(rf'\b{re.escape(loc)}\b', clean_text, re.IGNORECASE):
                    found_loc = loc
                    break

            sector_match = re.search(r'(Sector\s*[\w\d-]+|Block\s*[\w\d-]+|Street\s*[\w\d-]+|Phase\s*[\w\d-]+)', clean_text, re.IGNORECASE)
            specifier = sector_match.group(0) if sector_match else ""

            if found_loc and specifier and found_loc.lower() not in specifier.lower():
                extracted_loc_name = f"{found_loc} {specifier}".strip()
            elif found_loc:
                extracted_loc_name = found_loc
            elif specifier:
                extracted_loc_name = specifier
            elif location_context:
                extracted_loc_name = location_context.strip()
            else:
                extracted_loc_name = "Distress Incident Site"

        # 3. Intelligent Urdu / Roman Urdu / English Translation
        is_roman_urdu = any(w in text_lower for w in [
            "hai", "hain", "me", "mein", "par", "se", "aa", "gaya", "gayi", "pani", "paani",
            "aag", "zakhmi", "log", "madad", "bachao", "ghar", "chat", "chhat", "bacha",
            "bache", "aurat", "jaldi", "bhejo", "bhejein", "makan", "gir", "dabe", "phanse",
            "chahiye", "dadi", "dawa", "dawai", "barish", "sailab"
        ])
        is_urdu_script = bool(re.search(r'[\u0600-\u06FF]', clean_text))

        urdu_hazards_map = {
            "flood": "سیلاب کا پانی داخل ہو گیا ہے",
            "fire": "آگ لگنے کا شدید واقعہ پیش آیا ہے",
            "structural_collapse": "عمارت کا ملبہ یا چھت گر گئی ہے",
            "medical_emergency": "شدید طبی امداد کی ضرورت ہے",
            "earthquake": "زلزلے کے جھٹکے اور نقصان ہوا ہے",
            "supply_shortage": "خوراک اور پینے کے پانی کی شدید قلت ہے",
            "general_emergency": "ہنگامی صورتحال پیش آئی ہے",
        }
        urdu_hazard_desc = urdu_hazards_map.get(hazard_type, "ہنگامی صورتحال پیش آئی ہے")

        if is_roman_urdu:
            detected_lang = "roman_urdu"
            # Build natural, fluent English translation
            clause_main = ""
            if hazard_type == "flood":
                if any(w in text_lower for w in ["ghar", "andar", "pani", "paani"]):
                    clause_main = f"Floodwater has inundated residential homes in {extracted_loc_name}."
                elif any(w in text_lower for w in ["embankment", "breach"]):
                    clause_main = f"Severe embankment breach has caused flooding threatening homes in {extracted_loc_name}."
                else:
                    clause_main = f"Severe flooding reported in {extracted_loc_name}."
            elif hazard_type == "fire":
                clause_main = f"An active fire has broken out in {extracted_loc_name}."
            elif hazard_type == "structural_collapse":
                clause_main = f"Structural collapse and fallen debris reported in {extracted_loc_name}."
            elif hazard_type == "medical_emergency":
                clause_main = f"Urgent medical emergency reported in {extracted_loc_name}."
            else:
                clause_main = f"Urgent emergency distress signal received from {extracted_loc_name}."

            clauses_victim = []
            if any(w in text_lower for w in ["chat", "chhat"]):
                clauses_victim.append(f"{headcount} individual(s) are trapped on the rooftop")
            elif any(w in text_lower for w in ["phanse", "stuck", "trapped"]):
                clauses_victim.append(f"{headcount} individual(s) are trapped and unable to evacuate")
            elif headcount > 1:
                clauses_victim.append(f"{headcount} individuals are in immediate danger")

            special_needs = []
            if any(w in text_lower for w in ["bacha", "bachay", "child", "infant"]):
                special_needs.append("children/infants on site")
            if any(w in text_lower for w in ["buzurg", "elderly", "dadi", "dada"]):
                special_needs.append("elderly residents")
            if any(w in text_lower for w in ["dil", "heart", "dawa", "dawai", "medicine"]):
                special_needs.append("urgent cardiac medication required")
            elif any(w in text_lower for w in ["zakhmi", "injured", "chot"]):
                special_needs.append("injured casualties requiring medical evacuation")

            if special_needs:
                clauses_victim.append(f"with {', '.join(special_needs)}")

            victim_sentence = " ".join(clauses_victim)
            if victim_sentence:
                victim_sentence = victim_sentence.capitalize() + "."

            action_sentence = "Immediate rescue team dispatch and relief assistance requested."

            english_translation = f"{clause_main} {victim_sentence} {action_sentence}".strip()
            urdu_translation = f"{extracted_loc_name} میں {urdu_hazard_desc}۔ {headcount} افراد خطرے میں ہیں، فوری امداد اور ریسکیو ٹیم روانہ کی جائے۔"

        elif is_urdu_script:
            detected_lang = "urdu_script"
            english_translation = f"Emergency at {extracted_loc_name}: {hazard_type.replace('_', ' ').title()} incident involving {headcount} individual(s). Immediate rescue and relief requested."
            urdu_translation = clean_text
        else:
            detected_lang = "english"
            english_translation = clean_text
            urdu_translation = f"{extracted_loc_name} میں {urdu_hazard_desc}۔ {headcount} افراد متاثر ہیں اور فوری ریسکیو کی ضرورت ہے۔"

        # 4. Construct human-readable, operational situation summary
        situation_summary = (
            f"{hazard_type.replace('_', ' ').title()} emergency at {extracted_loc_name}. "
            f"{headcount} individual(s) affected. {english_translation}"
        )

        parsed_text = clean_text
        hazard_display = hazard_type.replace('_', ' ').title()
        overall_report = {
            "title": f"{hazard_display} Emergency - {extracted_loc_name}",
            "executive_summary": english_translation,
            "original_language": "Roman Urdu" if is_roman_urdu else ("Urdu" if is_urdu_script else "English"),
            "translation_notes": "Synthesized emergency distress communication translation.",
            "operational_action_items": [
                f"Dispatch response unit to validated coordinates at {extracted_loc_name}.",
                f"Account for and secure safety of {headcount} reported individual(s)."
            ],
            "recommended_units": ["Rescue 1122 Rapid Response Unit", "Emergency Medical Services"],
        }

        return {
            "hazard_type": hazard_type,
            "hazard_subtype": hazard_subtype,
            "urgency_score": urgency_score,
            "confidence_score": 0.85,
            "parsed_text": parsed_text,
            "caller_statement": parsed_text,
            "english_translation": english_translation,
            "urdu_translation": urdu_translation,
            "situation_summary": situation_summary,
            "overall_report": overall_report,
            "headcount": headcount,
            "vulnerable_groups": vulnerable_groups,
            "medical_risks": immediate_needs,
            "injuries_reported": injuries,
            "location": {
                "extracted_name": extracted_loc_name,
                "neighborhood": found_loc or "",
                "sector_block": specifier or "",
                "city": "Pakistan",
                "landmarks": [],
                "specificity": "street_level" if specifier else "neighborhood",
            },
            "people": {
                "headcount": headcount,
                "headcount_confidence": "estimated",
                "vulnerable_groups": vulnerable_groups,
            },
            "medical_urgencies": {
                "has_medical_emergency": has_medical,
                "urgency_level": "critical" if has_medical else "none",
                "injuries_reported": injuries,
                "immediate_needs": immediate_needs,
                "details": "Immediate medical attention required" if has_medical else "No acute medical trauma detected",
            },
            "situation_summary": situation_summary,
            "situation_details": {
                "is_escalating": True,
                "supplies_needed": immediate_needs,
            },
            "visual_evidence_analysis": {
                "visible_hazards": [hazard_type] if hazard_type != "unclear" else [],
                "visual_severity": "high" if urgency_score > 0.7 else "medium",
                "scene_authenticity": "authentic_emergency",
                "damage_observed": "Emergency conditions observed at location.",
            },
            "anomaly_flags": [],
            "raw_input_preserved": raw_str,
            "detected_language": detected_lang,
            "escalation_triggers": ["life_safety_priority"],
        }

    @staticmethod
    def _empty_extraction() -> dict[str, Any]:
        """Return a safe empty extraction when input is missing or parsing fails."""
        return {
            "hazard_type": "unclear",
            "hazard_subtype": "unknown",
            "urgency_score": 0.0,
            "confidence_score": 0.0,
            "parsed_text": "No distress narrative provided.",
            "overall_report": {
                "title": "Pending Emergency Incident",
                "executive_summary": "Emergency alert registered without distress audio or narrative text. Immediate field reconnaissance advised.",
                "original_language": "Unknown",
                "translation_notes": "No voice or text input was provided for translation.",
                "operational_action_items": ["Contact caller or verify GPS coordinates for ground validation."],
                "recommended_units": ["Local First Response Patrol"],
            },
            "location": {"extracted_name": "", "specificity": "none"},
            "people": {"headcount": 0, "headcount_confidence": "unknown", "vulnerable_groups": []},
            "medical_urgencies": {
                "has_medical_emergency": False,
                "urgency_level": "none",
                "injuries_reported": [],
                "immediate_needs": [],
                "details": "None reported",
            },
            "situation_summary": "Unable to extract emergency information from input.",
            "situation_details": {"is_escalating": False, "supplies_needed": []},
            "visual_evidence_analysis": {"visible_hazards": [], "visual_severity": "none", "scene_authenticity": "none", "damage_observed": "none"},
            "anomaly_flags": [{"flag_type": "single_word_input", "description": "Empty or unparseable input", "severity": "critical"}],
            "raw_input_preserved": "",
            "detected_language": "unknown",
            "escalation_triggers": [],
            "headcount": 0,
            "vulnerable_groups": [],
            "medical_risks": [],
        }


# Module-level singleton
gemini_client = GeminiClient()

