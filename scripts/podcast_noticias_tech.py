#!/usr/bin/env python3
"""Genera un podcast de noticias tecnológicas con Edge-TTS (voz natural)."""
import asyncio
import edge_tts
import os

# Script de podcast profesional
SCRIPT = """
Bienvenidos a Tech Pulse, su resumen diario de noticias tecnológicas. Hoy es martes, dos de junio de dos mil veintiséis. Soy Álvaro, y estas son las historias que marcan la agenda del sector.

Empezamos con Microsoft Build 2026, que está arrancando en San Francisco y viene cargado de anuncios. El eje central de este año es la inteligencia artificial agente. Microsoft presentó Scout, un asistente personal que integra Outlook, OneDrive y Teams, y que, según la compañía, es el primer asistente real que ofrecen. Scout puede organizar calendarios, redactar correos e incluso hacer llamadas telefónicas. Omar Shahine, vicepresidente del proyecto, lo define como una experiencia muy distinta a un simple chat de inteligencia artificial.

En hardware, Microsoft ha lanzado la Surface RTX Spark Dev Box, una mini PC con el nuevo chip de Nvidia, ciento veintiocho gigabytes de memoria unificada y capacidad para ejecutar modelos de ciento veinte mil millones de parámetros de forma local. Su diseño recuerda a la parte superior de una Xbox Series X, y está pensada para desarrolladores que trabajan con inteligencia artificial en el dispositivo.

También en Build, Microsoft ha presentado Majorana Dos, su nuevo procesador cuántico. La compañía afirma que sus cúbits son mil veces más fiables que los de la generación anterior, gracias a un nuevo stack de materiales y a la ayuda de la inteligencia artificial agente de Microsoft Discovery. Además, han anunciado siete modelos de inteligencia artificial propios, incluyendo MAI Thinking One, un modelo de razonamiento avanzado entrenado desde cero sin destilación de terceros.

Microsoft también muestra Project Solara, un sistema operativo basado en Android diseñado específicamente para dispositivos que ejecutan agentes de inteligencia artificial. Han mostrado dos conceptos: un dispositivo de escritorio tipo Echo Show y una insignia digital. La idea es que estos gadgets compartan tareas con el PC de forma transparente.

Del lado de Nvidia, Jensen Huang estuvo en el escenario de Build de forma virtual y confirmó que llevan tres años trabajando con Microsoft en el chip RTX Spark. Este procesador basado en ARM promete un petaflop de rendimiento de inteligencia artificial y marca el inicio de una nueva era de PCs Windows diseñados para agentes personales.

Google, por su parte, está lanzando un armario digital generado por inteligencia artificial en Google Fotos. La función analiza tus imágenes para crear combinaciones de ropa virtuales que puedes probar, guardar y compartir. Por ahora, está disponible en Estados Unidos, India y Brasil, y requiere al menos mil fotos personales para funcionar sin suscripción.

Cambiando de tema, OpenAI anunció que Codex, su agente de programación, ya cuenta con cinco millones de usuarios semanales. La compañía enfatiza que la herramienta no es solo para programadores, sino para cualquier persona que necesite automatizar tareas técnicas.

Y para cerrar, Apple se prepara para su WWDC 2026, que comienza el lunes ocho de junio. Se esperan iOS veintisiete, macOS veintisiete y, lo más interesante, una versión conversacional de Siri que podría competir directamente con ChatGPT y Gemini. También se rumorea el primer iPhone plegable, con una interfaz tipo iPad para la pantalla interior.

Eso es todo por hoy en Tech Pulse. Si te ha gustado este episodio, compártelo y síguenos para más actualizaciones. Hasta mañana.
"""

async def generate():
    output_path = "output/podcast_noticias_tech_2jun2026.mp3"
    os.makedirs("output", exist_ok=True)
    
    # Voz profesional de podcast: Álvaro (España) - muy natural
    communicate = edge_tts.Communicate(SCRIPT.strip(), "es-ES-AlvaroNeural")
    await communicate.save(output_path)
    print(f"✅ Podcast generado: {output_path}")

if __name__ == "__main__":
    asyncio.run(generate())
