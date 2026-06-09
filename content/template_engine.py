"""
Template Engine — generates deterministic content for meditations and motivation podcasts.

Uses Jinja2 templates with randomized variables controlled by a seed.
"""

import random
from pathlib import Path
from typing import Dict, Any, List, Optional

import jinja2


class TemplateEngine:
    """Generates content from Jinja2 templates with controllable randomization."""

    MEDITATION_TOPICS = [
        "respiración",
        "gratitud",
        "amor propio",
        "sueño profundo",
        "reducción de ansiedad",
        "conexión con el cuerpo",
        "claridad mental",
        "perdón",
        "abundancia",
        "paz interior"
    ]

    MOTIVATION_TOPICS = [
        "superar el miedo",
        "constancia",
        "la disciplina vence a la motivación",
        "aprender del fracaso",
        "pequeños pasos",
        "enfocarse en lo que controlas",
        "el poder de los hábitos",
        "salir de la zona de confort",
        "creer en ti mismo",
        "la acción vence a la perfección"
    ]

    def __init__(self, templates_dir: str = "templates"):
        self.templates_dir = Path(templates_dir)
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self.templates_dir)),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True
        )

    def generate_meditation(
        self,
        duration_minutes: int = 10,
        topic: Optional[str] = None,
        seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate a meditation script."""
        rng = random.Random(seed)
        selected_topic = topic or rng.choice(self.MEDITATION_TOPICS)

        try:
            template = self.env.get_template("meditation/default.j2")
        except jinja2.TemplateNotFound:
            template = self.env.from_string(self._default_meditation_template())

        script = template.render(
            topic=selected_topic,
            duration_minutes=duration_minutes,
            seed=seed
        )

        return {
            "title": f"Meditación guiada: {selected_topic.capitalize()}",
            "topic": selected_topic,
            "duration_minutes": duration_minutes,
            "content_type": "meditation",
            "content": script,
            "source": "template",
            "source_url": ""
        }

    def generate_motivation(
        self,
        topic: Optional[str] = None,
        quote: Optional[str] = None,
        seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate a motivational podcast script."""
        rng = random.Random(seed)
        selected_topic = topic or rng.choice(self.MOTIVATION_TOPICS)

        try:
            template = self.env.get_template("motivation/default.j2")
        except jinja2.TemplateNotFound:
            template = self.env.from_string(self._default_motivation_template())

        script = template.render(
            topic=selected_topic,
            quote=quote or "",
            seed=seed
        )

        return {
            "title": f"Motivación: {selected_topic.capitalize()}",
            "topic": selected_topic,
            "content_type": "motivation",
            "content": script,
            "source": "template",
            "source_url": ""
        }

    def _default_meditation_template(self) -> str:
        return """Encuentra una posición cómoda y cierra los ojos suavemente.

Durante los próximos {{ duration_minutes }} minutos, vamos a practicar {{ topic }}.

Comienza llevando tu atención a la respiración. Inhala profundamente por la nariz... y exhala lentamente por la boca.

Con cada inhalación, siente como tu cuerpo se expande. Con cada exhalación, suelta cualquier tensión.

Ahora, imagina que estás en un lugar tranquilo. Puede ser un bosque, una playa, o cualquier lugar donde te sientas en paz.

Visualiza este lugar con todos tus sentidos. Escucha los sonidos. Siente el aire sobre tu piel. Huele los aromas naturales.

Deja que la sensación de {{ topic }} llene todo tu ser. No hay prisa. Solo estás aquí, en este momento.

Si tu mente divaga, es normal. Con amabilidad, regresa tu atención a la respiración y a este lugar de calma.

Respira profundamente una vez más. Inhala paz... exhala cualquier resto de tensión.

Cuando estés listo, comienza a mover suavemente tus dedos y tus pies. Abre los ojos cuando te sientas preparado.

Gracias por compartir este momento de {{ topic }}."""

    def _default_motivation_template(self) -> str:
        return """Hoy quiero hablarte sobre {{ topic }}.

Muchas veces pensamos que necesitamos sentirnos motivados para actuar. Pero la verdad es que la motivación sigue a la acción, no al revés.

{% if quote %}
Como dice la cita: "{{ quote }}"
{% endif %}

Piensa en una meta que tengas. No importa cuán grande sea. Lo importante es dar el primer paso hoy. No el paso perfecto, sino el primero.

{{ topic }} no es algo que haces una vez. Es una decisión que tomas todos los días.

Cuando sientas ganas de rendirte, recuerda por qué empezaste. Recuerda quién eres y todo lo que ya has superado.

Tienes dentro de ti todo lo necesario para lograrlo. Así que respira hondo, levántate, y da ese paso.

Hoy es tu día."""
