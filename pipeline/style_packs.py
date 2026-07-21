"""Topic-driven style-pack selection — the single Python source of truth.

Mirrors remotion/src/styles.ts (tests/test_style_packs.py keeps the two
registries in sync). Each pack carries:
  base      -- one of documentary/kinetic/editorial/noir; legacy helpers
               (sfx transitions, ambient-bed profiles) branch on this
  wrapper   -- photographic grammar appended to every AI-image prompt
  camera    -- hero-shot (image-to-video) camera grammar
  keywords  -- Hindi + English topic cues; the pack with the most keyword
               hits in the title/topic wins
  frames    -- SceneFrame variants that fit the look (subset of
               motion.FRAME_VARIANTS)
  lower_thirds -- AnimatedLowerThird variants that fit the look

Selection replaces the old `done_count % len(STYLES)` rotation: the LOOK
now follows the TOPIC (mystery -> noir family, space -> cosmos, body ->
medical...) with a no-repeat window over the last N videos, so back-to-back
uploads never wear the same skin. Deterministic: same title + same history
=> same pack.
"""
import hashlib
import os

RECENT_WINDOW = 8

PACKS: dict[str, dict] = {
    # ── The original five ────────────────────────────────────────────────
    "documentary": {
        "base": "documentary",
        "wrapper": ("cinematic documentary photography, dramatic natural "
                    "light, atmospheric haze, shot on 35mm film, subtle film "
                    "grain, muted earth tones"),
        "camera": "slow push-in, drifting atmospheric haze",
        "keywords": [],
        "frames": ("corners", "film"),
        "lower_thirds": ("rail", "underline"),
    },
    "kinetic": {
        "base": "kinetic",
        "wrapper": ("high-contrast editorial photography, deep shadows, one "
                    "strong directional light, bold graphic composition, dark "
                    "background, saturated accent colors"),
        "camera": "dynamic parallax slide, hard light shifting",
        "keywords": [],
        "frames": ("corners", "grid"),
        "lower_thirds": ("pill", "rail"),
    },
    "editorial": {
        "base": "editorial",
        "wrapper": ("muted editorial palette, soft diffused overcast light, "
                    "minimalist composition with negative space, premium "
                    "printed-magazine look"),
        "camera": "measured lateral dolly, soft light",
        "keywords": [],
        "frames": ("film",),
        "lower_thirds": ("underline", "index"),
    },
    "noir": {
        "base": "noir",
        "wrapper": ("black and white fine-art photography, hard chiaroscuro "
                    "lighting, fog, deep blacks, visible grain, brooding mood"),
        "camera": "creeping zoom, fog rolling through frame",
        "keywords": ["रहस्य", "गायब", "लापता", "मर्डर", "अपराध", "जासूस",
                     "गुत्थी", "अनसुलझ", "mystery", "crime"],
        "frames": ("film", "focus"),
        "lower_thirds": ("rail", "underline"),
    },
    "telemetry": {
        "base": "editorial",
        "wrapper": ("scientific expedition photography, precise clinical "
                    "framing, cool ambient light, instrument panels and "
                    "readouts, teal-tinted shadows"),
        "camera": "slow orbital drift, instrument lights blinking",
        "keywords": ["मिशन", "सैटेलाइट", "उपग्रह", "सिग्नल", "प्रोब",
                     "voyager", "टेलीस्कोप", "probe"],
        "frames": ("scanner", "grid"),
        "lower_thirds": ("locator", "index"),
    },

    # ── History / culture ────────────────────────────────────────────────
    "archive": {
        "base": "editorial",
        "wrapper": ("archival documentary look, faded kodachrome tones, dust "
                    "and scratches, aged paper textures, warm tungsten light, "
                    "museum photograph quality"),
        "camera": "slow pan across the frame like examining an old photograph",
        "keywords": ["इतिहास", "सदी", "साल पहले", "राजा", "सम्राट", "युद्ध",
                     "आज़ादी", "ब्रिटिश", "मुग़ल", "history", "empire"],
        "frames": ("film",),
        "lower_thirds": ("index", "underline"),
    },
    "manuscript": {
        "base": "editorial",
        "wrapper": ("ancient illuminated manuscript aesthetic, candlelit "
                    "warm glow, gold leaf accents, deep shadow, sacred "
                    "geometry, old parchment tones"),
        "camera": "candle-flicker light, very slow reverent push-in",
        "keywords": ["पुराण", "वेद", "मंदिर", "शास्त्र", "संस्कृत", "देवता",
                     "ऋषि", "ग्रंथ", "mythology"],
        "frames": ("film", "focus"),
        "lower_thirds": ("underline",),
    },
    "relic": {
        "base": "noir",
        "wrapper": ("archaeological photography, raking golden light over "
                    "stone textures, dust motes in light shafts, weathered "
                    "bronze and marble, museum-grade detail"),
        "camera": "torchlight sweep across carved stone, dust drifting",
        "keywords": ["खंडहर", "सभ्यता", "पुरातत्व", "खुदाई", "पिरामिड",
                     "मोहनजो", "हड़प्पा", "कब्र", "ममी", "ruins", "खोई हुई"],
        "frames": ("film", "focus"),
        "lower_thirds": ("index", "underline"),
    },
    "bazaar": {
        "base": "documentary",
        "wrapper": ("vibrant Indian street photography, saturated marigold "
                    "and rose tones, busy layered composition, festival "
                    "light, joyful color chaos"),
        "camera": "handheld walk through the crowd, colors streaking",
        "keywords": ["त्योहार", "मेला", "खाना", "मसाल", "बाज़ार", "शादी",
                     "परंपरा", "festival", "food", "होली", "दिवाली"],
        "frames": ("corners",),
        "lower_thirds": ("pill", "rail"),
    },
    "terracotta": {
        "base": "documentary",
        "wrapper": ("warm earthen documentary photography, clay and ochre "
                    "palette, golden hour light, honest human textures, "
                    "hand-crafted detail"),
        "camera": "gentle handheld drift, warm dust in the air",
        "keywords": ["गांव", "किसान", "कारीगर", "मिट्टी", "हस्तशिल्प",
                     "हाथ से", "craft", "village"],
        "frames": ("corners",),
        "lower_thirds": ("pill", "rail"),
    },
    "folklore": {
        "base": "noir",
        "wrapper": ("moonlit folk-tale atmosphere, firefly glow, deep indigo "
                    "night, lantern light, mist between trees, storybook "
                    "mystery"),
        "camera": "lantern-lit creep forward, mist curling",
        "keywords": ["कहानी", "किंवदंती", "लोक", "भूत", "श्राप", "आत्मा",
                     "legend", "myth", "डरावन", "शापित"],
        "frames": ("focus", "film"),
        "lower_thirds": ("underline", "locator"),
    },

    # ── Space / physics ──────────────────────────────────────────────────
    "cosmos": {
        "base": "kinetic",
        "wrapper": ("deep space astrophotography, violet nebula glow, "
                    "starfield depth, vast cosmic scale, sharp planetary "
                    "detail, NASA archive quality"),
        "camera": "weightless drift past the subject, stars parallaxing",
        "keywords": ["अंतरिक्ष", "चांद", "चंद्र", "मंगल", "सूरज", "सौर",
                     "ग्रह", "तारा", "तारे", "नासा", "इसरो", "रॉकेट",
                     "ब्रह्मांड", "ब्लैक होल", "आकाशगंगा", "उल्का", "space",
                     "galaxy", "moon", "mars"],
        "frames": ("focus", "aperture"),
        "lower_thirds": ("underline", "locator"),
    },
    "quantum": {
        "base": "kinetic",
        "wrapper": ("abstract physics visualization, violet and teal "
                    "interference patterns, macro crystal detail, light "
                    "refraction, elegant scientific minimalism"),
        "camera": "slow macro rotation, light refracting through the frame",
        "keywords": ["क्वांटम", "परमाणु", "कण", "भौतिक", "आइंस्टीन",
                     "गुरुत्व", "प्रकाश की गति", "physics", "atom", "समय का"],
        "frames": ("aperture", "scanner"),
        "lower_thirds": ("underline", "index"),
    },
    "horizon": {
        "base": "documentary",
        "wrapper": ("golden hour adventure photography, sun flare on the "
                    "horizon, epic scale landscape, warm coral and amber "
                    "sky, human figure small against vastness"),
        "camera": "rising crane move toward the horizon, sun flaring",
        "keywords": ["खोज", "अभियान", "रिकॉर्ड", "सबसे पहले", "एवरेस्ट",
                     "यात्रा", "explorer", "expedition"],
        "frames": ("corners",),
        "lower_thirds": ("rail", "underline"),
    },

    # ── Ocean / water / weather ──────────────────────────────────────────
    "abyss": {
        "base": "noir",
        "wrapper": ("deep sea photography, bioluminescent teal glow in "
                    "black water, submersible floodlight, marine snow "
                    "particles, crushing dark depths"),
        "camera": "submersible glide, floodlight cone sweeping the dark",
        "keywords": ["समुद्र", "सागर", "महासागर", "गहराई", "गहरा", "मछली",
                     "व्हेल", "शार्क", "ऑक्टोपस", "पानी के नीचे", "ocean",
                     "trench", "टाइटैनिक", "पनडुब्बी"],
        "frames": ("scanner", "focus"),
        "lower_thirds": ("locator", "underline"),
    },
    "monsoon": {
        "base": "documentary",
        "wrapper": ("monsoon documentary photography, rain-soaked greens, "
                    "heavy grey sky, mist over forest canopy, wet reflective "
                    "surfaces, humid atmosphere"),
        "camera": "slow tilt through falling rain, mist drifting",
        "keywords": ["बारिश", "मानसून", "नदी", "बाढ़", "जंगल", "पेड़",
                     "जलवायु", "मौसम", "climate", "rain", "अमेज़न"],
        "frames": ("corners", "focus"),
        "lower_thirds": ("rail", "underline"),
    },
    "storm": {
        "base": "kinetic",
        "wrapper": ("extreme weather photography, lightning-lit storm "
                    "clouds, slate grey and electric yellow, wind-whipped "
                    "debris, dramatic supercell scale"),
        "camera": "urgent handheld push against the wind, lightning strobing",
        "keywords": ["तूफान", "चक्रवात", "बिजली", "आंधी", "बवंडर", "cyclone",
                     "tornado", "hurricane"],
        "frames": ("corners", "scanner"),
        "lower_thirds": ("rail", "pill"),
    },
    "glacier": {
        "base": "editorial",
        "wrapper": ("polar expedition photography, ice blue and white "
                    "palette, crisp arctic light, crystalline textures, "
                    "vast frozen minimalism"),
        "camera": "serene aerial glide over ice, breath-fog in the air",
        "keywords": ["बर्फ", "ग्लेशियर", "हिम", "अंटार्कटिका", "आर्कटिक",
                     "ठंड", "हिमालय", "ice", "frozen"],
        "frames": ("focus",),
        "lower_thirds": ("underline",),
    },

    # ── Earth / nature / wildlife ────────────────────────────────────────
    "safari": {
        "base": "documentary",
        "wrapper": ("wildlife documentary photography, long-lens compression, "
                    "khaki and olive savanna tones, dust in golden light, "
                    "animal eye-level intimacy"),
        "camera": "long-lens tracking, heat shimmer, dust kicked into light",
        "keywords": ["जानवर", "शेर", "बाघ", "हाथी", "सांप", "पक्षी",
                     "शिकार", "जीव", "प्रजाति", "animal", "wildlife",
                     "डायनासोर", "जंगली"],
        "frames": ("corners", "film"),
        "lower_thirds": ("rail", "locator"),
    },
    "verdant": {
        "base": "documentary",
        "wrapper": ("macro nature photography, lush chlorophyll greens, "
                    "dew drops, soft dappled forest light, intricate "
                    "botanical detail"),
        "camera": "intimate macro drift, dappled light shifting",
        "keywords": ["पौध", "फूल", "कवक", "बैक्टीरिया", "जीवाणु", "कीड़",
                     "मधुमक्खी", "चींटी", "plant", "फफूंद"],
        "frames": ("focus", "corners"),
        "lower_thirds": ("underline", "rail"),
    },
    "dune": {
        "base": "documentary",
        "wrapper": ("desert photography, rust and sand palette, harsh "
                    "sculpted light, rippled dune textures, heat haze, "
                    "lone-figure scale"),
        "camera": "low glide over rippled sand, heat haze bending light",
        "keywords": ["रेगिस्तान", "रेत", "सहारा", "थार", "सूखा", "desert",
                     "गर्म"],
        "frames": ("corners", "focus"),
        "lower_thirds": ("rail", "index"),
    },
    "ember": {
        "base": "kinetic",
        "wrapper": ("volcanic photography, molten orange against charcoal "
                    "black, ember sparks, glowing fissures, apocalyptic "
                    "drama, heat distortion"),
        "camera": "urgent push toward the glow, embers streaking past",
        "keywords": ["ज्वालामुखी", "लावा", "आग", "भूकंप", "विस्फोट",
                     "तबाही", "आपदा", "volcano", "fire", "disaster"],
        "frames": ("corners", "film"),
        "lower_thirds": ("rail", "pill"),
    },

    # ── Science / body / how-things-work ─────────────────────────────────
    "medical": {
        "base": "editorial",
        "wrapper": ("medical visualization aesthetic, teal-lit anatomical "
                    "detail, clean clinical background, translucent layers, "
                    "microscopic precision"),
        "camera": "clinical orbit around the subject, soft even light",
        "keywords": ["शरीर", "दिमाग", "दिल", "खून", "हड्डी", "आंख", "नींद",
                     "बीमारी", "वायरस", "डॉक्टर", "दवा", "कोशिका", "डीएनए",
                     "dna", "सांस", "पेट", "body", "brain", "मांसपेश"],
        "frames": ("grid", "focus"),
        "lower_thirds": ("underline", "index"),
    },
    "laboratory": {
        "base": "editorial",
        "wrapper": ("modern laboratory photography, cool blue-grey palette, "
                    "glassware and precise instruments, shallow depth of "
                    "field, quiet scientific rigor"),
        "camera": "measured lateral dolly past instruments, focus pulling",
        "keywords": ["प्रयोग", "वैज्ञानिक", "रिसर्च", "अध्ययन", "साइंस",
                     "science", "experiment", "नोबेल", "खोज की"],
        "frames": ("grid",),
        "lower_thirds": ("index", "underline"),
    },
    "blueprint": {
        "base": "editorial",
        "wrapper": ("engineering photography, steel blue palette, technical "
                    "cross-section clarity, precise structural lines, "
                    "draftsman lighting"),
        "camera": "precise mechanical dolly along the structure",
        "keywords": ["कैसे बनता", "कैसे काम", "इंजीनियर", "मशीन", "पुल",
                     "बांध", "सुरंग", "टरबाइन", "इंजन", "तकनीक",
                     "how it works"],
        "frames": ("grid", "scanner"),
        "lower_thirds": ("index", "locator"),
    },
    "circuit": {
        "base": "kinetic",
        "wrapper": ("technology macro photography, emerald circuit-board "
                    "glow on black, fiber optic light trails, server room "
                    "depth, digital precision"),
        "camera": "glide along circuit traces, lights pulsing in waves",
        "keywords": ["एआई", " ai ", "कंप्यूटर", "रोबोट", "इंटरनेट", "चिप",
                     "सॉफ्टवेयर", "स्मार्टफोन", "डिजिटल", "साइबर", "robot"],
        "frames": ("scanner", "grid"),
        "lower_thirds": ("locator", "index"),
    },

    # ── City / modern / dark ─────────────────────────────────────────────
    "neon-vice": {
        "base": "kinetic",
        "wrapper": ("neon night photography, magenta and cyan reflections "
                    "on wet streets, rain bokeh, cyberpunk depth, electric "
                    "city glow"),
        "camera": "smooth gimbal glide through neon reflections",
        "keywords": ["रात की", "नियॉन", "टोक्यो", "वेगास", "क्लब", "गेमिंग",
                     "मेटावर्स", "भविष्य", "future", "नाइटलाइफ"],
        "frames": ("grid", "scanner"),
        "lower_thirds": ("pill", "locator"),
    },
    "metro": {
        "base": "kinetic",
        "wrapper": ("urban infrastructure photography, concrete and safety-"
                    "orange palette, leading lines, megastructure scale, "
                    "overcast industrial light"),
        "camera": "confident dolly along leading lines, scale revealing",
        "keywords": ["शहर", "मेट्रो", "ट्रेन", "सड़क", "इमारत", "गगनचुंबी",
                     "एयरपोर्ट", "मुंबई", "दिल्ली", "city", "मेगा", "पुल का"],
        "frames": ("grid", "corners"),
        "lower_thirds": ("pill", "index"),
    },
    "rustbelt": {
        "base": "documentary",
        "wrapper": ("industrial decay photography, rust and steel patina, "
                    "shafts of light through broken roofs, heavy machinery "
                    "scale, oxidized textures"),
        "camera": "slow reveal through a light shaft, dust suspended",
        "keywords": ["फैक्ट्री", "कारखान", "खदान", "स्टील", "लोहा", "जहाज़",
                     "बंदरगाह", "तेल", "industry", "मशीनें"],
        "frames": ("film", "grid"),
        "lower_thirds": ("rail", "index"),
    },
    "signal": {
        "base": "kinetic",
        "wrapper": ("investigative photojournalism look, hard flash "
                    "contrast, red-and-black urgency, documentary evidence "
                    "framing, grainy realism"),
        "camera": "urgent handheld push-in, hard light snapping",
        "keywords": ["ख़तरा", "खतरा", "चेतावनी", "अलर्ट", "जांच", "साज़िश",
                     "घोटाला", "अपहरण", "warning", "सच्चाई"],
        "frames": ("film", "grid"),
        "lower_thirds": ("pill", "locator"),
    },
}

_LEGACY_BASES = ("documentary", "kinetic", "editorial", "noir")

# ── Pacing DNA: how each pack CUTS ───────────────────────────────────────
# pace  -> multiplier on max shot length AND crossfade weight: snappy packs
#          (<1) cut faster with shorter dissolves, contemplative packs (>1)
#          hold shots longer and dissolve slower.
# chunk -> multiplier on caption max_chars: punchy packs flash short word
#          groups, editorial packs breathe with fuller thought groups.
PACING: dict[str, dict] = {
    "documentary": {"pace": 1.00, "chunk": 1.00},
    "kinetic":     {"pace": 0.75, "chunk": 0.80},
    "editorial":   {"pace": 1.25, "chunk": 1.15},
    "noir":        {"pace": 1.15, "chunk": 1.15},
    "telemetry":   {"pace": 1.10, "chunk": 1.00},
    "archive":     {"pace": 1.20, "chunk": 1.15},
    "manuscript":  {"pace": 1.30, "chunk": 1.15},
    "relic":       {"pace": 1.20, "chunk": 1.15},
    "bazaar":      {"pace": 0.85, "chunk": 0.80},
    "terracotta":  {"pace": 1.00, "chunk": 1.00},
    "folklore":    {"pace": 1.20, "chunk": 1.15},
    "cosmos":      {"pace": 1.10, "chunk": 1.00},
    "quantum":     {"pace": 1.05, "chunk": 1.15},
    "horizon":     {"pace": 0.95, "chunk": 1.00},
    "abyss":       {"pace": 1.15, "chunk": 1.15},
    "monsoon":     {"pace": 1.10, "chunk": 1.00},
    "storm":       {"pace": 0.75, "chunk": 0.80},
    "glacier":     {"pace": 1.30, "chunk": 1.15},
    "safari":      {"pace": 0.95, "chunk": 1.00},
    "verdant":     {"pace": 1.20, "chunk": 1.15},
    "dune":        {"pace": 1.10, "chunk": 1.00},
    "ember":       {"pace": 0.70, "chunk": 0.80},
    "medical":     {"pace": 1.05, "chunk": 1.00},
    "laboratory":  {"pace": 1.20, "chunk": 1.15},
    "blueprint":   {"pace": 1.10, "chunk": 1.00},
    "circuit":     {"pace": 0.90, "chunk": 0.90},
    "neon-vice":   {"pace": 0.80, "chunk": 0.80},
    "metro":       {"pace": 0.90, "chunk": 0.90},
    "rustbelt":    {"pace": 1.10, "chunk": 1.00},
    "signal":      {"pace": 0.75, "chunk": 0.80},
}


def pace_for(name: str) -> float:
    return float(PACING.get(str(name), {}).get("pace", 1.0))


def chunk_scale_for(name: str) -> float:
    return float(PACING.get(str(name), {}).get("chunk", 1.0))


def apply_pacing(cfg: dict, name: str, is_short: bool = False) -> None:
    """Bend the render config to the pack's cutting rhythm (bounded)."""
    pace = pace_for(name)
    video = cfg.setdefault("video", {})
    base_shot = float(video.get("max_shot_seconds", 2.4 if is_short else 5))
    lo, hi = (1.4, 3.6) if is_short else (3.0, 8.0)
    video["max_shot_seconds"] = round(min(max(base_shot * pace, lo), hi), 2)
    base_xfade = float(video.get("crossfade", 0.4))
    video["crossfade"] = round(
        min(max(base_xfade * min(max(pace, 0.8), 1.25), 0.2), 0.7), 3)
    caps = cfg.setdefault("captions", {})
    base_chars = int(caps.get("max_chars", 24 if is_short else 30))
    c_lo, c_hi = (12, 30) if is_short else (18, 40)
    caps["max_chars"] = int(min(max(round(base_chars * chunk_scale_for(name)),
                                    c_lo), c_hi))
    print(f"[style] pacing '{name}': shot<={video['max_shot_seconds']}s, "
          f"xfade={video['crossfade']}s, captions<={caps['max_chars']}ch")


# ── registry lookups (fail-open to sane defaults) ───────────────────────
def base_for(name: str) -> str:
    base = PACKS.get(str(name), {}).get("base", "documentary")
    return base if base in _LEGACY_BASES else "documentary"


def wrapper_for(name: str) -> str:
    return PACKS.get(str(name), PACKS["documentary"])["wrapper"]


def camera_for(name: str) -> str:
    return PACKS.get(str(name), PACKS["documentary"])["camera"]


def frames_for(name: str) -> tuple:
    return tuple(PACKS.get(str(name), PACKS["documentary"])["frames"])


def lower_thirds_for(name: str) -> tuple:
    return tuple(PACKS.get(str(name), PACKS["documentary"])["lower_thirds"])


# ── style history (no-repeat window) ────────────────────────────────────
def recent_styles(path: str, n: int = RECENT_WINDOW) -> list[str]:
    try:
        with open(path, encoding="utf-8") as f:
            lines = [ln.strip() for ln in f if ln.strip()
                     and not ln.startswith("#")]
        return lines[-n:]
    except OSError:
        return []


def record_style(path: str, name: str) -> None:
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{name}\n")
    except OSError as exc:  # never block a run on bookkeeping
        print(f"[style] history append failed ({exc})")


# ── topic-driven selection ──────────────────────────────────────────────
def _score(pack: dict, text: str) -> int:
    return sum(1 for kw in pack.get("keywords", []) if kw.lower() in text)


def select(title: str, extra: str = "", history: list[str] | None = None) -> str:
    """Deterministic: keyword affinity first, then a title-hash tie-break
    among the top scorers, excluding the last RECENT_WINDOW packs used
    (unless that would empty the pool)."""
    text = f"{title} {extra}".lower()
    recent = set(history or [])
    scores = {name: _score(pack, text) for name, pack in PACKS.items()}
    pool = {n: s for n, s in scores.items() if n not in recent} or scores
    best = max(pool.values())
    top = sorted(n for n, s in pool.items() if s == best)
    digest = hashlib.sha256(title.encode("utf-8")).digest()
    return top[int.from_bytes(digest[:4], "big") % len(top)]


def select_and_log(title: str, extra: str, repo_root: str,
                   is_short: bool = False) -> str:
    """Pick the pack for this video against the on-disk history. The pick
    is only recorded later via record_use() once the run succeeds."""
    path = history_path(repo_root, is_short)
    return select(title, extra, recent_styles(path))


def history_path(repo_root: str, is_short: bool = False) -> str:
    fname = "styles_used_shorts.txt" if is_short else "styles_used.txt"
    return os.path.join(repo_root, fname)


def record_use(name: str, repo_root: str, is_short: bool = False) -> None:
    record_style(history_path(repo_root, is_short), name)


# ── per-video render jitter (seeded, python-side knobs) ─────────────────
def _unit(seed: str, key: str) -> float:
    digest = hashlib.sha256(f"{key}:{seed}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / 2 ** 64


def render_jitter(seed: str) -> dict:
    """Structural knobs the manifest carries — the Remotion side adds its
    own cosmetic jitter (variation.ts) from motionSeed. Ranges are narrow:
    editing-rhythm variation, not chaos."""
    return {
        "xfade_mul": 0.80 + _unit(seed, "xfade") * 0.45,     # 0.80-1.25
        "max_shot_mul": 0.85 + _unit(seed, "shot") * 0.35,   # 0.85-1.20
        "overlay_mul": 0.88 + _unit(seed, "overlay") * 0.27, # 0.88-1.15
        "caption_y_off": (_unit(seed, "capy") - 0.5) * 0.04, # ±0.02
        "watermark_off": (_unit(seed, "wm") - 0.5) * 0.04,   # ±0.02
    }
