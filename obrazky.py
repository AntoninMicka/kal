import json
import os
import sys
import argparse
import urllib.request
import time
import urllib.parse

# --- KONFIGURACE ---
COMFY_URL = "http://127.0.0.1:8188"
SABLONA_SOUBOR = "double.json"
PROJEKT_SOUBOR = "projekt.json"

def odesli_do_comfy(prompt_data):
    """Odešle JSON graf do API ComfyUI a vrátí ID úlohy."""
    data = json.dumps({"prompt": prompt_data}).encode('utf-8')
    req = urllib.request.Request(f"{COMFY_URL}/prompt", data=data)
    try:
        with urllib.request.urlopen(req) as response:
            odpoved = json.loads(response.read())
            return odpoved['prompt_id']
    except Exception as e:
        print(f"Chyba připojení ke ComfyUI: {e}")
        print("Ujistěte se, že ComfyUI běží a API je dostupné.")
        return None

def cekej_na_dokonceni(prompt_id):
    """Pravidelně se dotazuje ComfyUI, zda už je obrázek vygenerovaný."""
    print("  Generuji obrázky v ComfyUI...", end="", flush=True)
    while True:
        req = urllib.request.Request(f"{COMFY_URL}/history/{prompt_id}")
        try:
            with urllib.request.urlopen(req) as response:
                historie = json.loads(response.read())
                if prompt_id in historie:
                    print(" Hotovo!")
                    return
        except Exception as e:
            print(f"\n  Chyba při dotazování na historii: {e}")
            return

        print(".", end="", flush=True)
        time.sleep(2)

def stahni_obrazky(prompt_id):
    """Zjistí z historie názvy souborů a stáhne je do aktuálního adresáře."""
    req = urllib.request.Request(f"{COMFY_URL}/history/{prompt_id}")
    try:
        with urllib.request.urlopen(req) as response:
            historie = json.loads(response.read())

            # ComfyUI vrací historii pod klíčem daného prompt_id
            if prompt_id in historie:
                vystupy = historie[prompt_id].get("outputs", {})

                # Projdeme všechny uzly (Save Image), které něco vygenerovaly
                for node_id, data_uzlu in vystupy.items():
                    if "images" in data_uzlu:
                        for obrazek in data_uzlu["images"]:
                            nazev = obrazek["filename"]
                            slozka = obrazek["subfolder"]
                            typ = obrazek["type"]

                            # Sestavení URL pro stažení přes API
                            params = urllib.parse.urlencode({"filename": nazev, "subfolder": slozka, "type": typ})
                            download_url = f"{COMFY_URL}/view?{params}"

                            print(f"    Stahuji: {nazev} ... ", end="", flush=True)

                            # Stažení a uložení jako binární soubor do aktuální složky
                            with urllib.request.urlopen(download_url) as img_res:
                                with open(nazev, "wb") as f:
                                    f.write(img_res.read())
                            print("OK")
    except Exception as e:
        print(f"\n  Chyba při stahování obrázků z API: {e}")

def existuji_obrazky(prefix):
    """Zkontroluje, zda v aktuálním adresáři existují soubory s daným prefixem."""
    for soubor in os.listdir('.'):
        if soubor.startswith(prefix) and soubor.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
            return True
    return False

def zeptej_se_na_prepsani(nazev, generovat_vse):
    """Zeptá se uživatele, zda chce přepsat existující soubory."""
    if generovat_vse:
        return True, True
    while True:
        odpoved = input(f"  Obrázky pro '{nazev}' již existují. Přepsat? [A]no / [N]e / [V]še / [U]končit: ").strip().lower()
        if odpoved in ('a', 'ano'): return True, False
        if odpoved in ('n', 'ne'): return False, False
        if odpoved in ('v', 'vše', 'vse'): return True, True
        if odpoved in ('u', 'ukoncit', 'ukončit', 'k', 'konec'):
            print("  Ukončuji skript...")
            sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description="Generátor obrázků pro kalendář v ComfyUI.")
    parser.add_argument("-m", "--mesic", type=int, choices=range(0, 13), help="Číslo měsíce ke generování (0 = titulka, 1-12 = měsíce). Pokud není zadáno, generuje se vše.", default=None)
    args = parser.parse_args()

    print("Načítám soubory...")
    # 1. Načtení šablony jako čistého textu pro snadné nahrazování
    try:
        with open(SABLONA_SOUBOR, "r", encoding="utf-8") as f:
            sablona_text = f.read()
    except FileNotFoundError:
        print(f"Chyba: Soubor {SABLONA_SOUBOR} nebyl nalezen.")
        return

    # 2. Načtení nastavení projektu
    try:
        with open(PROJEKT_SOUBOR, "r", encoding="utf-8") as f:
            projekt = json.load(f)
    except FileNotFoundError:
        print(f"Chyba: Soubor {PROJEKT_SOUBOR} nebyl nalezen.")
        return

    globalni = projekt.get("globalni_promenne", {})
    stranky = projekt.get("stranky", {})

    generovat_vse = False

    # --- ZPRACOVÁNÍ TITULKY ---
    titulka = stranky.get("00_titulka")
    if titulka and (args.mesic is None or args.mesic == 0):
        print("\nZpracovávám: 00_titulka (Titulní strana)")

        prepsat = True
        if existuji_obrazky("00_titulka_"):
            prepsat, generovat_vse = zeptej_se_na_prepsani("00_titulka", generovat_vse)

        if not prepsat:
            print("  Přeskakuji...")
        else:
            prompt_titulka = titulka["prompt"].format(**globalni)
            negativni = titulka.get("negativni", "").format(**globalni)

            aktualni_sablona = sablona_text
            aktualni_sablona = aktualni_sablona.replace("__HLAVNI_PROMPT__", prompt_titulka)
            aktualni_sablona = aktualni_sablona.replace("__NEGATIVNI_PROMPT__", negativni)

            # Šablona vyžaduje inpainting, pro titulku pošleme slepá data
            aktualni_sablona = aktualni_sablona.replace("__EDITACNI_PROMPT__", "empty background")
            aktualni_sablona = aktualni_sablona.replace("__TEXT_MASKY__", "none")

            # Uložíme základ jako titulku, inpaintingový výsledek označíme jako odpad
            aktualni_sablona = aktualni_sablona.replace('"base_"', '"00_titulka_"')
            aktualni_sablona = aktualni_sablona.replace('"edited_"', '"00_odpad_"')

            prompt_json = json.loads(aktualni_sablona)
            prompt_id = odesli_do_comfy(prompt_json)
            if prompt_id:
                cekej_na_dokonceni(prompt_id)
                stahni_obrazky(prompt_id)

    # --- ZPRACOVÁNÍ MĚSÍCŮ ---
    mesice = stranky.get("mesice", {})
    for mesic_id, data_mesice in mesice.items():
        # Pokud byl zadán parametr, přeskočíme měsíce, které neodpovídají volbě
        if args.mesic is not None and args.mesic != int(mesic_id):
            continue

        poznamka = data_mesice.get('poznamka', '')
        print(f"\nZpracovávám měsíc: {mesic_id} ({poznamka})")

        zaklad = data_mesice.get("zaklad", "A")
        if zaklad == "A":
            prefix_zaklad = f"{mesic_id}A"
            prefix_edit = f"{mesic_id}B"
        else:
            prefix_zaklad = f"{mesic_id}B"
            prefix_edit = f"{mesic_id}A"

        prepsat = True
        if existuji_obrazky(f"{prefix_zaklad}_") or existuji_obrazky(f"{prefix_edit}_"):
            prepsat, generovat_vse = zeptej_se_na_prepsani(f"Měsíc {mesic_id}", generovat_vse)

        if not prepsat:
            print("  Přeskakuji...")
            continue

        prompt_A = data_mesice["prompt_A"].format(**globalni)
        prompt_B = data_mesice["prompt_B"].format(**globalni)
        negativni = data_mesice.get("negativni", "").format(**globalni)
        text_masky = data_mesice["editacni_maska"].format(**globalni)

        if zaklad == "A":
            hlavni_prompt = prompt_A
            editacni_prompt = prompt_B
        else:
            hlavni_prompt = prompt_B
            editacni_prompt = prompt_A

        aktualni_sablona = sablona_text
        aktualni_sablona = aktualni_sablona.replace("__HLAVNI_PROMPT__", hlavni_prompt)
        aktualni_sablona = aktualni_sablona.replace("__EDITACNI_PROMPT__", editacni_prompt)
        aktualni_sablona = aktualni_sablona.replace("__TEXT_MASKY__", text_masky)
        aktualni_sablona = aktualni_sablona.replace("__NEGATIVNI_PROMPT__", negativni)

        aktualni_sablona = aktualni_sablona.replace('"base_"', f'"{prefix_zaklad}_"')
        aktualni_sablona = aktualni_sablona.replace('"edited_"', f'"{prefix_edit}_"')

        prompt_json = json.loads(aktualni_sablona)
        prompt_id = odesli_do_comfy(prompt_json)
        if prompt_id:
            cekej_na_dokonceni(prompt_id)
            stahni_obrazky(prompt_id)

    print("\nCelý projekt byl úspěšně zpracován!")

if __name__ == "__main__":
    main()
