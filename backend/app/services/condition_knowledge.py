from typing import TypedDict


class ConditionProfile(TypedDict):
    title: str
    aliases: list[str]
    meaning: str
    risks: list[str]
    prevention: list[str]
    treatment: list[str]


CONDITION_PROFILES: list[ConditionProfile] = [
    {
        "title": "Vitamin D Deficiency",
        "aliases": ["vitamin d", "vit d", "25-oh vitamin d", "vitamin d deficiency"],
        "meaning": "Your body does not have enough vitamin D to support bone health, immunity, and calcium balance.",
        "risks": [
            "Weaker bones and higher fracture risk (osteopenia/osteoporosis)",
            "Muscle weakness, fatigue, and bone pain",
            "Lower immunity and slower recovery from illness",
            "In severe cases, rickets in children or osteomalacia in adults",
        ],
        "prevention": [
            "Safe sun exposure when suitable (10-20 min midday sun on arms/legs)",
            "Eat vitamin D foods: fatty fish, eggs, fortified milk/cereals",
            "Maintain healthy weight and stay physically active",
            "Repeat labs yearly or as your doctor advises if you are at risk",
        ],
        "treatment": [
            "Clinician-guided vitamin D supplementation (dose based on your level)",
            "Retest levels after 8-12 weeks of treatment",
            "Correct calcium intake if needed — do not mega-dose without medical advice",
            "Investigate underlying causes if levels do not improve (malabsorption, kidney/liver issues)",
        ],
    },
    {
        "title": "Vitamin B12 Deficiency",
        "aliases": ["vitamin b12", "b12", "vit b12", "cobalamin"],
        "meaning": "Low B12 reduces healthy red blood cell production and nerve function.",
        "risks": [
            "Megaloblastic anemia (fatigue, breathlessness, pallor)",
            "Numbness, tingling, or balance problems from nerve damage",
            "Memory and mood changes in prolonged deficiency",
            "Severe untreated deficiency can cause irreversible nerve injury",
        ],
        "prevention": [
            "Include B12 sources: eggs, dairy, fish, meat (or fortified foods if vegetarian)",
            "Screen B12 if you are vegan, elderly, or on long-term metformin/PPI medicines",
            "Treat pernicious anemia or absorption issues early if diagnosed",
        ],
        "treatment": [
            "Oral B12 supplements or injections depending on cause and severity",
            "Find and treat root cause (diet, gut absorption, medications)",
            "Repeat CBC and B12 levels to confirm response",
        ],
    },
    {
        "title": "Prediabetes / Elevated Blood Sugar",
        "aliases": ["hba1c", "prediabetes", "high glucose", "glucose", "fasting glucose", "eag", "diabetes risk"],
        "meaning": "Blood sugar is higher than optimal, suggesting insulin resistance or early diabetes risk.",
        "risks": [
            "Progression to type 2 diabetes",
            "Higher risk of heart disease, stroke, and kidney disease",
            "Nerve, eye, and foot complications if sugars stay uncontrolled",
            "Poor wound healing and increased infection risk over time",
        ],
        "prevention": [
            "Cut refined carbs, sugary drinks, and late-night snacking",
            "Walk 15-30 min after meals; aim for 150 min/week activity",
            "Sleep 7-8 hours and manage stress",
            "Maintain healthy weight and monitor labs every 3-6 months",
        ],
        "treatment": [
            "Structured diet (low GI foods, portion control, more fiber)",
            "Metformin or other medicines if prescribed by your doctor",
            "Home glucose monitoring when advised",
            "Annual eye, kidney, and foot screening if diabetes is confirmed",
        ],
    },
    {
        "title": "High Triglycerides (Hypertriglyceridemia)",
        "aliases": ["triglycerides", "tg", "vldl", "vldl cholesterol", "high lipids"],
        "meaning": "Blood fat levels are elevated, often linked to diet, weight, alcohol, or metabolic syndrome.",
        "risks": [
            "Increased heart disease and stroke risk",
            "Pancreatitis risk at very high triglyceride levels",
            "Often occurs with low HDL and insulin resistance",
            "Liver fat buildup (fatty liver) over time",
        ],
        "prevention": [
            "Limit sugar, alcohol, and refined carbohydrates",
            "Choose whole grains, vegetables, and lean protein",
            "Exercise regularly and maintain healthy weight",
            "Control diabetes and blood pressure if present",
        ],
        "treatment": [
            "Therapeutic lifestyle changes are first-line treatment",
            "Omega-3 or fibrate medicines if lifestyle alone is insufficient",
            "Recheck lipid panel in 8-12 weeks",
            "Treat underlying thyroid/diabetes issues if present",
        ],
    },
    {
        "title": "Anemia / Low Hemoglobin",
        "aliases": ["hemoglobin", "haemoglobin", "hb", "pcv", "hematocrit", "anemia", "low rbc"],
        "meaning": "Reduced oxygen-carrying capacity in blood, often from iron, B12, folate loss, or chronic disease.",
        "risks": [
            "Fatigue, dizziness, shortness of breath, poor exercise tolerance",
            "Heart strain if severe and untreated",
            "Poor concentration and reduced productivity",
            "May signal hidden bleeding or chronic illness",
        ],
        "prevention": [
            "Balanced diet with iron, B12, and folate",
            "Screen for anemia in women with heavy periods or during pregnancy",
            "Do not ignore chronic fatigue — check CBC and iron studies",
        ],
        "treatment": [
            "Iron/B12/folate supplements only after confirming the cause",
            "Treat bleeding sources or underlying disease (thyroid, kidney, inflammation)",
            "Repeat hemoglobin and reticulocyte count to monitor recovery",
        ],
    },
    {
        "title": "Kidney Stress / Reduced Kidney Function",
        "aliases": ["creatinine", "urea", "bun", "blood urea nitrogen", "kidney", "renal"],
        "meaning": "Kidney filtration markers are outside optimal range, suggesting reduced clearance or dehydration.",
        "risks": [
            "Fluid imbalance and electrolyte disturbances",
            "Blood pressure complications",
            "Medicine buildup if kidney function worsens",
            "Progression to chronic kidney disease if untreated",
        ],
        "prevention": [
            "Control blood pressure and blood sugar",
            "Stay hydrated; avoid unnecessary NSAID painkillers",
            "Limit very high protein diets unless medically indicated",
            "Regular kidney function tests if diabetic or hypertensive",
        ],
        "treatment": [
            "Treat root causes (BP, diabetes, obstruction, infection)",
            "Adjust medicines that affect kidneys under doctor supervision",
            "Repeat creatinine, eGFR, urine albumin monitoring",
        ],
    },
    {
        "title": "Thyroid Dysfunction Risk",
        "aliases": ["tsh", "thyroid", "t3", "t4", "hypothyroid", "hyperthyroid"],
        "meaning": "Thyroid hormone balance may be off, affecting metabolism, energy, and heart rate.",
        "risks": [
            "Hypothyroid: weight gain, cold intolerance, fatigue, high cholesterol",
            "Hyperthyroid: palpitations, weight loss, anxiety, bone loss",
            "Untreated thyroid disease can affect heart rhythm and pregnancy outcomes",
        ],
        "prevention": [
            "Routine TSH screening if you have symptoms or family history",
            "Ensure adequate iodine in diet (not excess)",
            "Manage stress and get regular checkups",
        ],
        "treatment": [
            "Levothyroxine for hypothyroidism when prescribed",
            "Anti-thyroid therapy or other specialist treatment for hyperthyroidism",
            "Repeat TSH and free T4 until stable on treatment",
        ],
    },
    {
        "title": "Elevated RDW (Red Cell Distribution Width)",
        "aliases": ["rdw", "rdw-cv", "rdw cv", "red cell distribution width"],
        "meaning": "RDW measures how much your red blood cells vary in size. A high RDW often means red cells are not uniform, which can happen in nutritional anemias or mixed blood disorders.",
        "risks": [
            "Often a sign of iron, B12, or folate deficiency rather than a disease by itself",
            "May indicate anemia type — especially when hemoglobin or PCV is also low",
            "Can appear with chronic inflammation, liver disease, or mixed nutritional deficiencies",
            "Alone it is not usually dangerous, but the underlying cause should be evaluated",
        ],
        "prevention": [
            "Balanced diet with iron, B12, folate, and protein",
            "Screen for anemia if you have fatigue, breathlessness, or heavy periods",
            "Manage chronic conditions (thyroid, kidney, inflammation) that affect blood counts",
        ],
        "treatment": [
            "Repeat CBC with hemoglobin, MCV, and iron/B12/folate studies as your doctor advises",
            "Treat the underlying deficiency or condition — not RDW itself",
            "Follow up labs after 8-12 weeks of treatment to confirm improvement",
        ],
    },
    {
        "title": "Platelet Activation (Elevated PDW/MPV)",
        "aliases": ["pdw", "mpv", "platelet"],
        "meaning": "Platelet size variation is increased, which can reflect active clotting turnover or inflammation.",
        "risks": [
            "May accompany higher clotting activity in some cardiovascular conditions",
            "Can appear with infection, inflammation, or bone marrow stress",
            "Must be read with platelet count — not a standalone diagnosis",
        ],
        "prevention": [
            "Manage cardiovascular risk factors (BP, lipids, sugar, smoking)",
            "Treat infections/inflammation promptly",
            "Follow up if platelet count is also abnormal",
        ],
        "treatment": [
            "No specific treatment for PDW alone — treat the underlying cause",
            "Hematology review if platelet count is very high or very low",
            "Repeat CBC if symptoms like easy bruising or clotting occur",
        ],
    },
]


def find_condition_profile(term: str) -> ConditionProfile | None:
    needle = term.strip().lower()
    if not needle:
        return None
    for profile in CONDITION_PROFILES:
        if needle == profile["title"].lower():
            return profile
        if any(needle == alias or alias in needle or needle in alias for alias in profile["aliases"]):
            return profile
    return None


def profile_for_metric_name(metric_name: str) -> ConditionProfile | None:
    return find_condition_profile(metric_name)
