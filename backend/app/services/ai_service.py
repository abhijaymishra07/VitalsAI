import re
from typing import Iterable

from openai import OpenAI

from app.core.config import settings
from app.schemas.health import HealthSnapshot, MetricSnapshot
from app.services.condition_knowledge import find_condition_profile, profile_for_metric_name


MEDICAL_TERM_ALIASES: dict[str, str] = {
    "vit c": "vitamin c",
    "vitamin-c": "vitamin c",
    "ascorbic acid": "vitamin c",
    "vit d": "vitamin d",
    "vitamin-d": "vitamin d",
    "25-oh vitamin d": "vitamin d",
    "25 - oh vitamin d": "vitamin d",
    "vit b12": "vitamin b12",
    "vitamin-b12": "vitamin b12",
    "b12": "vitamin b12",
    "cobalamin": "vitamin b12",
    "vit b": "vitamin b",
    "folic acid": "folate",
    "folic": "folate",
    "blood sugar": "glucose",
    "fasting glucose": "glucose",
    "fbs": "glucose",
    "sugar": "glucose",
    "egfr": "egfr",
    "gfr": "egfr",
    "chol": "cholesterol",
    "total cholesterol": "cholesterol",
    "bad cholesterol": "ldl",
    "good cholesterol": "hdl",
    "wbc": "wbc",
    "rbc": "rbc",
    "hb": "hemoglobin",
    "hgb": "hemoglobin",
    "pcv": "pcv",
    "hct": "pcv",
    "hematocrit": "pcv",
}

OFFLINE_MEDICAL_TERMS: dict[str, str] = {
    "creatinine": "Creatinine is a waste product filtered by the kidneys. Higher levels may suggest reduced kidney filtration and should be read with eGFR and clinical context.",
    "egfr": "eGFR (estimated glomerular filtration rate) estimates how well your kidneys filter blood. Lower values suggest reduced kidney function.",
    "glucose": "Glucose is blood sugar. Persistently high fasting glucose may indicate insulin resistance or diabetes risk; low glucose can cause weakness or dizziness.",
    "cholesterol": "Total cholesterol measures blood fats that can affect heart and artery health. It is interpreted together with LDL, HDL, and triglycerides.",
    "ldl": "LDL is often called 'bad cholesterol' because higher levels are linked to artery plaque and cardiovascular risk.",
    "hdl": "HDL is often called 'good cholesterol' because it helps remove excess cholesterol from blood vessels.",
    "triglycerides": "Triglycerides are blood fats used for energy storage. High levels are linked to metabolic and heart risk.",
    "hemoglobin": "Hemoglobin is the oxygen-carrying protein in red blood cells. Low levels may indicate anemia.",
    "haemoglobin": "Haemoglobin is the oxygen-carrying protein in red blood cells. Low levels may indicate anemia.",
    "hba1c": "HbA1c shows your average blood sugar over roughly 3 months. It is a key marker for diabetes screening and control.",
    "tsh": "TSH (Thyroid Stimulating Hormone) tells your thyroid gland how much hormone to make. It is the main screening test for thyroid function.",
    "pdw": "PDW (Platelet Distribution Width) measures variation in platelet size. Higher PDW can reflect active platelet turnover and is usually interpreted with platelet count and MPV.",
    "mpv": "MPV (Mean Platelet Volume) is the average size of platelets. Larger platelets may be younger and more active; read with platelet count and PDW.",
    "rdw": "RDW (Red Cell Distribution Width) shows how much red blood cell size varies. A high RDW can appear in iron deficiency, B12/folate deficiency, or mixed anemias.",
    "rdw-cv": "RDW-CV measures variation in red blood cell size. Elevated values can suggest nutritional anemias or mixed blood disorders.",
    "mcv": "MCV (Mean Corpuscular Volume) is the average size of red blood cells. Low MCV suggests microcytic anemia; high MCV suggests macrocytic anemia.",
    "mch": "MCH (Mean Corpuscular Hemoglobin) is the average amount of hemoglobin per red blood cell.",
    "mchc": "MCHC (Mean Corpuscular Hemoglobin Concentration) is hemoglobin concentration inside red blood cells.",
    "pcv": "PCV (Packed Cell Volume / Hematocrit) is the percentage of blood made up of red cells. Low PCV can indicate anemia; high PCV may reflect dehydration or polycythemia.",
    "esr": "ESR (Erythrocyte Sedimentation Rate) is a general inflammation marker. It rises with infection, inflammation, and some chronic diseases.",
    "platelet": "Platelets help blood clot and stop bleeding. Low counts raise bleeding risk; high counts may reflect inflammation or other conditions.",
    "platelet count": "Platelet count measures clot-forming cells in blood. It is interpreted with MPV and PDW.",
    "wbc": "WBC (White Blood Cell count) reflects immune cells in blood. High counts may suggest infection or inflammation; low counts may raise infection risk.",
    "rbc": "RBC (Red Blood Cell count) measures oxygen-carrying cells. Low RBC often appears with anemia.",
    "urea": "Blood urea reflects protein breakdown and kidney clearance. It rises when kidney function drops or with high protein load/dehydration.",
    "bun": "BUN (Blood Urea Nitrogen) is a kidney marker related to urea. It rises with reduced kidney function or dehydration.",
    "alt": "ALT is a liver enzyme. Elevated ALT often suggests liver cell stress from fatty liver, alcohol, medicines, or hepatitis.",
    "ast": "AST is an enzyme found in liver and muscle. Elevated AST may reflect liver injury, muscle injury, or other tissue stress.",
    "bilirubin": "Bilirubin is a yellow pigment from red blood cell breakdown. High levels can cause jaundice and may reflect liver or bile duct problems.",
    "vitamin a": "Vitamin A supports vision, skin health, and immune function. Deficiency can affect night vision; excess can be toxic.",
    "vitamin b": "B vitamins help energy metabolism, nerves, and blood cell production. Different B vitamins (B1, B6, B12, folate) have distinct roles.",
    "vitamin c": "Vitamin C (ascorbic acid) supports immunity, skin, wound healing, and iron absorption. Deficiency can cause scurvy; very high doses may upset the stomach.",
    "vitamin d": "Vitamin D supports bone health, immunity, and calcium balance. Low levels are common and may need diet, sun exposure, or supplementation.",
    "vitamin e": "Vitamin E is an antioxidant that helps protect cells. Deficiency is uncommon but may affect nerves and muscles.",
    "vitamin k": "Vitamin K is needed for blood clotting and bone health. Low levels can increase bleeding risk.",
    "vitamin b12": "Vitamin B12 is needed for nerves, DNA synthesis, and red blood cell health. Low levels can cause anemia and neuropathy symptoms.",
    "folate": "Folate (vitamin B9) is essential for DNA synthesis and red blood cell formation. Low folate can contribute to anemia, especially in pregnancy.",
    "iron": "Iron is needed for hemoglobin and oxygen transport. Low iron is a common cause of anemia; high iron may reflect overload conditions.",
    "ferritin": "Ferritin reflects iron stores in the body. Low ferritin suggests iron deficiency; high ferritin may reflect inflammation or iron overload.",
    "calcium": "Calcium supports bones, muscles, nerves, and heart rhythm. Abnormal levels should be interpreted with albumin and vitamin D.",
    "magnesium": "Magnesium supports muscles, nerves, and heart rhythm. Low levels may cause cramps, fatigue, or arrhythmias.",
    "potassium": "Potassium is an electrolyte vital for heart and muscle function. High or low potassium can be dangerous and needs clinical review.",
    "sodium": "Sodium is an electrolyte that helps control fluid balance and blood pressure. Abnormal sodium often relates to hydration or kidney issues.",
    "crp": "CRP (C-Reactive Protein) is an inflammation marker. It rises with infection, inflammation, and cardiovascular risk.",
    "hs-crp": "hs-CRP is a high-sensitivity inflammation marker linked to heart disease risk when persistently elevated.",
    "thyroid": "The thyroid gland regulates metabolism, energy, heart rate, and temperature through thyroid hormones.",
    "kidney": "Kidneys filter blood, remove waste, and balance fluids and electrolytes.",
    "liver": "The liver processes nutrients, detoxifies chemicals, and makes proteins essential for metabolism and clotting.",
    "anemia": "Anemia means low hemoglobin or red cell mass, leading to fatigue and reduced oxygen delivery. Causes include iron, B12, folate deficiency, or chronic disease.",
}


class AIService:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.openai_api_key, timeout=5) if settings.openai_api_key else None

    def explain_metric(self, metric_name: str, value: float, unit: str, abnormal: bool, fast: bool = False) -> str:
        risk = "outside typical range" if abnormal else "within a likely normal range"
        quick = f"{metric_name} is {value} {unit}. It appears {risk}. Discuss with your clinician for diagnosis."
        if fast or not self.client:
            return quick
        try:
            prompt = (
                f"You are a medical education assistant. Explain the lab metric {metric_name} "
                f"with measured value {value} {unit}. Abnormal={abnormal}. Keep answer under 100 words and non-diagnostic."
            )
            response = self.client.responses.create(model=settings.llm_model, input=prompt)
            return response.output_text
        except Exception:
            return quick

    @staticmethod
    def _collapse_dotted_abbrev(text: str) -> str:
        return re.sub(
            r"(?:[a-z]\.)+[a-z]:?",
            lambda match: match.group(0).replace(".", "").rstrip(":"),
            text,
            flags=re.IGNORECASE,
        )

    @classmethod
    def _normalize_lab_abbrev(cls, term: str) -> str:
        cleaned = cls._collapse_dotted_abbrev(term.strip().lower()).rstrip(":. ")
        return cleaned.replace("rdw-cv", "rdw")

    @classmethod
    def _canonical_medical_term(cls, term: str) -> str:
        normalized = cls._normalize_lab_abbrev(term).replace("-", " ").strip()
        if normalized in MEDICAL_TERM_ALIASES:
            return MEDICAL_TERM_ALIASES[normalized]
        for alias, canonical in MEDICAL_TERM_ALIASES.items():
            if normalized == alias or alias in normalized or normalized in alias:
                return canonical
        return normalized

    @classmethod
    def _lookup_offline_term(cls, term: str) -> str | None:
        canonical = cls._canonical_medical_term(term)
        if canonical in OFFLINE_MEDICAL_TERMS:
            return OFFLINE_MEDICAL_TERMS[canonical]
        profile = find_condition_profile(canonical)
        if profile:
            return profile["meaning"]
        for key, explanation in OFFLINE_MEDICAL_TERMS.items():
            if canonical in key or key in canonical:
                return explanation
        return None

    def explain_medical_term(self, term: str, snapshot: HealthSnapshot | None = None) -> str:
        canonical = self._canonical_medical_term(term)
        offline = self._lookup_offline_term(term)
        if offline:
            explanation = offline
        elif not self.client:
            explanation = self._generic_term_fallback(term, canonical)
        else:
            try:
                response = self.client.responses.create(
                    model=settings.llm_model,
                    input=(
                        f"Explain the medical or lab term '{term}' in plain English in 2-4 sentences. "
                        "Include what it measures, why doctors order it, and what high/low may suggest. "
                        "Keep it educational and non-diagnostic."
                    ),
                )
                explanation = response.output_text
            except Exception:
                explanation = self._generic_term_fallback(term, canonical)

        if snapshot:
            metric = self._find_metric_for_term(term, snapshot)
            if metric is None:
                for m in snapshot.metrics:
                    if canonical in m.metric_name.lower() or m.metric_name.lower() in canonical:
                        metric = m
                        break
            if metric:
                ref = ""
                if metric.reference_min is not None and metric.reference_max is not None:
                    ref = f" (reference {metric.reference_min}–{metric.reference_max} {metric.unit})"
                status = "above reference" if metric.is_abnormal else "within reference"
                explanation += (
                    f"\n\n**Your latest value:** {metric.metric_value} {metric.unit} — {status}{ref}."
                )

        return explanation

    @staticmethod
    def _generic_term_fallback(term: str, canonical: str) -> str:
        if canonical.startswith("vitamin "):
            letter = canonical.replace("vitamin ", "").strip().upper()
            return (
                f"Vitamin {letter} is a nutrient involved in normal body function. "
                f"'{term}' usually refers to this vitamin or a related lab marker. "
                "Interpret results with your full report and clinician — levels vary by age, diet, and health conditions."
            )
        return (
            f"'{term}' is a medical or lab-related term. "
            f"It should be interpreted with your symptoms, other labs, and clinical context — not as a standalone diagnosis. "
            "Upload your report or ask in chat with the exact line name for a value-specific explanation."
        )

    def health_chat(
        self,
        user_message: str,
        snapshot: HealthSnapshot,
        extra_context: Iterable[str] | None = None,
        citations: Iterable[str] | None = None,
        chat_history: Iterable[tuple[str, str]] | None = None,
    ) -> str:
        citation_list = list(citations or [])
        history = list(chat_history or [])

        if snapshot.metrics:
            return self._offline_copilot_reply(user_message, snapshot, citation_list, history)

        prompt_lines = self._snapshot_to_prompt(snapshot)
        if extra_context:
            prompt_lines.extend(extra_context)
        if citation_list:
            prompt_lines.append("Relevant report excerpts:")
            prompt_lines.extend(citation_list[:5])

        context = "\n".join(prompt_lines)
        system_prompt = (
            "You are a personal health copilot. Use the patient's actual lab values and prior chat turns. "
            "Answer in clear sections with bullet points when explaining conditions: meaning, risks, prevention, treatment. "
            "Educational only — not a diagnosis. Mention clinician follow-up for abnormal values."
        )
        if not self.client:
            return self._offline_copilot_reply(user_message, snapshot, citation_list, history)
        try:
            messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
            for role, text in history[-8:]:
                messages.append({"role": role, "content": text})
            messages.append(
                {
                    "role": "user",
                    "content": f"Patient data:\n{context}\n\nQuestion:\n{user_message}",
                }
            )
            response = self.client.responses.create(model=settings.llm_model, input=messages)
            return response.output_text
        except Exception:
            return self._offline_copilot_reply(user_message, snapshot, citation_list, history)

    def doctor_summary(self, context_items: Iterable[str]) -> str:
        context = "\n".join(context_items)
        if not self.client:
            return f"Doctor-ready summary:\n{context}"
        try:
            response = self.client.responses.create(
                model=settings.llm_model,
                input=(
                    "Create a concise doctor handoff summary from this patient context. "
                    "Include trend concerns, abnormal values, adherence notes, and key questions.\n\n"
                    f"{context}"
                ),
            )
            return response.output_text
        except Exception:
            return f"Doctor-ready summary:\n{context}"

    def symptom_guidance(
        self,
        symptoms: str,
        snapshot: HealthSnapshot,
        specialist: str,
        urgency: str,
    ) -> str:
        abnormal = self._abnormal_for_reply(snapshot)
        lab_context = ""
        if abnormal:
            lab_context = "Relevant abnormal labs:\n" + self._format_abnormal_bullets(abnormal[:5], include_count=False)

        if self.client:
            try:
                response = self.client.responses.create(
                    model=settings.llm_model,
                    input=(
                        f"Patient symptoms: {symptoms}\n"
                        f"Suggested specialist: {specialist}, urgency: {urgency}\n"
                        f"{lab_context}\n"
                        "Provide brief educational guidance: what the symptom may indicate, "
                        "when to seek urgent care, simple home care tips, and how their labs may relate if relevant. "
                        "Under 150 words. Not a diagnosis."
                    ),
                )
                return response.output_text
            except Exception:
                pass

        return self._offline_symptom_reply(symptoms, snapshot, specialist, urgency)

    def _offline_symptom_reply(
        self,
        symptoms: str,
        snapshot: HealthSnapshot,
        specialist: str,
        urgency: str,
    ) -> str:
        text = symptoms.lower()
        guidance: list[str] = []

        if any(w in text for w in ("chest tightness", "chest pain", "chest pressure", "chest discomfort")):
            guidance.extend([
                "Chest tightness can come from heart-related causes, acid reflux, muscle strain, anxiety, or lung issues.",
                "Seek emergency care immediately if you have crushing chest pain, pain spreading to arm/jaw, breathlessness, sweating, nausea, or fainting.",
                "Until evaluated: rest, avoid exertion, and do not ignore new or worsening symptoms.",
            ])
        elif any(w in text for w in ("breathless", "breathlessness", "shortness of breath", "can't breathe")):
            guidance.extend([
                "Shortness of breath can reflect heart, lung, anemia, or anxiety-related causes.",
                "Seek urgent care if breathing is suddenly worse, lips turn blue, or you cannot speak in full sentences.",
                "Sit upright, loosen tight clothing, and avoid triggers like smoke or heavy exertion until seen.",
            ])
        elif any(w in text for w in ("skin", "rash", "itch", "lesion")):
            guidance.extend([
                "Skin rashes may reflect allergy, infection, eczema, or medication reaction.",
                "Seek urgent care for spreading rash with fever, facial swelling, or trouble breathing.",
                "Avoid scratching, note new soaps/medicines/foods, and keep the area clean and dry.",
            ])
        elif any(w in text for w in ("anxiety", "depression", "mood", "panic")):
            guidance.extend([
                "Mood and anxiety symptoms are common and treatable — they are not a sign of weakness.",
                "Seek urgent help for thoughts of self-harm or if panic feels unmanageable.",
                "Try slow breathing (4-7-8), regular sleep, and limit caffeine/alcohol while arranging professional support.",
            ])
        elif any(w in text for w in ("sugar", "thirst", "frequent urination", "diabetes")):
            guidance.extend([
                "These symptoms can suggest high blood sugar or diabetes risk.",
                "Seek urgent care if you have vomiting, confusion, rapid breathing, or fruity breath.",
                "Limit sugary drinks, walk after meals, and discuss fasting glucose/HbA1c with your doctor.",
            ])
        elif any(w in text for w in ("cough", "fever", "cold", "sore throat")):
            guidance.extend([
                "Respiratory symptoms often reflect viral infection but can also signal pneumonia or other illness.",
                "Seek care if fever is high/persistent, breathing is difficult, or symptoms worsen after initial improvement.",
                "Rest, hydrate, use paracetamol for fever if suitable, and isolate if contagious.",
            ])
        else:
            guidance.append(
                f"For '{symptoms.strip()}', a {specialist} visit ({urgency}) is a reasonable starting point."
            )

        abnormal = self._abnormal_for_reply(snapshot)
        related: list[str] = []
        if any(w in text for w in ("chest", "breath", "heart", "palpitation")):
            related = [m for m in abnormal if any(k in m.metric_name.lower() for k in ("hemoglobin", "pcv", "hba1c", "glucose", "triglyceride", "ldl"))]
        elif any(w in text for w in ("tired", "fatigue", "weak", "anemia")):
            related = [m for m in abnormal if any(k in m.metric_name.lower() for k in ("hemoglobin", "pcv", "rdw", "b12", "vitamin d", "iron"))]
        elif any(w in text for w in ("sugar", "thirst", "diabetes")):
            related = [m for m in abnormal if any(k in m.metric_name.lower() for k in ("glucose", "hba1c", "eag", "triglyceride"))]
        else:
            related = abnormal[:3]

        if related:
            lab_lines = ", ".join(f"{m.metric_name} {m.metric_value}{m.unit}" for m in related[:3])
            guidance.append(f"Your recent labs that may be relevant: {lab_lines}.")

        guidance.append("This is educational guidance only — not a diagnosis.")
        return " ".join(guidance)

    def _is_metric_question(self, message: str) -> bool:
        msg = message.strip().lower()
        keywords = (
            "lower",
            "reduce",
            "increase",
            "boost",
            "raise",
            "high",
            "low",
            "explain",
            "cholesterol",
            "cholestrol",
            "ldl",
            "hdl",
            "glucose",
            "sugar",
            "creatinine",
            "hba1c",
            "triglyceride",
            "lipid",
            "vitamin",
            "b12",
            "thyroid",
            "hemoglobin",
            "haemoglobin",
            "kidney",
            "liver",
            "abnormal",
            "what about",
            "my ",
            "help",
            "improve",
            "control",
            "what is",
            "what's",
            "meaning",
            "define",
        )
        return any(keyword in msg for keyword in keywords)

    def _is_action_question(self, msg: str) -> bool:
        if self._is_definition_question(msg):
            return False
        return any(
            keyword in msg
            for keyword in ("reduce", "lower", "increase", "boost", "raise", "improve", "control", "high", "low", "help")
        )

    def _is_definition_question(self, msg: str) -> bool:
        if self._is_more_abnormal_question(msg):
            return False
        return bool(
            re.search(
                r"\b(what is|what's|whats|what does|explain|meaning of|define|tell me about|describe)\b",
                msg,
                flags=re.IGNORECASE,
            )
        ) or bool(re.fullmatch(r"[a-z0-9 /%-]{2,40}\??", msg.strip(), flags=re.IGNORECASE))

    def _is_more_abnormal_question(self, msg: str) -> bool:
        normalized = self._normalize_msg(msg)
        exact = {
            "what else",
            "anything else",
            "what other",
            "what others",
            "more",
            "next",
            "else",
            "others",
            "go on",
            "continue",
            "and then",
            "show more",
            "any more",
            "what more",
        }
        if normalized in exact:
            return True
        return any(phrase in normalized for phrase in ("what else", "anything else", "other abnormal", "more abnormal"))

    def _extract_term_from_question(self, msg: str) -> str | None:
        patterns = [
            r"(?:what is|what's|whats|explain|meaning of|define|tell me about|describe)\s+(.+)",
            r"what does\s+(.+?)\s+mean\b",
            r"^(.+?)\s+(?:means?|meaning)\??$",
        ]
        for pattern in patterns:
            match = re.search(pattern, msg.strip(), flags=re.IGNORECASE)
            if match:
                term = match.group(1).strip().rstrip("?.!")
                term = re.sub(r"\b(in my report|from my report|in simple terms)\b", "", term, flags=re.IGNORECASE).strip()
                term = re.split(r"\s+and\s+(?:how|why|is|are)\b", term, maxsplit=1, flags=re.IGNORECASE)[0].strip()
                if term:
                    return self._normalize_lab_abbrev(term)

        cleaned = self._normalize_lab_abbrev(msg.strip().rstrip("?.!"))
        if self._is_vague_term(cleaned) or self._is_more_abnormal_question(cleaned):
            return None
        if 1 <= len(cleaned.split()) <= 3 and not self._is_abnormal_list_question(cleaned):
            return cleaned
        return None

    def _find_metric_for_term(self, term: str, snapshot: HealthSnapshot) -> MetricSnapshot | None:
        needle = self._normalize_lab_abbrev(term)
        if not needle:
            return None

        for metric in snapshot.metrics:
            name = metric.metric_name.lower()
            if name == needle or needle in name or name in needle:
                return metric

        for metric in snapshot.metrics:
            first_token = metric.metric_name.lower().split()[0]
            if first_token == needle or needle == first_token:
                return metric
        return None

    def _wants_disease_detail(self, msg: str) -> bool:
        normalized = self._normalize_msg(msg)
        if self._is_more_abnormal_question(normalized):
            return False
        return any(
            word in normalized
            for word in (
                "disease",
                "condition",
                "risks",
                "risk",
                "threat",
                "danger",
                "complication",
                "prevention",
                "prevent",
                "cure",
                "treatment",
                "treat",
                "manage",
                "symptom",
                "linked to",
                "cause",
                "harmful",
                "harm",
                "dangerous",
                "bad for",
            )
        )

    def _is_follow_up_question(self, msg: str) -> bool:
        return any(
            phrase in msg
            for phrase in (
                "this",
                "that",
                "it",
                "same",
                "those",
                "tell me more",
                "what about",
                "and the",
                "more about",
                "follow up",
                "you mentioned",
                "above",
                "medical condition",
            )
        )

    def _guess_term_from_text(self, text: str, snapshot: HealthSnapshot) -> str | None:
        lowered = text.lower()
        profile = find_condition_profile(lowered)
        if profile:
            return profile["aliases"][0]
        for metric in snapshot.metrics:
            name = metric.metric_name.lower()
            if name in lowered or name.split()[0] in lowered:
                return metric.metric_name
        for word in re.findall(r"[a-z0-9]{2,}", lowered):
            if find_condition_profile(word) or self._find_metric_for_term(word, snapshot):
                return word
        return None

    def _is_vague_term(self, term: str) -> bool:
        lowered = term.strip().lower()
        vague_terms = {
            "this",
            "that",
            "it",
            "condition",
            "medical condition",
            "this medical condition",
            "this condition",
            "that condition",
            "what else",
            "anything else",
            "what other",
            "more",
            "else",
            "others",
            "next",
            "go on",
            "continue",
        }
        return lowered in vague_terms or lowered.startswith("this ") or lowered.startswith("that ")

    def _resolve_conversation_topic(
        self,
        msg: str,
        history: list[tuple[str, str]],
        snapshot: HealthSnapshot,
    ) -> str | None:
        extracted = self._extract_term_from_question(msg)
        if extracted:
            cleaned = extracted.strip().rstrip("?.!")
            if not self._is_vague_term(cleaned):
                if find_condition_profile(cleaned) or self._find_metric_for_term(cleaned, snapshot):
                    return cleaned
                if len(cleaned.split()) <= 4:
                    return cleaned

        if not self._is_follow_up_question(msg) and not self._wants_disease_detail(msg):
            return None

        for role, text in reversed(history[-10:]):
            if role == "user":
                term = self._extract_term_from_question(self._normalize_msg(text))
                if term:
                    return term
            guessed = self._guess_term_from_text(text, snapshot)
            if guessed:
                return guessed
        return None

    def _condition_deep_reply(self, term: str, snapshot: HealthSnapshot) -> str:
        profile = find_condition_profile(term)
        metric = self._find_metric_for_term(term, snapshot)
        if profile is None and metric is not None:
            profile = profile_for_metric_name(metric.metric_name)

        title = profile["title"] if profile else term.strip().title()
        meaning = profile["meaning"] if profile else self.explain_medical_term(term)
        risks = profile["risks"] if profile else [
            "Progression if the underlying cause is not addressed",
            "Complications depend on severity — discuss your exact values with a clinician",
        ]
        prevention = profile["prevention"] if profile else [
            "Regular lab monitoring and healthy lifestyle habits",
            "Early treatment of related conditions (BP, sugar, thyroid, nutrition)",
        ]
        treatment = profile["treatment"] if profile else [
            "Personalized plan based on repeat labs and clinical exam",
            "Medicines only if prescribed by your doctor",
        ]

        lines = [title, "", "What it means:", f"• {meaning}", "", "Potential risks / threats:"]
        lines.extend(f"• {item}" for item in risks)
        lines.extend(["", "Prevention:"])
        lines.extend(f"• {item}" for item in prevention)
        lines.extend(["", "Treatment / management:"])
        lines.extend(f"• {item}" for item in treatment)

        if metric:
            ref = ""
            if metric.reference_min is not None and metric.reference_max is not None:
                ref = f" (reference {metric.reference_min}-{metric.reference_max} {metric.unit})"
            status = "above reference" if metric.is_abnormal else "within reference"
            lines.extend(["", "Your latest lab value:", f"• {metric.metric_name}: {metric.metric_value} {metric.unit} — {status}{ref}"])

        lines.append("\nThis is educational guidance, not a diagnosis. Please confirm with your doctor.")
        return "\n".join(lines)

    def _is_comparison_question(self, msg: str) -> bool:
        return bool(
            re.search(
                r"\b(same|equal|identical|difference|different|compare|comparison|vs|versus|related|relation|linked|connection)\b",
                msg,
                flags=re.IGNORECASE,
            )
        ) or bool(re.search(r"\b(.+?)\s+and\s+(.+?)\s+(?:is|are)\b", msg, flags=re.IGNORECASE))

    def _extract_comparison_terms(self, msg: str) -> tuple[str, str] | None:
        patterns = [
            r"(.+?)\s+and\s+(.+?)\s+(?:is|are)\s+(?:the\s+)?(?:same|equal|identical)",
            r"(?:difference|compare|comparison)\s+(?:between\s+)?(.+?)\s+and\s+(.+)",
            r"(.+?)\s+(?:vs|versus)\s+(.+)",
            r"(?:is|are)\s+(.+?)\s+and\s+(.+?)\s+(?:the\s+)?(?:same|related|linked)",
            r"(.+?)\s+and\s+(.+?)\s+(?:related|linked|connected)",
        ]
        for pattern in patterns:
            match = re.search(pattern, msg.strip().rstrip("?.!"), flags=re.IGNORECASE)
            if match:
                left = match.group(1).strip()
                right = match.group(2).strip().rstrip("?.!")
                if left and right and not self._is_vague_term(left) and not self._is_vague_term(right):
                    return left, right
        return None

    def _normalize_compare_key(self, term: str) -> str:
        return self._normalize_lab_abbrev(term)

    def _comparison_reply(self, term_a: str, term_b: str, snapshot: HealthSnapshot) -> str:
        a = self._normalize_compare_key(term_a)
        b = self._normalize_compare_key(term_b)
        pair = tuple(sorted([a, b]))

        known = {
            ("anemia", "pdw"): (
                "No — PDW and anemia are not the same.",
                "• PDW (Platelet Distribution Width) is a platelet test — it measures variation in platelet size.",
                "• Anemia is a condition of low red blood cells or hemoglobin (not a single lab line item).",
                "• They are related only in the sense that both come from a blood test panel, but they measure different cell lines.",
                "• RDW is usually more relevant than PDW when investigating anemia.",
            ),
            ("anemia", "rdw"): (
                "No — but they are closely related.",
                "• Anemia means low hemoglobin/red cell mass (fatigue, pallor, low exercise tolerance).",
                "• RDW (Red Cell Distribution Width) measures how much red blood cell size varies.",
                "• High RDW often appears in iron-deficiency or mixed nutritional anemias — so RDW helps explain anemia type, but RDW itself is not anemia.",
            ),
            ("anemia", "rdw-cv"): (
                "No — but they are closely related.",
                "• Anemia means low hemoglobin/red cell mass.",
                "• RDW-CV measures red blood cell size variation; high values can be seen in many anemias.",
                "• A high RDW supports anemia workup but does not by itself confirm anemia — check hemoglobin and PCV too.",
            ),
            ("pdw", "rdw"): (
                "No — they are different lab markers.",
                "• PDW reflects platelet size variation (clotting cell line).",
                "• RDW reflects red blood cell size variation (oxygen-carrying cell line).",
                "• Both can be abnormal in different conditions and should be interpreted with the full CBC.",
            ),
            ("pdw", "rdw-cv"): (
                "No — they are different lab markers.",
                "• PDW = platelet size variation.",
                "• RDW-CV = red blood cell size variation.",
                "• Your report flags both — ask about each separately for disease risk and next steps.",
            ),
            ("hba1c", "glucose"): (
                "No — related but not the same.",
                "• Glucose is a point-in-time blood sugar reading.",
                "• HbA1c is a 3-month average sugar marker.",
                "• Both are used for diabetes screening, but HbA1c is better for long-term control.",
            ),
            ("ldl", "hdl"): (
                "No — both are cholesterol types but opposite in risk meaning.",
                "• LDL is often called 'bad cholesterol' (lower is usually better).",
                "• HDL is often called 'good cholesterol' (higher is usually protective).",
            ),
            ("creatinine", "urea"): (
                "No — different kidney markers from the same panel.",
                "• Creatinine reflects muscle metabolism and kidney filtration.",
                "• Urea reflects protein breakdown and kidney clearance.",
                "• Both rise when kidney function drops, but they are not the same test.",
            ),
        }

        metric_a = self._find_metric_for_term(term_a, snapshot)
        metric_b = self._find_metric_for_term(term_b, snapshot)

        if pair in known:
            lines = list(known[pair])
        else:
            lines = [
                f"No — {term_a} and {term_b} are not the same thing.",
                f"• {term_a}: {self.explain_medical_term(term_a)}",
                f"• {term_b}: {self.explain_medical_term(term_b)}",
                "• They may appear in the same report but measure different aspects of health.",
            ]

        if metric_a:
            lines.append(f"\nYour {metric_a.metric_name}: {metric_a.metric_value} {metric_a.unit}")
        if metric_b:
            lines.append(f"Your {metric_b.metric_name}: {metric_b.metric_value} {metric_b.unit}")

        lines.append("\nWant disease risks for one of these? Ask: \"what disease is linked to [marker]\"")
        return "\n".join(lines)

    def _abnormal_list_reply(self, abnormal: list[MetricSnapshot]) -> str:
        if not abnormal:
            return "No abnormal markers in your latest uploaded report."
        body = self._format_abnormal_bullets(abnormal, include_count=True)
        return (
            f"{body}\n\n"
            "Next step — pick any marker above:\n"
            "• Ask \"what is PDW\" for a quick explanation\n"
            "• Ask \"what disease is linked to PDW\" for risks, prevention, and treatment"
        )

    def _term_short_reply(self, term: str, snapshot: HealthSnapshot) -> str:
        explanation = self.explain_medical_term(term)
        metric = self._find_metric_for_term(term, snapshot)
        lines = [f"{term.strip().upper() if len(term.strip()) <= 6 else term.strip()}", explanation]
        if metric:
            ref = ""
            if metric.reference_min is not None and metric.reference_max is not None:
                ref = f" (reference {metric.reference_min}-{metric.reference_max} {metric.unit})"
            status = "above reference" if metric.is_abnormal else "within reference"
            lines.append(f"\nYour value: {metric.metric_value} {metric.unit} — {status}{ref}.")
        lines.append(
            "\nWant disease risks, prevention, and treatment? Ask: "
            f"\"what disease is linked to {term.strip()}\""
        )
        return "\n".join(lines)

    def _term_explanation_reply(self, term: str, snapshot: HealthSnapshot) -> str:
        return self._term_short_reply(term, snapshot)

    def _snapshot_to_prompt(self, snapshot: HealthSnapshot) -> list[str]:
        lines: list[str] = []
        if snapshot.recent_report_titles:
            lines.append("Reports on file: " + ", ".join(snapshot.recent_report_titles))
        for m in snapshot.metrics[:15]:
            ref = ""
            if m.reference_min is not None and m.reference_max is not None:
                ref = f" (reference {m.reference_min}-{m.reference_max})"
            flag = "ABNORMAL" if m.is_abnormal else "in range"
            lines.append(f"- {m.metric_name}: {m.metric_value} {m.unit}{ref} [{flag}]")
        return lines

    def _abnormal_for_reply(self, snapshot: HealthSnapshot) -> list[MetricSnapshot]:
        abnormal = snapshot.abnormal_metrics
        if snapshot.recent_report_titles:
            latest_title = snapshot.recent_report_titles[0]
            latest_abnormal = [m for m in abnormal if m.report_title == latest_title]
            if latest_abnormal:
                abnormal = latest_abnormal

        deduped: list[MetricSnapshot] = []
        seen: set[str] = set()
        for metric in abnormal:
            key = metric.metric_name.strip().lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(metric)
        return deduped

    def _format_abnormal_bullets(self, abnormal: list[MetricSnapshot], *, include_count: bool = True) -> str:
        if not abnormal:
            return "No abnormal markers flagged in your uploaded reports yet."

        lines: list[str] = []
        if include_count:
            label = "signal" if len(abnormal) == 1 else "signals"
            lines.append(f"You have {len(abnormal)} abnormal {label} outside the reference range:")
        else:
            lines.append("Your flagged values:")

        for metric in abnormal:
            ref = ""
            if metric.reference_min is not None and metric.reference_max is not None:
                ref = f" (ref {metric.reference_min}-{metric.reference_max} {metric.unit})".strip()
            elif metric.unit:
                ref = f" ({metric.unit})"
            direction = "high" if metric.reference_max is not None and metric.metric_value > metric.reference_max else (
                "low" if metric.reference_min is not None and metric.metric_value < metric.reference_min else "out of range"
            )
            lines.append(f"• {metric.metric_name}: {metric.metric_value} {metric.unit} — {direction}{ref}")

        return "\n".join(lines)

    def _format_abnormal_summary(self, abnormal: list[MetricSnapshot]) -> str:
        if not abnormal:
            return ""
        return self._format_abnormal_bullets(abnormal, include_count=True)

    def _is_abnormal_list_question(self, msg: str) -> bool:
        if any(
            phrase in msg
            for phrase in (
                "abnormal",
                "flagged",
                "outside reference",
                "out of range",
                "how many",
            )
        ):
            return True
        return bool(
            re.search(r"\b(bullet|list|signals?)\b", msg, flags=re.IGNORECASE)
        )

    def _normalize_msg(self, message: str) -> str:
        msg = (
            message.strip()
            .lower()
            .replace("cholestrol", "cholesterol")
            .replace("colesterol", "cholesterol")
        )
        return self._collapse_dotted_abbrev(msg)

    def _find_metrics_by_keywords(self, snapshot: HealthSnapshot, keywords: list[str]) -> list[MetricSnapshot]:
        matches: list[MetricSnapshot] = []
        seen: set[str] = set()
        for metric in snapshot.metrics:
            name = metric.metric_name.lower()
            if any(keyword in name for keyword in keywords):
                key = self._metric_identity(metric)
                if key in seen:
                    continue
                seen.add(key)
                matches.append(metric)
        return matches

    @staticmethod
    def _metric_identity(metric: MetricSnapshot) -> str:
        return f"{metric.metric_name}:{metric.metric_value}"

    def _match_metric_in_message(self, msg: str, snapshot: HealthSnapshot) -> MetricSnapshot | None:
        for metric in snapshot.metrics:
            name = metric.metric_name.lower()
            if name in msg or name.split()[0] in msg:
                return metric

        alias_map = {
            "sugar": ["glucose", "fbs", "ppbs", "hba1c"],
            "cholesterol": ["cholesterol", "ldl", "hdl", "triglyceride", "vldl"],
            "ldl": ["ldl"],
            "hdl": ["hdl"],
            "bp": ["systolic", "diastolic"],
            "kidney": ["creatinine", "urea", "bun"],
            "liver": ["alt", "ast", "bilirubin"],
            "thyroid": ["tsh", "t3", "t4"],
            "vitamin d": ["vitamin d", "25 - oh vitamin d", "25-oh"],
            "vit d": ["vitamin d", "25 - oh vitamin d"],
            "vitamin b12": ["vitamin b12", "b12"],
            "b12": ["vitamin b12", "b12"],
            "iron": ["hemoglobin", "haemoglobin", "ferritin"],
            "anemia": ["hemoglobin", "haemoglobin", "pcv"],
        }
        for alias, targets in alias_map.items():
            if alias not in msg:
                continue
            for metric in snapshot.metrics:
                name = metric.metric_name.lower()
                if any(target in name for target in targets):
                    return metric
        return None

    def _cholesterol_reply(self, snapshot: HealthSnapshot) -> str | None:
        lipid_order = [
            "total cholesterol",
            "ldl cholesterol",
            "hdl cholesterol",
            "non-hdl cholesterol",
            "triglycerides",
            "vldl cholesterol",
        ]
        by_name = {metric.metric_name.lower(): metric for metric in snapshot.metrics}
        lipid_metrics = [by_name[name] for name in lipid_order if name in by_name]
        if not lipid_metrics:
            lipid_metrics = self._find_metrics_by_keywords(snapshot, lipid_order)
        if not lipid_metrics:
            return None

        lines = ["Here is your lipid profile from uploaded reports:"]
        abnormal: list[MetricSnapshot] = []
        for metric in lipid_metrics:
            status = "above reference" if metric.is_abnormal else "in range"
            lines.append(f"• {metric.metric_name}: {metric.metric_value} {metric.unit} ({status})")
            if metric.is_abnormal:
                abnormal.append(metric)

        focus = abnormal[0] if abnormal else lipid_metrics[0]
        steps = self._reduction_steps_for_metric(focus.metric_name)
        lines.append("")
        if abnormal:
            lines.append(
                f"Main concern: {focus.metric_name} is elevated. {steps} "
                "Repeat lipids in 8-12 weeks and review with your clinician."
            )
        else:
            lines.append(
                f"Your cholesterol panel looks mostly in range. {steps} "
                "Keep monitoring with annual labs or sooner if your doctor advises."
            )
        return "\n".join(lines)

    def _vitamin_reply(self, snapshot: HealthSnapshot, vitamin: str = "d") -> str | None:
        if vitamin == "d":
            names = ["vitamin d (25 - oh vitamin d)", "vitamin d - 25 hydroxy (d2+d3)"]
            label = "Vitamin D"
        else:
            names = ["vitamin b12"]
            label = "Vitamin B12"

        by_name = {metric.metric_name.lower(): metric for metric in snapshot.metrics}
        metric = next((by_name[name] for name in names if name in by_name), None)
        if metric is None:
            metric = next(
                (m for m in snapshot.metrics if vitamin == "d" and "vitamin d" in m.metric_name.lower()),
                None,
            )
        if metric is None:
            metric = next(
                (m for m in snapshot.metrics if vitamin == "b12" and "vitamin b12" in m.metric_name.lower()),
                None,
            )
        if metric is None:
            return None

        status = "below reference" if metric.is_abnormal else "in range"
        steps = self._guidance_steps_for_metric(metric.metric_name, increase=metric.is_abnormal)
        return (
            f"Your {label} from uploaded reports: {metric.metric_value} {metric.unit} ({status}). "
            f"{steps}"
        )

    def _metric_answer(self, metric: MetricSnapshot, msg: str) -> str:
        wants_increase = any(word in msg for word in ("increase", "boost", "raise", "low", "improve"))
        wants_decrease = any(word in msg for word in ("reduce", "lower", "high", "control"))
        if metric.is_abnormal and metric.reference_max is not None and metric.metric_value > metric.reference_max:
            direction_increase = False
        elif metric.is_abnormal and metric.reference_min is not None and metric.metric_value < metric.reference_min:
            direction_increase = True
        else:
            direction_increase = wants_increase and not wants_decrease

        steps = self._guidance_steps_for_metric(metric.metric_name, increase=direction_increase)
        flag = "above reference" if metric.is_abnormal and not direction_increase else (
            "below reference" if metric.is_abnormal else "within reference"
        )
        return (
            f"{metric.metric_name}: {metric.metric_value} {metric.unit} ({flag}). "
            f"{steps} Recheck labs in 8-12 weeks and discuss with your clinician."
        )

    def _offline_copilot_reply(
        self,
        user_message: str,
        snapshot: HealthSnapshot,
        citations: list[str],
        chat_history: list[tuple[str, str]] | None = None,
    ) -> str:
        msg = self._normalize_msg(user_message)
        history = list(chat_history or [])
        abnormal = self._abnormal_for_reply(snapshot)
        abnormal_summary = self._format_abnormal_summary(abnormal)

        if self._is_more_abnormal_question(msg):
            return self._abnormal_list_reply(abnormal)

        topic = self._resolve_conversation_topic(msg, history, snapshot)
        if topic and self._wants_disease_detail(msg):
            return self._condition_deep_reply(topic, snapshot)

        if msg in {"hi", "hello", "hey", "hii", "yo"}:
            return "Hi! I am your health copilot. Ask \"what are my abnormal values\" to see flagged labs first."

        if msg in {"ok", "okay", "thanks", "thank you"}:
            return "Ask \"what are my abnormal values\" or pick a marker like \"what is PDW\"."

        if self._is_abnormal_list_question(msg):
            return self._abnormal_list_reply(abnormal)

        if self._is_comparison_question(msg):
            terms = self._extract_comparison_terms(msg)
            if terms:
                return self._comparison_reply(terms[0], terms[1], snapshot)

        if self._is_definition_question(msg):
            term = self._extract_term_from_question(msg)
            if term and not self._is_vague_term(term):
                return self._term_short_reply(term, snapshot)

        if any(keyword in msg for keyword in ("cholesterol", "ldl", "hdl", "triglyceride", "lipid", "vldl")):
            lipid_reply = self._cholesterol_reply(snapshot)
            if lipid_reply:
                return lipid_reply

        if "vitamin d" in msg or "vit d" in msg:
            vitamin_reply = self._vitamin_reply(snapshot, vitamin="d")
            if vitamin_reply:
                return vitamin_reply

        if "vitamin b12" in msg or "b12" in msg:
            vitamin_reply = self._vitamin_reply(snapshot, vitamin="b12")
            if vitamin_reply:
                return vitamin_reply

        targeted = self._match_metric_in_message(msg, snapshot)
        if targeted and self._is_action_question(msg):
            return self._metric_answer(targeted, msg)

        if any(keyword in msg for keyword in ("reduce", "kam", "lower", "control", "improve", "increase", "boost")) and abnormal:
            steps = self._reduction_plan_for_abnormals(abnormal)
            return f"{abnormal_summary} {steps}"

        if ("high" in msg or "low" in msg) and abnormal:
            return self._abnormal_list_reply(abnormal)

        if "trend" in msg or "history" in msg:
            if snapshot.metrics:
                names = ", ".join(m.metric_name for m in snapshot.metrics[:5])
                return f"Recent tracked metrics: {names}. Use the trend chart for a specific metric name."
            return "Upload a report first so I can track trends."

        if not snapshot.metrics:
            return "Upload a medical report first — then I can use your real lab values in answers."

        return (
            "I did not fully catch that. Try:\n"
            "• \"what are my abnormal values\"\n"
            "• \"what is RDW\" or \"what does RDW mean\"\n"
            "• \"is RDW and anemia the same?\"\n"
            "• \"what disease is linked to RDW\""
        )

    def _guidance_steps_for_metric(self, metric_name: str, increase: bool = False) -> str:
        if increase:
            return self._increase_steps_for_metric(metric_name)
        return self._reduction_steps_for_metric(metric_name)

    def _increase_steps_for_metric(self, metric_name: str) -> str:
        n = metric_name.lower()
        if "vitamin d" in n:
            return (
                "Steps: safe sun exposure, vitamin D rich foods (eggs, fatty fish, fortified dairy), "
                "and clinician-guided supplementation. Retest after 8-12 weeks."
            )
        if "vitamin b12" in n or "b12" in n:
            return "Steps: B12 foods (eggs, dairy, fish) if diet allows; confirm absorption issues; supplement per clinician if deficient."
        if "hemoglobin" in n or "haemoglobin" in n or "hb" in n:
            return "Steps: check iron/B12/folate with your doctor, treat underlying cause, and use iron-rich foods only if appropriate."
        if "hdl" in n:
            return "Steps: regular aerobic exercise, healthy fats (nuts, olive oil), quit smoking, and limit refined carbs."
        return "Steps: discuss the target range with your clinician and follow a personalized plan based on repeat labs."

    def _reduction_steps_for_metric(self, metric_name: str) -> str:
        n = metric_name.lower()
        if "glucose" in n or "sugar" in n or "hba1c" in n or "eag" in n:
            return "Steps: cut refined carbs and sugary drinks, walk 15-20 min after meals, sleep 7-8h, avoid late snacking."
        if "ldl" in n or "cholesterol" in n:
            return "Steps: reduce fried foods and saturated fat, add fiber (oats, dal, vegetables), daily brisk walk, take statin only if prescribed."
        if "triglyceride" in n or "tg" in n or "vldl" in n:
            return "Steps: limit sugar and alcohol, choose whole grains, increase activity, maintain healthy weight."
        if "creatinine" in n or "egfr" in n or "urea" in n:
            return "Steps: control BP and blood sugar, stay hydrated, avoid unnecessary painkillers (NSAIDs), limit very high protein loads unless advised."
        if "hemoglobin" in n or "hb" in n or "haemoglobin" in n:
            return "Steps: check iron/B12 with your doctor, eat iron-rich foods if appropriate, rule out blood loss or chronic causes."
        if "vitamin d" in n:
            return "Steps: safe sun exposure if suitable, vitamin D foods/supplements per clinician guidance, repeat level after supplementation."
        return "Steps: improve diet quality, daily activity, sleep, stress management, and medication adherence as prescribed."

    def _reduction_plan_for_abnormals(self, abnormal: list[MetricSnapshot]) -> str:
        tips: list[str] = []
        seen: set[str] = set()
        for metric in abnormal[:4]:
            key = metric.metric_name.lower().split()[0]
            if key in seen:
                continue
            seen.add(key)
            tips.append(self._reduction_steps_for_metric(metric.metric_name))
        return " ".join(tips)
