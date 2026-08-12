# Mastering de podcast

El pipeline web aplica automáticamente mastering profesional a los episodios generados:

- **Crossfade y trimming entre líneas de diálogo**: `DramaMixer` corta silencios al inicio/final de cada línea y une las frases con crossfade suave.
- **Procesado de voz**: EQ (high-pass + presencia), compresión, limitador y noise gate vía ffmpeg.
- **Normalización de loudness**: el episodio final se normaliza a **-16 LUFS** con pico **-1 dBTP** usando `loudnorm` de ffmpeg.
- **Ducking sidechain en música de fondo**: la música se atenúa automáticamente cuando hay voz mediante `sidechaincompress`.
- **Crossfade y loudness en intro/outro**: `BrandingEngine` normaliza intro, cuerpo y outro al mismo target LUFS y los une con crossfade.

## Configuración

`EpisodeConfig` incluye el campo `podcast_mastering` (tipo `MasteringConfig`). Se puede desactivar configurando:

```python
EpisodeConfig(
    episode_type="raw",
    sources=[{"content": "...", "title": "..."}],
    podcast_mastering=MasteringConfig(enabled=False),
)
```

## Requisitos

- ffmpeg >= 5.0 (recomendado n8.x).
- Sin dependencias Python adicionales: se reutilizan pydub, numpy y ffmpeg.
