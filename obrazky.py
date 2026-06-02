import json
import os
import sys
import argparse
import urllib.request
import urllib.error
import time
import urllib.parse
import copy
import random

# --- KONFIGURACE ---
COMFY_URL = "http://127.0.0.1:8188"
PROJEKT_SOUBOR = "projekt.json"

SABLONY = {
    "sdxl": "sdxl.json",
    "flux": "flux.json",
    "qwen": "qwen.json"
}

def odesli_do_comfy(prompt_data):
    """Odešle JSON graf do API ComfyUI a vrátí ID úlohy."""
    data = json.dumps({"prompt": prompt_data}).encode('utf-8')
    req = urllib.request.Request(f"{COMFY_URL}/prompt", data=data)
    try:
        with urllib.request.urlopen(req) as response:
            odpoved = json.loads(response.read())
            return odpoved['prompt_id']
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode('utf-8')
        print(f"\nChyba API ComfyUI ({e.code}): {err_msg}")
        print("  -> Ujistěte se, že Váš JSON graf je uložen v 'API formátu' (Save API Format).")
        return None
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

def bezpecne_nahradit(text, klic, hodnota):
    """Bezpečně nahradí klíč v textu (s escapováním uvozovek pro vložení do JSONu)."""
    escapovana = json.dumps(hodnota)[1:-1]
    return text.replace(klic, escapovana)

def nahrad_a_nacti(sablona_text, hlavni, negativni, edit, maska, prefix_base, prefix_edit):
    """Univerzální funkce, která textově nahradí proměnné a zrandomizuje seedy ve výsledném JSONu."""
    s = sablona_text
    s = bezpecne_nahradit(s, "__HLAVNI_PROMPT__", hlavni)
    s = bezpecne_nahradit(s, "__NEGATIVNI_PROMPT__", negativni)
    s = bezpecne_nahradit(s, "__EDITACNI_PROMPT__", edit)
    s = bezpecne_nahradit(s, "__TEXT_MASKY__", maska)
    
    # Jména souborů
    s = s.replace('"base_"', f'"{prefix_base}"')
    s = s.replace('"edited_"', f'"{prefix_edit}"')
    
    try:
        graf = json.loads(s)
    except json.JSONDecodeError as e:
        print(f"Chyba při parsování grafu po nahrazení: {e}")
        sys.exit(1)
        
    # Dynamická randomizace seedů ve všech uzlech
    for node_id, node_data in graf.items():
        if "inputs" in node_data:
            for key in ["seed", "noise_seed"]:
                if key in node_data["inputs"]:
                    node_data["inputs"][key] = random.randint(1, 10**14)
                    
    return graf

def ziskej_dvoustupnove_prompty(data_mesice, globalni):
    """
    Určí, který prompt je základ a který je editace.
    Standard je A -> B. Volitelné pole "zaklad": "B" zachová starší opačné projekty.
    """
    zaklad = data_mesice.get("zaklad", "A").upper()
    if zaklad not in ("A", "B"):
        print(f"  Varování: neznámá hodnota zaklad='{zaklad}', používám A.")
        zaklad = "A"

    prompt_a = data_mesice["prompt_A"].format(**globalni)
    prompt_b = data_mesice["prompt_B"].format(**globalni)

    if zaklad == "A":
        return prompt_a, prompt_b, "A", "B"
    return prompt_b, prompt_a, "B", "A"

def main():
    parser = argparse.ArgumentParser(description="Generátor obrázků pro kalendář v ComfyUI.")
    parser.add_argument("-m", "--mesic", type=int, choices=range(0, 13), help="Číslo měsíce ke generování (0 = titulka, 1-12 = měsíce). Pokud není zadáno, generuje se vše.", default=None)
    parser.add_argument("--model", choices=["sdxl", "flux", "qwen"], default="sdxl", help="Zvolte, který nezávislý graf (JSON) se má použít")
    args = parser.parse_args()

    print("Načítám soubory...")
    
    sablona_soubor = SABLONY[args.model]
    try:
        with open(sablona_soubor, "r", encoding="utf-8") as f:
            sablona_text = f.read()
    except FileNotFoundError:
        print(f"Chyba: Zvolený graf {sablona_soubor} nebyl nalezen. Ujistěte se, že existuje.")
        return

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
        print(f"\nZpracovávám: 00_titulka (Model: {args.model.upper()})")

        prepsat = True
        if existuji_obrazky("00_titulka_"):
            prepsat, generovat_vse = zeptej_se_na_prepsani("00_titulka", generovat_vse)

        if not prepsat:
            print("  Přeskakuji...")
        else:
            prompt_titulka = titulka["prompt"].format(**globalni)
            negativni = titulka.get("negativni", "").format(**globalni)

            prompt_json = nahrad_a_nacti(
                sablona_text,
                prompt_titulka,
                negativni,
                "empty background",
                "none",
                "00_titulka_",
            )
                
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
        print(f"\nZpracovávám měsíc: {mesic_id} ({poznamka}) (Model: {args.model.upper()})")

        hlavni_prompt, editacni_prompt, pismeno_zaklad, pismeno_edit = ziskej_dvoustupnove_prompty(data_mesice, globalni)
        prefix_zaklad = f"{mesic_id}{pismeno_zaklad}_"
        prefix_edit = f"{mesic_id}{pismeno_edit}_"
        print(f"  Základ: {pismeno_zaklad}, editace ze základu: {pismeno_edit}")

        prepsat = True
        if existuji_obrazky(prefix_zaklad) or existuji_obrazky(prefix_edit):
            prepsat, generovat_vse = zeptej_se_na_prepsani(f"Měsíc {mesic_id}", generovat_vse)

        if not prepsat:
            print("  Přeskakuji...")
            continue

        negativni = data_mesice.get("negativni", "").format(**globalni)
        text_masky = data_mesice["editacni_maska"].format(**globalni)

        prompt_json = nahrad_a_nacti(
            sablona_text,
            hlavni_prompt,
            negativni,
            editacni_prompt,
            text_masky,
            prefix_zaklad,
            prefix_edit
        )
            
        prompt_id = odesli_do_comfy(prompt_json)
        if prompt_id:
            cekej_na_dokonceni(prompt_id)
            stahni_obrazky(prompt_id)

    print("\nCelý projekt byl úspěšně zpracován!")

if __name__ == "__main__":
    main()
