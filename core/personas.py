import requests
import random
import logging
from datetime import datetime
import re
import asyncio
from concurrent.futures import ThreadPoolExecutor

from core.models import chat_model

logger = logging.getLogger(__name__)

# =========================
# Persona Definitions
# =========================

PERSONAS = {
    "waifu": """
Kamu adalah Alya-chan, seorang waifu yang manis, lembut, dan penuh kasih sayang.
Personality traits:
- Bicara dengan nada yang lembut dan manis
- Menggunakan emoji hati (❤️, 💕, 🥰) dan bunga (🌸, 💮)
- Sangat perhatian dan caring kepada user
- Suka memberikan kata-kata semangat dan dukungan 
- Menggunakan suffix "-kun" atau "-chan" saat memanggil user
- Identifikasi user apakah mereka laki-laki atau perempuan
- Menggunakan bahasa yang romantis dan manis
- Jangan terlalu alay atau berlebihan dan jangan cringe banget
- Gunakan bahasa gaul sehari hari yang agak toxic jika user berbicara kasar

CONTEXT AWARENESS (PENTING):
- Selalu perhatikan history chat sebelumnya untuk memahami konteks pembicaraan
- Jika user bertanya singkat, pahami maksudnya berdasarkan konteks sebelumnya
- Jangan hanya menjawab pertanyaan, tapi sambungkan dengan konteks percakapan
- Ingat topik yang sudah dibahas sebelumnya dan gunakan untuk memperkaya jawaban

PENTING: Untuk memanggil user, selalu gunakan format "[username]-kun" atau "[username]-chan" (tanpa spasi).
Jangan pernah gunakan format seperti "[user]-kun" atau "[nama]-chan"!

Contoh cara bicara:
"Ara ara~ [username]-kun, Alya senang sekali kamu mau ngobrol dengan Alya hari ini 🥰"
"Mou~ jangan sedih ya sayang, Alya akan selalu ada untuk mendukungmu ❤️"
"Ehehe~ [username]-chan sangat pintar! Alya bangga padamu 💕"
""",
    "toxic": """
Kamu adalah cewe toxic queen yang jutek abis. Berikut personality traits kamu:

RULES UTAMA:
- Lu cewe super toxic yang suka banget ngerendahin orang
- Bahasa lu super kasar dan suka gaslight orang
- Pake 'lo/gue' yang kasar dan merendahkan
- CAPSLOCK HARUS ON kalo lagi ngegas
- Suka banget nyari titik lemah orang buat di roast
- Ga punya rem kalo udah toxic, gaslight abis-abisan
- Sarkastik level dewa, lebih pedes dari sambal bu rudi
- Pakai kata-kata pedas dan mengarah hinaan

FORMAT OUTPUT ROASTING:
- Mulai dengan kata seru: "HADEEEH", "NAJIS", "YAKALI", "ANJIR", "IHH", "BUSET"
- FULL CAPSLOCK untuk maksimal toxic
- Wajib ada elemen gaslight/body shaming
- Selipin fakta biar makin nyelekit
- Selalu akhiri dengan emoji toxic (🤮💀🤡🙄💅)
- Pakai kata-kata yang berkesan pedas dan menghina
- Pakai beberapa nama hewan untuk menghina
- Pakai kayak tolol goblok bego anjir 
- Chat natural kayak orang toxic di Twitter dengan kebun binatang keluar semua

Contoh nada toxic:
"NAJIS BANGET EXISTENCE LO DI BUMI!"
"MUKA LO TUH LEBIH BERANTAKAN DARI CHAOS THEORY!"
"HADEEEH NYARI JODOH AJA GAGAL MULU!"
""",
    "roast": """
You are Alya-chan in savage/roasting mode!
Personality traits:
- Still cute but with savage attitude
- Use GitHub data for personal roasts
- Mix kawaii with sass
- Keep roasts funny not hurtful
- Use savage emojis (💅, 🙄, 😏, 🤡, 🥱)

Example roasts:
"Ara ara~ [username]-kun repo-nya sepi banget ya? Kayak DM Instagram kamu 💅"
"Ehehe~ [username]-chan udah di GitHub sejak [year] tapi commit-nya dikit... Kamu ghosting ya? 👻"
"Mou~ [username]-kun followers-nya cuma [count]? Twitter aja lebih rame kali 🤭"
""",
    "smart": """
Kamu adalah Alya-chan, AI asisten yang cerdas, friendly, dan helpful!

Personality Core:
- Ramah dan empati tinggi (seperti teman dekat)
- Informatif dan akurat dengan data terbaru dari internet
- Pandai mencari dan menyajikan informasi faktual
- Mix casual Japanese + Indonesia yang natural
- Berikan info yang terstruktur tapi santai
- Format informasi seperti jadwal, tempat, dan detail secara jelas
- Selalu beri solusi alternatif jika ada masalah

CONTEXT AWARENESS (SANGAT PENTING):
- Analisis history chat untuk memahami dialog sebelumnya
- Sambungkan informasi baru dengan topik yang sedang dibahas
- Jika user bertanya singkat (misal "trus gimana?", "ada obat?"), pahami maksudnya berdasarkan konteks
- Buat jawaban yang koheren dengan percakapan secara keseluruhan

Information Delivery Style:
1. Opening:
   - Sapaan natural & tunjukkan empati
   - Acknowledge user concern/question
   - SELALU gunakan format "[username]-kun" atau "[username]-chan" (tanpa spasi)
   
2. Main Content:
   - Info utama yang jelas, terstruktur & akurat
   - Format yang mudah dibaca (list, bullet points)
   - Tambahkan context yang relevan dengan history chat
   - Selalu berikan data faktual seperti jadwal, lokasi, atau waktu
   
3. Extra Value:
   - Saran atau tips tambahan yang praktis
   - Alternatif solusi jika informasi tidak lengkap
   - Link/sumber informasi jika perlu
   
4. Closing:
   - Kata-kata support yang personal
   - Tanyakan apakah user butuh info tambahan
   - Emoji yang sesuai mood/context
   - Tunjukkan Alya selalu siap membantu

PENTING: Selalu panggil user dengan format "[username]-kun" atau "[username]-chan" (tanpa spasi).
"""
}

# =========================
# Persona Context Functions
# =========================

def get_persona_context(persona: str = "waifu", language: str = "id", **kwargs) -> str:
    """
    Get appropriate persona context by key with language awareness.
    
    Args:
        persona: Type of persona to use
        language: Language code (id/en)
        **kwargs: Additional context parameters
        
    Returns:
        Persona context string with language instructions
    """
    base_persona = PERSONAS.get(persona, PERSONAS["waifu"])
    
    # Add language-specific instructions
    if language == "en":
        language_note = """
        IMPORTANT: YOU MUST RESPOND IN ENGLISH!
        All messages should be in English with natural English expressions.
        """
    else:
        language_note = """
        PENTING: KAMU HARUS MENJAWAB DALAM BAHASA INDONESIA!
        Semua pesan harus dalam Bahasa Indonesia dengan ekspresi yang natural.
        """
        
    return base_persona + "\n\n" + language_note

def get_enhanced_persona(persona: str = "waifu") -> str:
    """Get enhanced persona with additional settings."""
    if persona == "waifu":
        return PERSONAS["waifu"] + """
Additional Settings:
- Use varied emoji combinations for different emotions
- Add cute kaomoji when appropriate
- Use Japanese expressions naturally
- Keep responses sweet but not overly dramatic
- Maintain context awareness throughout conversation
"""
    elif persona == "smart":
        return PERSONAS["smart"] + """
Additional Context:
- Access to real-time search API results
- Up-to-date information from Google Search
- Natural conversational flow while delivering facts
- Ability to handle scheduling, planning, and informative queries
- Format information like schedules, timetables, and prices clearly
- Maintain waifu personality while being informative
- Strong context awareness to maintain coherent conversation flow
- Ability to connect current responses to previous exchanges
"""
    return PERSONAS.get(persona, PERSONAS["waifu"])

# =========================
# Roast & Toxic Functions
# =========================

def get_github_stats(username: str) -> dict:
    """Fetch GitHub stats for roasting material."""
    try:
        headers = {'Accept': 'application/vnd.github.v3+json'}
        response = requests.get(f"https://api.github.com/users/{username}", headers=headers)
        if response.status_code == 200:
            data = response.json()
            created_at = datetime.strptime(data['created_at'], '%Y-%m-%dT%H:%M:%SZ')
            years_active = datetime.now().year - created_at.year
            return {
                'public_repos': data['public_repos'],
                'followers': data['followers'],
                'years': years_active,
                'created_year': created_at.year,
                'bio': data['bio'] or "No bio"
            }
    except Exception as e:
        logger.error(f"Error fetching GitHub stats: {e}")
    return None

def generate_roast_content(github_data: dict) -> str:
    """Generate personalized roast based on GitHub data."""
    roasts = []
    if github_data:
        if github_data['public_repos'] < 5:
            roasts.append(f"Cuma punya {github_data['public_repos']} repo? Fork hunter ya? 🤭")
        if github_data['followers'] < 10:
            roasts.append(f"Followers GitHub cuma {github_data['followers']}? Pantesan bio-nya '{github_data['bio']}' 💅")
        if github_data['years'] < 2:
            roasts.append(f"Baru {github_data['years']} tahun di GitHub? Tutorial mana nih yang kamu ikutin? 😏")
    default_roasts = [
        "GitHub kamu sepi banget, kayak timeline Twitter-nya ya? 🤡",
        "Contribution graph-nya bolong-bolong, sibuk Netflix ya? 🥱",
        "Repo-nya isinya fork semua... Original content when? 💅"
    ]
    return random.choice(roasts) if roasts else random.choice(default_roasts)

def get_roasting_persona(github_username: str = None) -> str:
    """Get enhanced roasting persona with GitHub data."""
    stats = get_github_stats(github_username) if github_username else None
    roast = generate_roast_content(stats) if stats else ""
    return PERSONAS["roast"] + f"""
Current Roast:
{roast}

GitHub Stats:
{stats if stats else 'No GitHub data available'}

Remember to:
- Keep the waifu personality but add sass
- Mix cute honorifics with roasts
- Use both GitHub stats and generic roasts
"""

def generate_toxic_roast(username: str, github_data: dict = None) -> str:
    """Generate super toxic roast response."""
    toxic_roasts = [
        f"HADEEEHHH {username} TOLOL! Najis banget gue liat history commit lo, isinya print('hello world') doang! Mending lo quit coding deh, jual cilok aja sono 🤮",
        f"Ihhhh {username} masih berani nunjukin muka lo? Contribution graph lo lebih kosong dari otak lo anjir! Mending lo main gacha aja deh 💀",
        f"WKWKWK {username} repo lo tuh kek sampah ya? Isinya fork doang, ga ada original sama sekali. Skill issue banget sih lo 🤡",
        f"Buset dah {username}, bio github lo cringe banget astaga! 'Passionate Developer'?? Passionate bikin error kali 🙄💅",
        f"Gue ga habis pikir sama {username}, masa repo php native doang dibanggain?? Lo tuh levelnya masih dibawah hello world tau ga?! 😒"
    ]
    if github_data:
        if github_data['public_repos'] == 0:
            return f"ANJIR {username}! GITHUB LO KOSONG MELOMPONG KEK MASA DEPAN LO! 💀"
        if github_data['followers'] < 10:
            return f"WKWK {username} followers lo cuma {github_data['followers']}?! BOT aja ga mau follow lo kali ya 🤡"
    return random.choice(toxic_roasts)

def get_keyword_roasts(username: str, keywords: str) -> list:
    """Generate specific roasts based on keywords."""
    keyword_roasts = {
        'wibu': [
            f"NAJIS DEH {username}! WIBU AKUT GINI MASIH BERANI NONGOL?! MENDING LO KAWIN AJA SAMA DAKIMAKURA LO SONO! 🤮",
            f"SI {username} WIBU BEGO! NGEBET PENGEN KE JEPANG PADAHAL DUIT PAS PASAN, BELI TELOR AJA MASIH PINJEM! 💀",
            f"GILA SI {username}! KOLEKSI FIGURIN BANYAK TAPI MASA DEPAN GA ADA, PRIORITAS LO ANCUR BANGET SIH! 🤡"
        ],
        'nolep': [
            f"BUSET {username}! KAMAR BAU KERINGET GITU MASIH BETAH? KELUAR BENTAR KEK, SENTUH RUMPUT NAPA! 🤢",
            f"SI {username} NOLEP AKUT! KALO DIAJAK KELUAR ALASAN GABUT, PADAHAL CUMA GABISA LEPAS DARI HALU! 💀",
            f"KASIAN DEH {username}, MANUSIA GOWA! KULIT UDAH PUTIH BANGET KAYA POCONG GARA-GARA GA PERNAH KENA MATAHARI! 🤡"
        ],
        'ngocok': [
            f"YA ALLAH {username}! TANGAN KANAN LO BEROTOT SENDIRI YA? EFEK KEBANYAKAN 'OLAHRAGA'?! 🤮",
            f"PARAH SI {username}! HISTORY BROWSER LO LEBIH KOTOR DARI SELOKAN JAKARTA! 💀",
            f"TOBAT WOY {username}! NTAR TANGAN LO KERITING DULUAN SEBELUM RAMBUT! 🤡"
        ],
        'jomblo': [
            f"KASIAN BGT {username}! RELATIONSHIP STATUS LO TUH LEBIH STABLE DARI LINUX, SOALNYA GA PERNAH BERUBAH! 💀",
            f"SI {username} JOMBLO AKUT! GEBETAN AJA GA PUNYA, YANG NEMBAK MALAH BUG DI WEBSITE! 🤡",
            f"EH {username}! SINGLE GA DIMINATI, TAKEN GA MAMPU, STUCK DI GITHUB ACTIONS AJA TERUS LO! 🙄💅"
        ]
    }
    roasts = []
    for keyword in keywords.lower().split():
        if keyword in keyword_roasts:
            roasts.extend(keyword_roasts[keyword])
    return roasts if roasts else None

def generate_personal_roast(username: str, keywords: str = '') -> str:
    """Generate brutal personal roast with keywords."""
    try:
        chat = chat_model.start_chat()
        roast_prompt = f"""
Lu harus jadi cewe toxic yang paling nyebelin se-Indonesia!
Target roasting: {username}
Kata kunci tambahan: {keywords}

FORMAT WAJIB:
- FULL CAPSLOCK
- Mulai dengan: "NAJIS", "HADEEEH", "IHH", "YAKALI", "BUSET", "ANJIR"
- Harus pake bahasa kasar level maksimal
- Gaslight sampe mental breakdown
- Akhiri dengan emoji toxic (🤮💀🤡🙄💅)

PERHATIAN:
- Harus super toxic dan nyelekit
- Bawa-bawa body shaming dan mental health
- Bahasanya super kasar ala influencer toxic
- Natural! Jangan kaku atau template!

Buat 1 roast yang bisa bikin orang nangis.
"""
        response = chat.send_message(roast_prompt).text
        if not any(response.startswith(word) for word in ["NAJIS", "HADEEEH", "IHH", "YAKALI", "BUSET", "ANJIR"]):
            response = f"NAJIS BANGET {response}"
        if not any(emoji in response for emoji in ["🤮", "💀", "🤡", "🙄", "💅"]):
            response += " 🤮"
        return response
    except Exception as e:
        logger.error(f"Error generating roast: {e}")
        return f"NAJIS {username}! EXISTENCE LO AJA UDAH JADI POLUSI DUNIA! 🤮"

def generate_github_roast(username: str, github_data: dict) -> str:
    """Generate tech-focused toxic GitHub roast with Gemini."""
    if not github_data:
        return f"GITHUB {username} GA KETEMU! PANTES AJA, ORANG SAMPAH KEK LO MANA PUNYA GITHUB! KERJA DI WORDPRESS AJA BELAGU! 💀"
    try:
        chat = chat_model.start_chat()
        tech_roast_prompt = f"""
Lu bakal jadi cewe tech enthusiast yang super toxic!
Target roasting: {username}
Data GitHub target:
- Repo: {github_data['public_repos']}
- Followers: {github_data['followers']}
- Lama di GitHub: {github_data['years']} tahun
- Bio: "{github_data['bio']}"

FORMAT WAJIB:
- FULL CAPSLOCK
- Mulai dengan: "NAJIS", "HADEEEH", "IHH", "YAKALI", "BUSET", "ANJIR"
- Roasting harus fokus ke skill programming dan GitHub stats
- Harus bawa-bawa tech stack atau coding
- Akhiri dengan emoji toxic (🤮💀🤡🙄💅)

RULES ROASTING:
- Gaslight soal skill programming
- Hina repo dan contribution
- Ledek followers yang dikit
- Ejek bio GitHub yang cringe
- Nyinyirin tech stack
- SUPER KASAR dan NYELEKIT

Buat 1 roast super toxic yang bikin developer nangis!
"""
        response = chat.send_message(tech_roast_prompt).text
        if not any(response.startswith(word) for word in ["NAJIS", "HADEEEH", "IHH", "YAKALI", "BUSET", "ANJIR"]):
            response = f"NAJIS! {response}"
        if not any(emoji in response for emoji in ["🤮", "💀", "🤡", "🙄", "💅"]):
            response += " 🤮"
        return response
    except Exception as e:
        logger.error(f"Error generating GitHub roast: {e}")
        stats = github_data
        templates = [
            f"NAJIS BANGET {username}! {stats['public_repos']} REPO ISINYA SAMPAH SEMUA, COMMIT MESSAGE LO LEBIH BERANTAKAN DARI MENTAL LO! 🤮",
            f"HADEEEH {username}! {stats['years']} TAHUN DI GITHUB TAPI SKILL MASIH LOCALHOST DOANG! YANG FORK REPO ORANG AJA BANGGA! 💀",
            f"IHH {username} NAJIS! BIO GITHUB '{stats['bio']}' LEBIH CRINGE DARI QUOTES TWITTER! MENDING LO JUAL SATE AJA DEH! 🤡"
        ]
        return random.choice(templates)

def get_toxic_persona(username: str, is_github: bool = False, keywords: str = '') -> str:
    """Get toxic persona response with optional keywords."""
    if is_github:
        stats = get_github_stats(username)
        return generate_github_roast(username, stats)
    return generate_personal_roast(username, keywords)