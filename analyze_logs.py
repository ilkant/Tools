'''
Python Academy Global

Tämä skripti analysoi järjestelmän lokitiedostoja automaattisesti Pythonin avulla ja tunnistaa virheitä,
epäonnistuneita kirjautumisyrityksiä sekä mahdollisesti epäilyttäviä tapahtumia.
Se luokittelee havaitut tapahtumat, laskee niiden esiintymiskerrat ja näyttää kyseiset rivit analysoinnin
helpottamiseksi. Käytännöllinen ratkaisu lokien nopeaan tarkasteluun ja sellaisten poikkeamien tunnistamiseen,
jotka vaativat tarkempaa tutkimista.
'''

import re
from collections import Counter, defaultdict
from pathlib import Path

PATTERNS = {
    "Erreurs critiques": r"\b(CRITICAL|FATAL|EMERGENCY|PANIC)\b",
    "Erreurs": r"\b(ERROR|ERR|FAILED|FAILURE|EXCEPTION)\b",
    "Avertissements": r"\b(WARNING|WARN)\b",
    "Échecs de connexion": (
        r"failed password|authentication failure|login failed|"
        r"invalid user|access denied|échec de connexion"
    ),
    "Événements suspects": (
        r"unauthorized|permission denied|brute.?force|"
        r"malware|intrusion|suspicious|attack detected"
    ),
}

compiled_patterns = {
    category: re.compile(pattern, re.IGNORECASE)
    for category, pattern in PATTERNS.items()
}

def analyze_logs(file_path):
    path = Path(file_path)
    if not path.is_file():
        print(f"Tiedostoa {file_path} ei löytynyt.\n")
        return

    counts = Counter()
    events = defaultdict(list)
    try:
        with path.open("r", encoding="utf-8", errors="replace") as file:
            for line_number, line in enumerate(file, start=1):
                for category, pattern in compiled_patterns.items():
                    if pattern.search(line):
                        counts[category] += 1
                        events[category].append(
            (line_number, line.strip())
        )
    except OSError as error:
        print(f"Tiedostoa {file_path} ei voitu lukea : {error}\n")
        return

    print(f"Tiedostoanalyysi : {path.name}")
    if not counts:
        print("Sääntöjä vastaavia tapahtumia ei havaittu.\n")
        return

    for category, total in counts.most_common():
        print(f"\n{category} : {total}")
    for number, message in events[category][:5]:
        print(f"Rivi {number} : {message}")
    if total > 5:
        print(f" ... ja {total - 5} muu(t) esiintymä(t).\n")


if __name__ == "__main__":
    logfilebodies = [
        "alternatives", "apport", "auth boot", "bootstrap", "fontconfig", "gpu-manager",
        "gpu-manager-switch", "kern" "prime-offload" "prime-supported", "sddm", "ubuntu-advantage-apt-hook",
        "ubuntu-advantage", "wvdialconf", "Xorg.0", "Xorg.2", "Xorg.3", "dpkg"]

    print("*** Järjestelmän lokitiedsostojen virheet ja varoitukset.")
    for f in logfilebodies:
        file_path = "/var/log/" + f + ".log"
        analyze_logs(file_path)
