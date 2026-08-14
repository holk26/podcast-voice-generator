import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "data" / "app.db"

BRIEF = """Canal de enseñanza de inglés en formato diálogo bilingüe.
- Personajes: Alejandra (profesora, voz femenina) y Homero (alumno, voz masculina).
- Estructura: Alejandra presenta una frase o vocabulario en inglés, lo pronuncia con claridad, y Homero pregunta o repite. Luego Alejandra explica el significado y uso en español.
- Idioma: mezcla 50% inglés / 50% español; el inglés debe ser natural y didáctico, el español de apoyo.
- Tono: cercano, paciente, motivador.
- Reglas: cada episodio introduce 5-8 expresiones útiles, incluye ejemplos de situaciones reales, y termina con un mini repaso."""

DESCRIPTION = (
    "Aprende inglés práctico con una conversación bilingüe entre "
    "Alejandra (profesora) y Homero (alumno)."
)


def main() -> None:
    conn = sqlite3.connect(DB)
    conn.execute(
        """
        UPDATE channels
        SET name = 'English Every Day',
            description = ?,
            niche = 'educación / idiomas',
            format = 'podcast',
            default_voice_id = 'clone:homero_referencia:qwen3',
            is_active = 1,
            target_minutes = 10,
            brief = ?
        WHERE id = 1
        """,
        (DESCRIPTION, BRIEF),
    )
    conn.commit()
    conn.close()
    print("Canal English Every Day configurado.")


if __name__ == "__main__":
    main()
