#!/usr/bin/env python3
"""Prueba Orpheus TTS español con emociones usando transformers (sin vllm)."""
import os
import sys
import torch
import numpy as np
import wave

# Configurar device
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Usando device: {DEVICE}")

# Verificar VRAM disponible
if DEVICE == "cuda":
    vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
    print(f"VRAM total: {vram:.1f} GB")

MODEL_NAME = "canopylabs/3b-es_it-ft-research_release"
SNAC_MODEL = "hubertsiuzdak/snac_24khz"

print("Cargando tokenizer...")
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)

print("Cargando modelo con cuantización 8-bit...")
# Cargar en 8-bit para ahorrar VRAM
bnb_config = BitsAndBytesConfig(
    load_in_8bit=True,
    llm_int8_threshold=6.0,
    llm_int8_has_fp16_weight=False,
)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
    torch_dtype=torch.float16,
)

print("Cargando SNAC decoder...")
from snac import SNAC
snac_model = SNAC.from_pretrained(SNAC_MODEL).eval().to(DEVICE)

def format_prompt(text, voice="tara"):
    """Formatea el prompt para el modelo Orpheus."""
    adapted_prompt = f"{voice}: {text}"
    prompt_tokens = tokenizer(adapted_prompt, return_tensors="pt")
    start_token = torch.tensor([[128259]], dtype=torch.int64)
    end_tokens = torch.tensor([[128009, 128260, 128261, 128257]], dtype=torch.int64)
    all_input_ids = torch.cat([start_token, prompt_tokens.input_ids, end_tokens], dim=1)
    prompt_string = tokenizer.decode(all_input_ids[0])
    return prompt_string, all_input_ids

def turn_token_into_id(token_string, index):
    """Extrae el ID numérico de un custom token."""
    token_string = token_string.strip()
    last_token_start = token_string.rfind("<custom_token_")
    if last_token_start == -1:
        return None
    last_token = token_string[last_token_start:]
    if last_token.startswith("<custom_token_") and last_token.endswith(">"):
        try:
            number_str = last_token[14:-1]
            return int(number_str) - 10 - ((index % 7) * 4096)
        except ValueError:
            return None
    return None

def convert_to_audio(multiframe):
    """Convierte frames de tokens a audio usando SNAC."""
    if len(multiframe) < 7:
        return None
    
    frames = []
    num_frames = len(multiframe) // 7
    frame = multiframe[:num_frames*7]
    
    codes_0 = torch.tensor([], device=DEVICE, dtype=torch.int32)
    codes_1 = torch.tensor([], device=DEVICE, dtype=torch.int32)
    codes_2 = torch.tensor([], device=DEVICE, dtype=torch.int32)
    
    for j in range(num_frames):
        i = 7*j
        if codes_0.shape[0] == 0:
            codes_0 = torch.tensor([frame[i]], device=DEVICE, dtype=torch.int32)
        else:
            codes_0 = torch.cat([codes_0, torch.tensor([frame[i]], device=DEVICE, dtype=torch.int32)])
        
        if codes_1.shape[0] == 0:
            codes_1 = torch.tensor([frame[i+1], frame[i+4]], device=DEVICE, dtype=torch.int32)
        else:
            codes_1 = torch.cat([codes_1, torch.tensor([frame[i+1], frame[i+4]], device=DEVICE, dtype=torch.int32)])
        
        if codes_2.shape[0] == 0:
            codes_2 = torch.tensor([frame[i+2], frame[i+3], frame[i+5], frame[i+6]], device=DEVICE, dtype=torch.int32)
        else:
            codes_2 = torch.cat([codes_2, torch.tensor([frame[i+2], frame[i+3], frame[i+5], frame[i+6]], device=DEVICE, dtype=torch.int32)])
    
    codes = [codes_0.unsqueeze(0), codes_1.unsqueeze(0), codes_2.unsqueeze(0)]
    
    # Validar rango
    if torch.any(codes[0] < 0) or torch.any(codes[0] > 4096) or \
       torch.any(codes[1] < 0) or torch.any(codes[1] > 4096) or \
       torch.any(codes[2] < 0) or torch.any(codes[2] > 4096):
        return None
    
    with torch.inference_mode():
        audio_hat = snac_model.decode(codes)
    
    audio_slice = audio_hat[:, :, 2048:4096]
    audio_np = audio_slice.detach().cpu().numpy()
    audio_int16 = (audio_np * 32767).astype(np.int16)
    return audio_int16.tobytes()


def generate_speech(text, voice="tara", max_new_tokens=1200, temperature=0.6, top_p=0.8):
    """Genera audio a partir de texto."""
    prompt_string, input_ids = format_prompt(text, voice)
    input_ids = input_ids.to(model.device)
    
    print(f"Generando audio para: {text[:60]}...")
    
    with torch.inference_mode():
        outputs = model.generate(
            input_ids,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=True,
            repetition_penalty=1.3,
            pad_token_id=tokenizer.pad_token_id if tokenizer.pad_token_id else tokenizer.eos_token_id,
        )
    
    # Extraer tokens generados (después del prompt)
    generated_ids = outputs[0][input_ids.shape[1]:]
    
    # Decodificar tokens
    tokens_text = tokenizer.decode(generated_ids, skip_special_tokens=False)
    
    # Extraer custom tokens
    buffer = []
    count = 0
    all_audio_bytes = b""
    
    # Procesar todo el texto de tokens
    import re
    token_matches = re.findall(r'<custom_token_(\d+)>', tokens_text)
    
    for match in token_matches:
        token_val = int(match) - 10 - ((count % 7) * 4096)
        if token_val > 0:
            buffer.append(token_val)
            count += 1
            
            if count % 7 == 0 and count > 27:
                buffer_to_proc = buffer[-28:]
                audio_samples = convert_to_audio(buffer_to_proc)
                if audio_samples:
                    all_audio_bytes += audio_samples
    
    return all_audio_bytes


if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)
    
    # Texto de prueba con emociones en español
    # Tags soportados en español: groan, chuckle, gasp, resoplido, laugh, yawn, cough
    texto = "¡Hola! Soy tu asistente virtual. <laugh> Hoy vamos a hablar de tecnología. ¿Estás listo? <chuckle> ¡Vamos allá!"
    
    print("\n" + "="*60)
    print("ORPHEUS TTS - ESPAÑOL CON EMOCIONES")
    print("="*60)
    
    audio_bytes = generate_speech(texto, voice="tara", max_new_tokens=600)
    
    if audio_bytes:
        output_path = "output/orpheus_spanish_test.wav"
        with wave.open(output_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(audio_bytes)
        print(f"\n✅ Audio generado: {output_path}")
    else:
        print("\n❌ No se generó audio")
