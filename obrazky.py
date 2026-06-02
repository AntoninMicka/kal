import json
import os
import sys
import argparse
import urllib.request
import urllib.error
import time
import urllib.parse
import copy

# --- KONFIGURACE ---
COMFY_URL = "http://127.0.0.1:8188"
SABLONA_SOUBOR = "double.json"
PROJEKT_SOUBOR = "projekt.json"

UZLY = {
    "hlavni_prompt": "5",
    "negativni_prompt": "6",
    "editacni_prompt": "21",
    "editacni_negativni_prompt": "101",
    "text_masky": "18",
    "editacni_sampler": "22",
    "editacni_latent": "20",
    "ulozit_zaklad": "2",
    "ulozit_edit": "25",
}

QWEN_MODELY = {
    "unet_name": "qwen_image_edit_fp8_e4m3fn.safetensors",
    "clip_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors",
    "vae_name": "qwen_image_vae.safetensors",
}

VYCHOZI_EDITACE = {
    "denoise": 0.45,
    "cfg": 6,
    "steps": 20,
    "maska_blur": 5,
    "maska_threshold": 0.08,
    "maska_dilation": 2,
    "grow_mask_by": 2,
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
        print("  -> Ujistěte se, že 'double.json' je uložen v 'API formátu' (Save API Format).")
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

def nastav_vstup(prompt_json, node_id, vstup, hodnota):
    """Nastaví hodnotu vstupu v ComfyUI API grafu a vypíše srozumitelnou chybu."""
    try:
        prompt_json[node_id]["inputs"][vstup] = hodnota
    except KeyError:
        raise KeyError(f"V šabloně chybí uzel {node_id} nebo jeho vstup '{vstup}'.")

def nastav_volitelny_vstup(prompt_json, node_id, vstup, hodnota):
    """Nastaví vstup jen tehdy, když v daném uzlu existuje."""
    if node_id in prompt_json and vstup in prompt_json[node_id].get("inputs", {}):
        prompt_json[node_id]["inputs"][vstup] = hodnota

def ziskej_nastaveni_editace(data_mesice, globalni):
    nastaveni = dict(VYCHOZI_EDITACE)
    nastaveni.update(data_mesice.get("editace", {}))

    for klic, hodnota in list(nastaveni.items()):
        if isinstance(hodnota, str):
            nastaveni[klic] = hodnota.format(**globalni)

    return nastaveni

def priprav_prompt(sablona_json, hlavni_prompt, editacni_prompt, text_masky, negativni, prefix_zaklad, prefix_edit, nastaveni_editace):
    """Vrátí kopii ComfyUI workflow vyplněnou pro jeden dvoustupňový běh."""
    prompt_json = copy.deepcopy(sablona_json)

    nastav_vstup(prompt_json, UZLY["hlavni_prompt"], "text", hlavni_prompt)
    nastav_vstup(prompt_json, UZLY["negativni_prompt"], "text", negativni)
    nastav_vstup(prompt_json, UZLY["editacni_prompt"], "text", editacni_prompt)
    nastav_vstup(prompt_json, UZLY["editacni_negativni_prompt"], "text", negativni)
    nastav_vstup(prompt_json, UZLY["text_masky"], "text", text_masky)
    nastav_vstup(prompt_json, UZLY["ulozit_zaklad"], "filename_prefix", prefix_zaklad)
    nastav_vstup(prompt_json, UZLY["ulozit_edit"], "filename_prefix", prefix_edit)

    nastav_volitelny_vstup(prompt_json, UZLY["editacni_sampler"], "denoise", nastaveni_editace["denoise"])
    nastav_volitelny_vstup(prompt_json, UZLY["editacni_sampler"], "cfg", nastaveni_editace["cfg"])
    nastav_volitelny_vstup(prompt_json, UZLY["editacni_sampler"], "steps", nastaveni_editace["steps"])
    nastav_volitelny_vstup(prompt_json, UZLY["text_masky"], "blur", nastaveni_editace["maska_blur"])
    nastav_volitelny_vstup(prompt_json, UZLY["text_masky"], "threshold", nastaveni_editace["maska_threshold"])
    nastav_volitelny_vstup(prompt_json, UZLY["text_masky"], "dilation_factor", nastaveni_editace["maska_dilation"])
    nastav_volitelny_vstup(prompt_json, UZLY["editacni_latent"], "grow_mask_by", nastaveni_editace["grow_mask_by"])

    return prompt_json

def priprav_prompt_qwen(sablona_json, hlavni_prompt, editacni_prompt, negativni, prefix_zaklad, prefix_edit):
    """Vrátí hybridní workflow: SDXL základ z původní šablony a Qwen instrukční editace."""
    prompt_json = copy.deepcopy(sablona_json)

    nastav_vstup(prompt_json, UZLY["hlavni_prompt"], "text", hlavni_prompt)
    nastav_vstup(prompt_json, UZLY["negativni_prompt"], "text", negativni)
    nastav_vstup(prompt_json, UZLY["ulozit_zaklad"], "filename_prefix", prefix_zaklad)

    prompt_json["1000"] = {
        "inputs": {
            "unet_name": QWEN_MODELY["unet_name"],
            "weight_dtype": "default",
        },
        "class_type": "UNETLoader",
        "_meta": {"title": "Qwen Edit Model"},
    }
    prompt_json["1001"] = {
        "inputs": {
            "clip_name": QWEN_MODELY["clip_name"],
            "type": "qwen_image",
            "device": "default",
        },
        "class_type": "CLIPLoader",
        "_meta": {"title": "Qwen Edit CLIP"},
    }
    prompt_json["1002"] = {
        "inputs": {
            "vae_name": QWEN_MODELY["vae_name"],
        },
        "class_type": "VAELoader",
        "_meta": {"title": "Qwen Edit VAE"},
    }
    prompt_json["1003"] = {
        "inputs": {
            "clip": ["1001", 0],
            "prompt": editacni_prompt,
            "vae": ["1002", 0],
            "image": ["28", 0],
        },
        "class_type": "TextEncodeQwenImageEdit",
        "_meta": {"title": "Qwen Edit Positive"},
    }
    prompt_json["1004"] = {
        "inputs": {
            "clip": ["1001", 0],
            "prompt": "",
            "vae": ["1002", 0],
            "image": ["28", 0],
        },
        "class_type": "TextEncodeQwenImageEdit",
        "_meta": {"title": "Qwen Edit Negative"},
    }
    prompt_json["1005"] = {
        "inputs": {
            "pixels": ["28", 0],
            "vae": ["1002", 0],
        },
        "class_type": "VAEEncode",
        "_meta": {"title": "Qwen Encode Base Image"},
    }
    prompt_json["1006"] = {
        "inputs": {
            "model": ["1000", 0],
            "shift": 3,
        },
        "class_type": "ModelSamplingAuraFlow",
        "_meta": {"title": "Qwen Model Sampling"},
    }
    prompt_json["1007"] = {
        "inputs": {
            "model": ["1006", 0],
            "strength": 1,
        },
        "class_type": "CFGNorm",
        "_meta": {"title": "Qwen CFG Norm"},
    }
    prompt_json["1008"] = {
        "inputs": {
            "seed": 344147753686358,
            "steps": 20,
            "cfg": 2.5,
            "sampler_name": "euler",
            "scheduler": "simple",
            "denoise": 1,
            "model": ["1007", 0],
            "positive": ["1003", 0],
            "negative": ["1004", 0],
            "latent_image": ["1005", 0],
        },
        "class_type": "KSampler",
        "_meta": {"title": "Qwen Edit Sampler"},
    }
    prompt_json["1009"] = {
        "inputs": {
            "samples": ["1008", 0],
            "vae": ["1002", 0],
        },
        "class_type": "VAEDecode",
        "_meta": {"title": "Qwen Decode Edit"},
    }

    nastav_vstup(prompt_json, UZLY["ulozit_edit"], "images", ["1009", 0])
    nastav_vstup(prompt_json, UZLY["ulozit_edit"], "filename_prefix", prefix_edit)

    if "19" in prompt_json:
        del prompt_json["19"]

    return prompt_json

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
    parser.add_argument("--editacni-model", choices=["sdxl", "qwen"], default="sdxl", help="Model pro druhý stupeň editace měsíců")
    args = parser.parse_args()

    print("Načítám soubory...")
    # 1. Načtení ComfyUI API šablony
    try:
        with open(SABLONA_SOUBOR, "r", encoding="utf-8") as f:
            sablona_json = json.load(f)
    except FileNotFoundError:
        print(f"Chyba: Soubor {SABLONA_SOUBOR} nebyl nalezen.")
        return
    except json.JSONDecodeError as e:
        print(f"Chyba: Soubor {SABLONA_SOUBOR} není platný JSON: {e}")
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

            # Šablona vyžaduje inpainting, pro titulku pošleme slepá data
            prompt_json = priprav_prompt(
                sablona_json,
                prompt_titulka,
                "empty background",
                "none",
                negativni,
                "00_titulka_",
                "00_odpad_",
                VYCHOZI_EDITACE,
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
        print(f"\nZpracovávám měsíc: {mesic_id} ({poznamka})")

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
        nastaveni_editace = ziskej_nastaveni_editace(data_mesice, globalni)

        if args.editacni_model == "qwen":
            print("  Editační model: Qwen-Image-Edit")
            prompt_json = priprav_prompt_qwen(
                sablona_json,
                hlavni_prompt,
                editacni_prompt,
                negativni,
                prefix_zaklad,
                prefix_edit,
            )
        else:
            print(f"  Editační model: SDXL inpaint, denoise={nastaveni_editace['denoise']}, maska='{text_masky}'")
            prompt_json = priprav_prompt(
                sablona_json,
                hlavni_prompt,
                editacni_prompt,
                text_masky,
                negativni,
                prefix_zaklad,
                prefix_edit,
                nastaveni_editace,
            )
        prompt_id = odesli_do_comfy(prompt_json)
        if prompt_id:
            cekej_na_dokonceni(prompt_id)
            stahni_obrazky(prompt_id)

    print("\nCelý projekt byl úspěšně zpracován!")

if __name__ == "__main__":
    main()
