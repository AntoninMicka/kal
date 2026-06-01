import os
import calendar
import argparse
import base64
import mimetypes
import datetime
try:
    import cairosvg
    from pypdf import PdfWriter
except ImportError:
    print("Chyba: Chybí potřebné knihovny. Nainstalujte je pomocí:")
    print("pip install cairosvg pypdf")
    exit(1)

# Databáze českých jmenin (index 0 je prázdný, aby indexy odpovídaly dnům v měsíci)
JMENINY = [
    [], # 0 (dummy)
    ["", "Nový rok", "Karina", "Radmila", "Diana", "Dalimil", "Tři králové", "Vilma", "Čestmír", "Vladan", "Břetislav", "Bohdana", "Pravoslav", "Edita", "Radovan", "Alice", "Ctirad", "Drahoslav", "Vladislav", "Doubravka", "Ilona", "Běla", "Slavomír", "Zdeněk", "Milena", "Miloš", "Zora", "Ingrid", "Otýlie", "Zdislava", "Robin", "Marika"], # 1 Leden
    ["", "Hynek", "Nela", "Blažej", "Jarmila", "Dobromila", "Vanda", "Veronika", "Milada", "Apolena", "Mojmír", "Božena", "Slavěna", "Věnceslav", "Valentýn", "Jiřina", "Ljuba", "Miloslava", "Gizela", "Patrik", "Oldřich", "Lenka", "Petr", "Svatopluk", "Matěj", "Liliana", "Dorota", "Alexandr", "Lumír", "Horymír"], # 2 Únor
    ["", "Bedřich", "Anežka", "Kamil", "Stela", "Kazimír", "Miroslav", "Tomáš", "Gabriela", "Františka", "Viktorie", "Anděla", "Řehoř", "Růžena", "Rút", "Ida", "Elena", "Vlastimil", "Eduard", "Josef", "Světlana", "Radek", "Leona", "Ivona", "Gabriel", "Marián", "Emanuel", "Dita", "Soňa", "Taťána", "Arnošt", "Kvido"], # 3 Březen
    ["", "Hugo", "Erika", "Richard", "Ivana", "Miroslava", "Vendula", "Heřman", "Ema", "Dušan", "Darja", "Izabela", "Julius", "Aleš", "Vincenc", "Anastázie", "Irena", "Rudolf", "Valérie", "Rostislav", "Marcela", "Alexandra", "Evženie", "Vojtěch", "Jiří", "Marek", "Oto", "Jaroslav", "Vlastislav", "Robert", "Blahoslav"], # 4 Duben
    ["", "Svátek práce", "Zikmund", "Alexej", "Květoslav", "Klaudie", "Radoslav", "Stanislav", "Den vítězství", "Ctibor", "Blažena", "Svatava", "Pankrác", "Servác", "Bonifác", "Žofie", "Přemysl", "Aneta", "Nataša", "Ivo", "Zbyšek", "Monika", "Emil", "Vladimír", "Jana", "Viola", "Filip", "Valdemar", "Vilém", "Maxmilián", "Ferdinand", "Kamila"], # 5 Květen
    ["", "Laura", "Jarmil", "Tamara", "Dalibor", "Dobroslav", "Norbert", "Iveta", "Medard", "Stanislava", "Gita", "Bruno", "Antonie", "Antonín", "Roland", "Vít", "Zbyněk", "Adolf", "Milan", "Leoš", "Květa", "Alois", "Pavla", "Zdeňka", "Jan", "Ivan", "Adriana", "Ladislav", "Lubomír", "Pavel", "Šárka"], # 6 Červen
    ["", "Jaroslava", "Patricie", "Radomír", "Prokop", "Cyril/Metoděj", "Jan Hus", "Bohuslava", "Nora", "Drahoslava", "Libuše", "Olga", "Bořek", "Markéta", "Karolína", "Jindřich", "Luboš", "Martina", "Drahomíra", "Čeněk", "Ilja", "Vítězslav", "Magdaléna", "Libor", "Kristýna", "Jakub", "Anna", "Věroslav", "Viktor", "Marta", "Bořivoj", "Ignác"], # 7 Červenec
    ["", "Oskar", "Gustav", "Miluše", "Dominik", "Kristián", "Oldřiška", "Lada", "Soběslav", "Roman", "Vavřinec", "Zuzana", "Klára", "Alena", "Alan", "Hana", "Jáchym", "Petra", "Helena", "Ludvík", "Bernard", "Johana", "Bohuslav", "Sandra", "Bartoloměj", "Radim", "Luděk", "Otakar", "Augustýn", "Evelína", "Vladěna", "Pavlína"], # 8 Srpen
    ["", "Linda", "Adéla", "Bronislav", "Jindřiška", "Boris", "Boleslav", "Regína", "Mariana", "Daniela", "Irma", "Denisa", "Marie", "Lubor", "Radka", "Jolana", "Ludmila", "Naděžda", "Kryštof", "Zita", "Oleg", "Matouš", "Darina", "Berta", "Jaromír", "Zlata", "Andrea", "Jonáš", "Václav", "Michal", "Jeroným"], # 9 Září
    ["", "Igor", "Olívie", "Bohumil", "František", "Eliška", "Hanuš", "Justýna", "Věra", "Štefan", "Marina", "Andrej", "Marcel", "Renáta", "Agáta", "Tereza", "Havel", "Hedvika", "Lukáš", "Michaela", "Vendelín", "Brigita", "Sabina", "Teodor", "Nina", "Beáta", "Erik", "Šarlota", "Státní svátek", "Silvie", "Tadeáš", "Štěpánka"], # 10 Říjen
    ["", "Felix", "Tobiáš", "Hubert", "Karel", "Miriam", "Liběna", "Saskie", "Bohumír", "Bohdan", "Evžen", "Martin", "Benedikt", "Tibor", "Sáva", "Leopold", "Otmar", "Mahulena", "Romana", "Alžběta", "Nikola", "Albert", "Cecílie", "Klement", "Emílie", "Kateřina", "Artur", "Xenie", "René", "Zina", "Ondřej"], # 11 Listopad
    ["", "Iva", "Blanka", "Svatoslav", "Barbora", "Jitka", "Mikuláš", "Ambrož", "Květoslava", "Vratislav", "Julie", "Dana", "Simona", "Lucie", "Lýdie", "Radana", "Albína", "Daniel", "Miloslav", "Ester", "Dagmar", "Natálie", "Šimon", "Vlasta", "Adam a Eva", "1. svátek", "Štěpán", "Žaneta", "Bohumila", "Judita", "David", "Silvestr"]  # 12 Prosinec
]

def vypocet_velikonoc(rok):
    a = rok % 19
    b = rok // 100
    c = rok % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mesic = (h + l - 7 * m + 114) // 31
    den = ((h + l - 7 * m + 114) % 31) + 1
    return datetime.date(rok, mesic, den)

def ziskej_statni_svatky(rok):
    vn = vypocet_velikonoc(rok)
    vp = vn - datetime.timedelta(days=2) # Velký pátek
    vpo = vn + datetime.timedelta(days=1) # Velikonoční pondělí

    return {
        (1, 1), (5, 1), (5, 8), (7, 5), (7, 6),
        (9, 28), (10, 28), (11, 17),
        (12, 24), (12, 25), (12, 26),
        (vp.month, vp.day),
        (vpo.month, vpo.day)
    }

def main():
    parser = argparse.ArgumentParser(description="Generátor jednoho PDF kalendáře z obrázků.")
    parser.add_argument("rok", type=int, help="Rok, pro který se má kalendář vygenerovat")
    parser.add_argument("-t", "--titulek", type=str, help="Vlastní titulek na úvodní stránku", default=None)
    parser.add_argument("-v", "--velikost", choices=["A4", "A3"], default="A4", help="Velikost výstupního PDF (A4 nebo A3)")
    parser.add_argument("--varianta", choices=["full", "economy"], default="full", help="Varianta zpracování kalendáře (full s průsvitkou, nebo economy 1 str./měsíc)")
    args = parser.parse_args()

    ROK = args.rok
    TITULEK = args.titulek if args.titulek else "KALENDÁŘ"
    VELIKOST = args.velikost
    VARIANTA = args.varianta
    STATNI_SVATKY = ziskej_statni_svatky(ROK)

    if VELIKOST == "A3":
        SVG_W, SVG_H = "297mm", "420mm"
    else:
        SVG_W, SVG_H = "210mm", "297mm"

    MESICE = ["LEDEN", "ÚNOR", "BŘEZEN", "DUBEN", "KVĚTEN", "ČERVEN",
              "ČERVENEC", "SRPEN", "ZÁŘÍ", "ŘÍJEN", "LISTOPAD", "PROSINEC"]

    # Úprava horní šablony: přidán <pattern> pro šrafování, fill=none pro průhlednost a sekce ODEBRAT
    SABLONA_HORNI = """<?xml version="1.0" encoding="UTF-8"?>
<svg width="{w}" height="{h}" viewBox="0 0 210 297" version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
    <defs>
        <pattern id="srafovani" patternUnits="userSpaceOnUse" width="6" height="6">
            <path d="M-1,1 l2,-2 M0,6 l6,-6 M5,7 l2,-2" stroke="#ffcccc" stroke-width="1.5"/>
        </pattern>
    </defs>
    <polygon points="0,0 210,0 210,185 80,185 45,220 0,220" fill="none" stroke="#c0c0c0" stroke-width="0.3"/>

    <polygon points="0,220 45,220 80,185 210,185 210,297 0,297" fill="url(#srafovani)" />
    <text x="145" y="245" text-anchor="middle" font-size="14" font-family="sans-serif" font-weight="bold" fill="#ff0000" letter-spacing="3">ODEBRAT</text>

    {obrazek_svg}
    <text x="22.5" y="210" text-anchor="middle" font-size="8" font-family="sans-serif" font-weight="bold" fill="#303030">{nazev_mesice}</text>
    <line x1="45" y1="220" x2="80" y2="185" stroke="#ff0000" stroke-width="0.3" stroke-dasharray="2,2"/>
</svg>"""

    SABLONA_SPODNI = """<?xml version="1.0" encoding="UTF-8"?>
<svg width="{w}" height="{h}" viewBox="0 0 210 297" version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
    <rect x="0" y="0" width="210" height="297" fill="#303030"/>
    {obrazek_svg}
{kalendarium}
</svg>"""

    # Nová šablona pro variantu economy (1 list na měsíc, bez odřezávání, černý podklad)
    SABLONA_ECONOMY = """<?xml version="1.0" encoding="UTF-8"?>
<svg width="{w}" height="{h}" viewBox="0 0 210 297" version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
    <rect x="0" y="0" width="210" height="297" fill="#303030"/>
    {obrazek_svg}
    <text x="25" y="193" text-anchor="start" font-size="10" font-family="sans-serif" font-weight="bold" fill="#ffffff" letter-spacing="1">{nazev_mesice}</text>
{kalendarium}
</svg>"""

    SABLONA_TITULKA = """<?xml version="1.0" encoding="UTF-8"?>
<svg width="{w}" height="{h}" viewBox="0 0 210 297" version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
    <rect x="0" y="0" width="210" height="297" fill="#f4f4f4"/>
    {obrazek_svg}
    <text x="105" y="210" text-anchor="middle" font-size="12" font-family="sans-serif" font-weight="normal" fill="#505050">{titulek}</text>
    <text x="105" y="235" text-anchor="middle" font-size="28" font-family="sans-serif" font-weight="bold" fill="#303030">{rok}</text>
</svg>"""

    SABLONA_SOUHRN = """<?xml version="1.0" encoding="UTF-8"?>
<svg width="{w}" height="{h}" viewBox="0 0 210 297" version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
    <rect x="0" y="0" width="210" height="297" fill="#f4f4f4"/>
    <text x="105" y="20" text-anchor="middle" font-size="10" font-family="sans-serif" font-weight="bold" fill="#303030">PŘEHLED ROKU {rok}</text>
{miniatury_svg}
</svg>"""

    def najdi_obrazek(prefix, x, y, cw, ch):
        for soubor in os.listdir('.'):
            if soubor.startswith(prefix) and soubor.lower().endswith(('.jpg', '.jpeg', '.png', '.svg')):
                mime_typ, _ = mimetypes.guess_type(soubor)
                if not mime_typ: mime_typ = "image/jpeg"
                with open(soubor, "rb") as img_file:
                    b64_data = base64.b64encode(img_file.read()).decode('utf-8')
                data_uri = f"data:{mime_typ};base64,{b64_data}"
                return f'<image x="{x}" y="{y}" width="{cw}" height="{ch}" href="{data_uri}" xlink:href="{data_uri}" preserveAspectRatio="xMidYMid meet" />'

        return f'''<rect x="{x}" y="{y}" width="{cw}" height="{ch}" fill="none" stroke="#808080" stroke-width="0.5" stroke-dasharray="2,2"/>
    <text x="{x + cw/2}" y="{y + ch/2}" text-anchor="middle" font-size="4" fill="#808080">{prefix}</text>'''

    seznam_pdf = []
    def vygeneruj_stranku(nazev_bez_pripony, svg_data):
        cesta_pdf = f"tmp_{nazev_bez_pripony}.pdf"
        cairosvg.svg2pdf(bytestring=svg_data.encode('utf-8'), write_to=cesta_pdf)
        seznam_pdf.append(cesta_pdf)

    print(f"Generuji kalendář pro rok {ROK} (Varianta: {VARIANTA.upper()})...")

    obrazek_titulka = najdi_obrazek("00", 25, 25, 160, 160)
    vygeneruj_stranku(f"{ROK}_00", SABLONA_TITULKA.format(w=SVG_W, h=SVG_H, titulek=TITULEK, rok=ROK, obrazek_svg=obrazek_titulka))

    miniatury_radky = []

    for mesic_idx, nazev_mesice in enumerate(MESICE, start=1):
        # Obrázek A (hlavní vizuál) vždy potřebujeme
        obrazek_A = najdi_obrazek(f"{mesic_idx:02d}A", 25, 25, 160, 160)

        # Do miniatur použijeme vždy základní vizuál
        mini_x = 20 + ((mesic_idx - 1) % 3) * 60
        mini_y = 35 + ((mesic_idx - 1) // 3) * 60
        miniatury_radky.append(f'    {najdi_obrazek(f"{mesic_idx:02d}A", mini_x, mini_y, 50, 50)}')
        miniatury_radky.append(f'    <text x="{mini_x + 25}" y="{mini_y + 55}" text-anchor="middle" font-size="5" font-family="sans-serif" fill="#303030">{nazev_mesice}</text>')

        dny_v_mesici = calendar.monthcalendar(ROK, mesic_idx)
        kalendarium_radky = []

        x_start, y_start = 95, 198
        col_w, row_h = 17, 14
        dny_v_tydnu = ["Po", "Út", "St", "Čt", "Pá", "So", "Ne"]

        for i, den_zkratka in enumerate(dny_v_tydnu):
            barva = "#ff5555" if i == 6 else "white"
            x_poz = x_start + i * col_w
            kalendarium_radky.append(f'    <text x="{x_poz}" y="{y_start}" font-size="6" text-anchor="middle" font-family="sans-serif" font-weight="bold" fill="{barva}">{den_zkratka}</text>')

        y_start_dny = y_start + 11

        for row_idx, tyden in enumerate(dny_v_mesici):
            for col_idx, den in enumerate(tyden):
                if den == 0: continue

                x_poz = x_start + col_idx * col_w
                y_poz_cislo = y_start_dny + row_idx * row_h
                y_poz_jmeno = y_poz_cislo + 4.5

                je_svatek_nebo_nedele = (mesic_idx, den) in STATNI_SVATKY or col_idx == 6

                barva_cislo = "#ff5555" if je_svatek_nebo_nedele else "white"
                vaha_cislo = "bold" if je_svatek_nebo_nedele else "normal"
                barva_jmeno = "#ffaaaa" if je_svatek_nebo_nedele else "#aaaaaa"

                jmeno_svatek = JMENINY[mesic_idx][den]

                kalendarium_radky.append(f'    <text x="{x_poz}" y="{y_poz_cislo}" font-size="8" text-anchor="middle" font-family="sans-serif" font-weight="{vaha_cislo}" fill="{barva_cislo}">{den}</text>')
                kalendarium_radky.append(f'    <text x="{x_poz}" y="{y_poz_jmeno}" font-size="3" text-anchor="middle" font-family="sans-serif" fill="{barva_jmeno}">{jmeno_svatek}</text>')

        kalendarium_formatovane = "\n".join(kalendarium_radky)

        # -----------------------------------------------
        # ZDE JE ROZCESTNÍK LOGIKY PODLE VARIANTY
        # -----------------------------------------------
        if VARIANTA == "full":
            # Potřebujeme i B obrázek pro druhou vrstvu
            obrazek_B = najdi_obrazek(f"{mesic_idx:02d}B", 25, 25, 160, 160)
            vygeneruj_stranku(f"{ROK}_{mesic_idx:02d}A", SABLONA_HORNI.format(w=SVG_W, h=SVG_H, nazev_mesice=nazev_mesice, obrazek_svg=obrazek_A))
            vygeneruj_stranku(f"{ROK}_{mesic_idx:02d}B", SABLONA_SPODNI.format(w=SVG_W, h=SVG_H, kalendarium=kalendarium_formatovane, obrazek_svg=obrazek_B))
        else:
            # Varianta Economy generuje pouze jednu stránku na měsíc s Ačkovým obrázkem
            vygeneruj_stranku(f"{ROK}_{mesic_idx:02d}", SABLONA_ECONOMY.format(w=SVG_W, h=SVG_H, nazev_mesice=nazev_mesice, obrazek_svg=obrazek_A, kalendarium=kalendarium_formatovane))

    vygeneruj_stranku(f"{ROK}_13", SABLONA_SOUHRN.format(w=SVG_W, h=SVG_H, rok=ROK, miniatury_svg="\n".join(miniatury_radky)))

    print("Spojuji do finálního PDF...")

    # Názvy PDF nyní reflektují zvolenou variantu
    vystupni_pdf = f"Kalendar_{ROK}_{VELIKOST}_{VARIANTA.upper()}.pdf"
    merger = PdfWriter()
    for pdf_soubor in seznam_pdf: merger.append(pdf_soubor)
    with open(vystupni_pdf, "wb") as f_out: merger.write(f_out)
    merger.close()

    for pdf_soubor in seznam_pdf:
        if os.path.exists(pdf_soubor): os.remove(pdf_soubor)

    print(f"Hotovo! Bylo úspěšně vygenerováno kompletní PDF ({len(seznam_pdf)} stran).")
    print(f"Uloženo jako: {vystupni_pdf}")

if __name__ == "__main__":
    main()
