# Key Soccer Players & Estimated xG Impact
# Used to penalize teams when these stars are missing from the Starting XI.
# Values represent estimated "WAR" (Wins Above Replacement) converted to Match xG Impact.

KEY_SOCCER_PLAYERS = {
    # --- PREMIER LEAGUE ---
    "Haaland E.": 0.85,  # Man City
    "Salah M.": 0.65,    # Liverpool (Aging but effective)
    "Saka B.": 0.70,     # Arsenal (Prime)
    "Odegaard M.": 0.55, # Arsenal
    "Rodri": 0.60,       # Man City (Critical)
    "Palmer C.": 0.65,   # Chelsea (Superstar)
    "Watkins O.": 0.55,  # Aston Villa
    "Isak A.": 0.55,     # Newcastle
    "Fernandes B.": 0.45,# Man Utd

    # --- LA LIGA ---
    "Mbappe K.": 0.90,   # Real Madrid (Peak)
    "Vinicius Jr.": 0.80,# Real Madrid
    "Bellingham J.": 0.75,# Real Madrid
    "Yamal L.": 0.75,    # Barcelona (Gen-Z Icon)
    "Griezmann A.": 0.50,# Atletico

    # --- BUNDESLIGA ---
    "Kane H.": 0.80,     # Bayern
    "Musiala J.": 0.75,  # Bayern (Prime)
    "Wirtz F.": 0.75,    # Leverkusen (Prime)
    "Openda L.": 0.60,   # Leipzig

    # --- SERIE A ---
    "Martinez L.": 0.70, # Inter
    "Vlahovic D.": 0.60, # Juventus
    "Leao R.": 0.60,     # Milan
    "Kvaratskhelia K.": 0.60, # Napoli

    # --- LIGUE 1 ---
    "Dembele O.": 0.55,  # PSG
    "Hakimi A.": 0.45,   # PSG
    "Barcola B.": 0.55,  # PSG (Rising Star)

    # --- MLS (High Impact in lower tier) ---
    "Messi L.": 1.20,    # Inter Miami (Massive outlier)
    "Suarez L.": 0.80,   # Inter Miami
    "Bouanga D.": 0.65,  # LAFC
    "Cucho Hernandez": 0.65, # Columbus
    "Acosta L.": 0.60    # Cincinnati
}
