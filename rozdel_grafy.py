import json
import copy

def main():
    try:
        with open("double.json", "r", encoding="utf-8") as f:
            zaklad = json.load(f)
    except Exception as e:
        print(f"Chyba při čtení double.json: {e}")
        return

    # 1. SDXL (přímá kopie)
    with open("sdxl.json", "w", encoding="utf-8") as f:
        json.dump(zaklad, f, indent=2)
    print("Vytvořeno: sdxl.json")

    # 2. FLUX (kompletní base i inpaint)
    flux = copy.deepcopy(zaklad)
    flux["3000"] = {"inputs": {"unet_name": "flux1-dev-fp8.safetensors", "weight_dtype": "default"}, "class_type": "UNETLoader"}
    flux["3001"] = {"inputs": {"clip_name1": "t5xxl_fp8_e4m3fn.safetensors", "clip_name2": "clip_l.safetensors", "type": "flux"}, "class_type": "DualCLIPLoader"}
    flux["3002"] = {"inputs": {"vae_name": "ae.safetensors"}, "class_type": "VAELoader"}

    flux["5"]["inputs"]["clip"] = ["3001", 0]
    flux["6"]["inputs"]["clip"] = ["3001", 0]
    flux["6"]["inputs"]["text"] = ""
    flux["4"]["inputs"]["model"] = ["3000", 0]
    flux["4"]["inputs"]["cfg"] = 1.0
    flux["3"]["inputs"]["vae"] = ["3002", 0]

    for det in ["28", "33"]:
        if det in flux:
            flux[det]["inputs"]["model"] = ["3000", 0]
            flux[det]["inputs"]["clip"] = ["3001", 0]
            flux[det]["inputs"]["vae"] = ["3002", 0]
            flux[det]["inputs"]["cfg"] = 1.0

    if "31" in flux:
        flux["31"]["inputs"]["clip"] = ["3001", 0]

    flux["2000"] = {"inputs": {"unet_name": "flux1-fill-dev-fp8.safetensors", "weight_dtype": "default"}, "class_type": "UNETLoader"}
    flux["2005"] = {"inputs": {"grow_mask_by": 8, "pixels": ["28", 0], "vae": ["3002", 0], "mask": ["18", 0]}, "class_type": "VAEEncodeForInpaint"}
    flux["2006"] = {"inputs": {"seed": 0, "steps": 25, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0, "model": ["2000", 0], "positive": ["21", 0], "negative": ["101", 0], "latent_image": ["2005", 0]}, "class_type": "KSampler"}
    flux["2007"] = {"inputs": {"samples": ["2006", 0], "vae": ["3002", 0]}, "class_type": "VAEDecode"}

    flux["21"]["inputs"]["clip"] = ["3001", 0]
    if "101" in flux:
        flux["101"]["inputs"]["clip"] = ["3001", 0]
        flux["101"]["inputs"]["text"] = ""
    flux["25"]["inputs"]["images"] = ["2007", 0]

    for u in ["100", "20", "22", "23"]: flux.pop(u, None)

    with open("flux.json", "w", encoding="utf-8") as f:
        json.dump(flux, f, indent=2)
    print("Vytvořeno: flux.json")

    # 3. QWEN (SDXL base s Qwen editací)
    qwen = copy.deepcopy(zaklad)
    qwen["1000"] = {"inputs": {"unet_name": "qwen_image_edit_fp8_e4m3fn.safetensors", "weight_dtype": "default"}, "class_type": "UNETLoader"}
    qwen["1001"] = {"inputs": {"clip_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors", "type": "qwen_image", "device": "default"}, "class_type": "CLIPLoader"}
    qwen["1002"] = {"inputs": {"vae_name": "qwen_image_vae.safetensors"}, "class_type": "VAELoader"}
    qwen["1003"] = {"inputs": {"clip": ["1001", 0], "prompt": "__EDITACNI_PROMPT__", "vae": ["1002", 0], "image": ["28", 0]}, "class_type": "TextEncodeQwenImageEdit"}
    qwen["1004"] = {"inputs": {"clip": ["1001", 0], "prompt": "__NEGATIVNI_PROMPT__", "vae": ["1002", 0], "image": ["28", 0]}, "class_type": "TextEncodeQwenImageEdit"}
    qwen["1005"] = {"inputs": {"pixels": ["28", 0], "vae": ["1002", 0]}, "class_type": "VAEEncode"}
    qwen["1006"] = {"inputs": {"model": ["1000", 0], "shift": 3}, "class_type": "ModelSamplingAuraFlow"}
    qwen["1007"] = {"inputs": {"model": ["1006", 0], "strength": 1}, "class_type": "CFGNorm"}
    qwen["1008"] = {"inputs": {"seed": 0, "steps": 20, "cfg": 2.5, "sampler_name": "euler", "scheduler": "simple", "denoise": 1, "model": ["1007", 0], "positive": ["1003", 0], "negative": ["1004", 0], "latent_image": ["1005", 0]}, "class_type": "KSampler"}
    qwen["1009"] = {"inputs": {"samples": ["1008", 0], "vae": ["1002", 0]}, "class_type": "VAEDecode"}
    
    qwen["25"]["inputs"]["images"] = ["1009", 0]
    for u in ["100", "20", "22", "23", "21", "101", "18", "17"]: qwen.pop(u, None)

    with open("qwen.json", "w", encoding="utf-8") as f:
        json.dump(qwen, f, indent=2)
    print("Vytvořeno: qwen.json")

if __name__ == "__main__":
    main()