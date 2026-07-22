# Orpheus TTS Setup Guide

## Estado de la integración

✅ **Engine creado**: `core/orpheus_engine.py`
✅ **Integrado en DramaMixer**: `audio/drama_mixer.py`
✅ **Perfiles de voz creados**: `cast/voice_profiles/orpheus_*.yaml`
✅ **Script demo**: `scripts/generate_orpheus_demo.py`

## Requisitos de hardware

- **VRAM**: ~3.5-4 GB con cuantización 8-bit (RTX 3060/5060 compatible)
- **RAM**: 8 GB mínimo
- **Disco**: ~6 GB para el modelo

## Modelos disponibles

| Modelo | Idioma | Estado | URL HuggingFace |
|--------|--------|--------|-----------------|
| `unsloth/orpheus-3b-0.1-ft` | Inglés | ✅ Público | Descarga automática |
| `canopylabs/3b-es_it-ft-research_release` | Español/Italiano | 🔒 Gated | Requiere solicitar acceso |

### Para usar español

1. Ve a https://huggingface.co/canopylabs/3b-es_it-ft-research_release
2. Haz clic en "Request access" y acepta los términos
3. Configura tu token de HuggingFace:
   ```bash
   venv311/bin/huggingface-cli login
   ```
4. Edita el engine o setea la variable de entorno:
   ```bash
   export ORPHEUS_MODEL="canopylabs/3b-es_it-ft-research_release"
   ```

## Uso rápido

### 1. Generar audio directo con el engine

```python
from core.orpheus_engine import OrpheusEngine
from core.project import Voice

engine = OrpheusEngine(load_in_8bit=True)
engine.load()

voice = Voice(
    id="orpheus_leo",
    name="Leo",
    type="pretrained",
    engine="orpheus",
    language="en",
    speaker_id="leo"  # tara, leah, jess, leo, dan, mia, zac, zoe
)

engine.synthesize(
    "Hello world! <laugh> This is amazing!",
    voice,
    "output/orpheus_demo.wav"
)
engine.unload()
```

### 2. Usar con DramaMixer (multi-voz)

```python
from audio.drama_mixer import DramaMixer
from core.media_package import MediaPackage, ScriptLine

mixer = DramaMixer()
package = MediaPackage(package_id="demo_orpheus")
package.script = [
    ScriptLine(character="Leo", text="Welcome to the show!", voice_id="orpheus_leo"),
    ScriptLine(character="Tara", text="<laugh> Nice to be here!", voice_id="orpheus_tara"),
]
mixer.mix_package(package, "output/orpheus_mix.wav")
mixer.close()
```

### 3. Script demo incluido

```bash
venv311/bin/python scripts/generate_orpheus_demo.py
```

## Tags emocionales soportados

Inserta estos tags directamente en el texto:

| Tag | Efecto |
|-----|--------|
| `<laugh>` | Risa |
| `<chuckle>` | Risita |
| `<sigh>` | Suspiro |
| `<cough>` | Tos |
| `<sniffle>` | Resuello |
| `<groan>` | Gemido |
| `<yawn>` | Bostezo |
| `<gasp>` | Jadeo |

**Nota**: En el modelo español los tags son: `groan`, `chuckle`, `gasp`, `resoplido`, `laugh`, `yawn`, `cough`.

## Arquitectura del engine

```
core/orpheus_engine.py
  ├─ load()          → Carga tokenizer + modelo (8-bit) + SNAC decoder
  ├─ synthesize()    → Formatea prompt → genera tokens → decodifica SNAC → WAV
  ├─ unload()        → Libera VRAM
  └─ get_speakers()  → Lista voces predefinidas
```

## Limitaciones conocidas

1. **Voice cloning**: Orpheus NO hace zero-shot cloning como XTTS. Para clonar una voz necesitas fine-tunear el modelo con 50-300 ejemplos de audio.
2. **Idioma**: El modelo público es en inglés. El español requiere acceso al modelo gated.
3. **Velocidad**: La primera carga tarda 1-2 min. La generación es ~2-5s por oración.
4. **Longitud**: No generar textos muy largos de una vez. Dividir en oraciones de ~200 caracteres.

## Comparativa con tu flujo actual

| Feature | XTTS v2 | Orpheus 3B |
|---------|---------|------------|
| Voice cloning Homero | ✅ Sí | ❌ No (requiere fine-tune) |
| Emociones inline | ❌ No | ✅ Sí (`<laugh>`, `<sigh>`) |
| Español | ✅ Sí | 🔒 Requiere acceso HF |
| VRAM | ~3-4 GB | ~3.5-4 GB (8-bit) |
| Calidad conversacional | Buena | Excelente |

## Recomendación de uso

- **XTTS v2**: Sigue siendo tu mejor opción para clonar la voz de Homero en español.
- **Orpheus**: Úsalo para contenido en inglés o cuando necesites expresiones emocionales muy naturales. Ideal para intros, efectos de voz, o personajes secundarios.
