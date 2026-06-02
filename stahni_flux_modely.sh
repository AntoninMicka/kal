#!/bin/bash

# Cesta k vaší instalaci ComfyUI (upravte podle potřeby)
COMFY_DIR="/home/antonin/Projects/Comfy/ComfyUI"


# Vytvoření složek, pokud ještě neexistují
mkdir -p "$COMFY_DIR/models/unet"
mkdir -p "$COMFY_DIR/models/clip"
mkdir -p "$COMFY_DIR/models/vae"

echo "Stahuji modely FLUX..."

# UNET modely (Hlavní model a Inpaint/Fill model)
wget -nc -P "$COMFY_DIR/models/unet/" "https://huggingface.co/Comfy-Org/flux1-dev/resolve/main/flux1-dev-fp8.safetensors"
wget -nc -P "$COMFY_DIR/models/unet/" "https://huggingface.co/comfyanonymous/flux_inpainting/resolve/main/flux1-fill-dev-fp8.safetensors"

# CLIP modely (Textové encodery)
wget -nc -P "$COMFY_DIR/models/clip/" "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp8_e4m3fn.safetensors"
wget -nc -P "$COMFY_DIR/models/clip/" "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/clip_l.safetensors"

# VAE model
wget -nc -P "$COMFY_DIR/models/vae/" "https://huggingface.co/black-forest-labs/FLUX.1-schnell/resolve/main/ae.safetensors"

echo "----------------------------------------"
echo "Stahování bylo dokončeno!"
echo "Zkontrolujte, zda se nevyskytla chyba 401 u chráněných modelů."