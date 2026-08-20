"""Crea el episodio de podcast sobre el caso Lindsay Clancy.

Uso:
    source venv311/bin/activate
    PYTHONPATH=. python scripts/create_lindsay_clancy_episode.py
"""

import json
import re
import urllib.request

from core.emotion_tags import HIGGS_TAGS

API_BASE = "http://localhost:8000"

SCRIPT = """
<|emotion:contemplation|> Tres niños. Una madre. Una llamada al nueve once. Y una pregunta que un jurado de Massachusetts está tratando de responder: ¿qué estaba ocurriendo realmente en la mente de Lindsay Clancy el veinticuatro de enero de dos mil veintitrés?

<|emotion:sadness|> Este es el caso Commonwealth contra Lindsay Clancy. Un caso que no se reduce a saber qué pasó físicamente en aquella casa de Duxbury. Lo que está en juego es si Lindsay Clancy podía entender o controlar sus acciones en el momento de los hechos.

<|emotion:contemplation|> Las víctimas fueron Cora Clancy, de cinco años. Dawson Clancy, de tres años. Y Callan Clancy, de apenas ocho meses. Tres hermanos que murieron en su propia vivienda, mientras su madre se encontraba con ellos. Lindsay Clancy fue acusada de causar la muerte de sus tres hijos. Ella se declaró no culpable.

<|emotion:fear|> Esa tarde de enero, Patrick Clancy, el esposo de Lindsay, salió de la vivienda. Cuando regresó, la escena que encontró lo llevó a llamar de inmediato a emergencias. Los tres hijos de la pareja habían muerto. La policía y los servicios de emergencia acudieron a la vivienda de Duxbury. Lindsay sobrevivió a un intento posterior de suicidio, pero quedó con graves consecuencias físicas.

<|emotion:helplessness|> Desde entonces, el caso ha generado un debate mucho más amplio: el de la salud mental, la maternidad y la responsabilidad penal. Pero antes de entrar en ese debate, conviene separar con cuidado lo que es un hecho establecido, lo que es evidencia presentada y lo que son alegaciones de cada parte.

<|emotion:contemplation|> Los hechos establecidos más básicos son estos. El veinticuatro de enero de dos mil veintitrés, Lindsay Clancy se encontraba en su vivienda de Duxbury con sus tres hijos. Su esposo, Patrick Clancy, salió de la vivienda. Posteriormente regresó y encontró a los niños y a Lindsay en circunstancias que desencadenaron una llamada al nueve once. Los tres niños fallecieron. Lindsay sobrevivió a un intento de suicidio. Eso es, grosso modo, lo que no está en discusión.

<|emotion:confusion|> Lo que está en discusión es el estado mental de Lindsay. La defensa sostiene que sufría una enfermedad mental grave, incluyendo una posible psicosis posparto. La fiscalía sostiene que actuó deliberadamente y cuestiona que existiera una psicosis que eliminara su responsabilidad criminal.

<|emotion:contemplation|> El principal punto de controversia del juicio no consiste únicamente en determinar quién estuvo físicamente involucrado en los hechos. La cuestión jurídica fundamental puede resumirse de esta manera: ¿tenía Lindsay Clancy la capacidad mental necesaria para ser considerada penalmente responsable de sus acciones?

<|emotion:contemplation|> Esta pregunta es diferente de determinar simplemente quién estuvo físicamente involucrado en los hechos. En el derecho penal, no basta con probar que alguien realizó un acto. También hay que evaluar si esa persona tenía la capacidad de comprender la naturaleza y consecuencias de sus actos, o de conformar su conducta a la ley. Esa distinción es el núcleo de todo este juicio.

<|emotion:sadness|> La investigación recopiló diferentes tipos de evidencia en la vivienda. Entre ellos, evidencia biológica, objetos encontrados en la escena, fotografías, evidencia relacionada con medicamentos, elementos examinados por los investigadores, evidencia médica, evidencia toxicológica, comunicaciones y documentación personal.

<|emotion:contemplation|> Los investigadores también buscaron huellas dactilares en objetos relevantes. Durante el juicio se discutieron cuestiones relacionadas con esas huellas. Los investigadores declararon que no encontraron huellas dactilares utilizables en algunos objetos relevantes. Esto no demuestra que Clancy sea inocente. Tampoco significa que la evidencia física sea inútil. Simplemente significa que determinadas piezas de evidencia física no proporcionaron una identificación mediante huellas dactilares.

<|emotion:confusion|> En un caso como este, la evidencia física raramente habla por sí sola. Cada objeto, cada muestra, cada rastro puede formar parte de una narrativa forense, pero esa narrativa debe construirse con cuidado. La ausencia de huellas utilizables no excluye a nadie, pero tampoco cierra la puerta a otras interpretaciones. Es una pieza más del rompecabezas, ni decisiva ni irrelevante.

<|emotion:contemplation|> Uno de los componentes más importantes del caso es la evidencia relacionada con los medicamentos. Los análisis encontraron medicamentos psiquiátricos prescritos, entre ellos mirtazapina, lamotrigina, trazodona y quetiapina.

<|emotion:contemplation|> La mirtazapina es un antidepresivo que suele usarse para tratar la depresión mayor y a veces los problemas de sueño. La lamotrigina es un estabilizador del estado de ánimo, frecuentemente asociado al trastorno bipolar. La trazodona se prescribe comúnmente para el insomnio y también como antidepresivo. La quetiapina es un antipsicótico atípico que puede usarse para tratar diversas condiciones psiquiátricas, incluyendo el insomnio severo y algunos trastornos del estado de ánimo.

<|emotion:contemplation|> El toxicólogo Justin Brower declaró durante el juicio. Según su testimonio, la quetiapina estaba algo elevada, pero los niveles encontrados no correspondían a una sobredosis tóxica. Los resultados tampoco demostraron una intoxicación que, por sí sola, explicara el comportamiento.

<|emotion:confusion|> La interpretación de estos datos es distinta para cada parte. La defensa sostiene que Clancy estaba tomando múltiples medicamentos durante una crisis psiquiátrica y que el tratamiento pudo haber influido en su estado mental. La fiscalía puede utilizar los resultados para cuestionar la teoría de que una intoxicación o sobredosis provocó el comportamiento.

<|emotion:contemplation|> En conclusión, los medicamentos son relevantes para entender el contexto médico. Sin embargo, la toxicología por sí sola no demuestra que Clancy estuviera psicótica. Tampoco demuestra que los medicamentos fueran irrelevantes para su estado mental. Son una pieza más del conjunto, interpretable de distintas maneras.

<|emotion:sadness|> El historial psicológico y psiquiátrico de Lindsay Clancy constituye una de las partes centrales del juicio. Antes de los hechos se documentaron problemas como depresión, ansiedad, insomnio, pensamientos suicidas, deterioro emocional, dificultades relacionadas con la maternidad y tratamiento psiquiátrico.

<|emotion:longing|> Este historial es importante porque demuestra que existía una crisis psicológica previa a los acontecimientos. No se trata de una persona sin antecedentes. Se trata de alguien que había buscado o recibido ayuda profesional antes de aquel día. Alguien que, según las personas cercanas, había cambiado visiblemente.

<|emotion:contemplation|> A comienzos de enero de dos mil veintitrés, pocos días antes de los hechos, Clancy ingresó voluntariamente en el McLean Hospital. Durante esa hospitalización recibió tratamiento por problemas relacionados con depresión, ansiedad, insomnio y pensamientos suicidas.

<|emotion:confusion|> Los profesionales que declararon posteriormente en el juicio indicaron que no habían observado características psicóticas durante esa hospitalización. Uno de los diagnósticos discutidos fue trastorno depresivo mayor grave, sin características psicóticas. Esto constituye una pieza importante de la estrategia de la fiscalía.

<|emotion:contemplation|> La defensa plantea una cuestión diferente. Su argumento esencial es que los profesionales pudieron no haber reconocido correctamente la gravedad o la naturaleza de la enfermedad mental de Clancy. Esto genera una pregunta compleja: ¿la ausencia de un diagnóstico de psicosis significa necesariamente que no existía psicosis?

<|emotion:confusion|> No necesariamente. Sin embargo, tampoco puede afirmarse lo contrario sin evidencia médica suficiente. La defensa tendrá que demostrar mediante sus expertos cómo una enfermedad psicótica pudo haberse desarrollado o no haber sido detectada pese a las evaluaciones realizadas poco antes de los hechos.

<|emotion:contemplation|> Este es uno de los puntos más técnicos del juicio. Los síntomas psicóticos no siempre son evidentes en una primera evaluación. Algunas condiciones evolucionan rápidamente. Los profesionales pueden no ver lo que aún no ha emergido del todo. Pero convertir esa posibilidad en una conclusión forense sólida requiere evidencia médica concreta, no solo especulación.

<|emotion:sadness|> Una de las piezas de evidencia más importantes es un diario manuscrito perteneciente a Clancy. Durante el juicio se presentaron contenidos relacionados con su estado emocional. El diario documenta cuestiones como ansiedad, problemas de sueño, culpa, sentirse sobrepasada, deterioro emocional y pensamientos perturbadores.

<|emotion:contemplation|> Un diario personal es una ventana incompleta pero potente. Muestra cómo una persona se percibe a sí misma, qué palabras usa para describir su mundo interior, qué miedos no comparte con nadie más. En un juicio, sin embargo, un diario también puede usarse de formas opuestas.

<|emotion:contemplation|> La defensa puede utilizar el diario para mostrar un deterioro psicológico progresivo. La fiscalía puede argumentar que el diario demuestra que Clancy comprendía su situación, podía describir sus pensamientos, podía reflexionar sobre sus problemas y mantenía cierto grado de organización cognitiva. Por tanto, el diario es un ejemplo de evidencia que puede tener interpretaciones opuestas.

<|emotion:longing|> Patrick Clancy, esposo de Lindsay, también declaró durante el juicio. Su testimonio tiene particular importancia porque conocía personalmente a Lindsay y podía describir su comportamiento antes de los acontecimientos. Patrick y otras personas cercanas a la familia han descrito a Clancy como una madre afectuosa y dedicada. También se ha hablado de su deterioro psicológico y de sus problemas de salud mental.

<|emotion:sadness|> Patrick ha expresado públicamente que perdona a Lindsay y que considera que la enfermedad mental tuvo un papel fundamental en lo ocurrido. Sin embargo, sus opiniones personales no determinan la responsabilidad criminal. El jurado debe evaluar la evidencia completa, no solo el dolor de un padre que ha perdido a sus tres hijos.

<|emotion:contemplation|> La fiscalía también ha presentado evidencia relacionada con mensajes, planes familiares, comunicaciones, actividades previstas y comportamiento previo a los hechos. Este material puede utilizarse para analizar la capacidad de Clancy para planificar, comunicarse, organizar actividades, mantener conversaciones y tomar decisiones.

<|emotion:bitterness|> La fiscalía puede interpretar esto como evidencia de organización y conciencia. La defensa puede argumentar que una persona con una enfermedad mental grave puede mantener conversaciones normales y realizar actividades cotidianas incluso durante una crisis psiquiátrica. La superficie puede parecer controlada mientras algo mucho más profundo se descompone.

<|emotion:contemplation|> Así, el juicio enfrenta dos narrativas muy diferentes. La fiscalía intenta presentar una narrativa basada en la actuación deliberada. Según esta interpretación, Clancy tenía conocimiento de sus circunstancias, su esposo salió de la vivienda, ella permaneció sola con los niños, durante ese período ocurrieron los hechos, y su conducta posterior forma parte de la evidencia sobre su estado mental y sus intenciones.

<|emotion:bitterness|> La fiscalía cuestiona que Clancy estuviera en un estado psicótico que eliminara su responsabilidad criminal. Su posición general es que la evidencia demuestra una conducta suficientemente organizada y deliberada.

<|emotion:sadness|> La defensa presenta una narrativa muy diferente. Su argumento puede resumirse de la siguiente manera. Clancy experimentó un deterioro psicológico progresivo. Tenía depresión y ansiedad graves. Sufría problemas importantes de sueño. Presentaba pensamientos suicidas. Recibió tratamiento psiquiátrico. Tomaba varios medicamentos. Su condición pudo haber evolucionado hacia una enfermedad mental mucho más grave. La psicosis posparto pudo haber afectado su percepción de la realidad. Y su estado mental pudo haber impedido que comprendiera o controlara adecuadamente sus acciones.

<|emotion:contemplation|> Por tanto, la defensa busca demostrar que la enfermedad mental afectó su responsabilidad jurídica. La principal dificultad para la defensa es que los profesionales que evaluaron a Clancy poco antes de los hechos no diagnosticaron psicosis.

<|emotion:confusion|> Esto obliga a los expertos de la defensa a explicar cómo pudo desarrollarse la enfermedad, por qué no fue detectada, qué síntomas estaban presentes, cómo esos síntomas se relacionan con la psicosis posparto, cómo los medicamentos pudieron influir, y cómo todo ello afecta la responsabilidad criminal.

<|emotion:contemplation|> La fiscalía también enfrenta una dificultad importante. No puede simplemente argumentar que Clancy no tenía problemas psiquiátricos. La evidencia demuestra que existía un historial considerable de depresión, ansiedad, insomnio, pensamientos suicidas, tratamiento psiquiátrico, hospitalización, medicamentos y deterioro emocional.

<|emotion:confusion|> Por eso la verdadera discusión no es si estaba enferma. La verdadera discusión es qué tan grave era su enfermedad y hasta qué punto afectó su capacidad mental y su responsabilidad criminal.

<|emotion:awe|> Una de las cuestiones más interesantes del caso es el conflicto entre dos tipos de evidencia. La evidencia médica puede mostrar diagnóstico, síntomas, medicamentos, hospitalización, historial psicológico y observaciones de médicos. La evidencia conductual puede mostrar planificación, comunicaciones, acciones, comportamiento, decisiones y conducta antes y después de los acontecimientos.

<|emotion:contemplation|> El jurado tendrá que determinar cómo se relacionan ambos conjuntos de evidencia. ¿Puede alguien estar lo suficientemente enfermo como para perder el contacto con la realidad y, al mismo tiempo, mantener apariencias de normalidad? Los psiquiatras dirían que sí, en algunos casos. Pero ese sí general no resuelve el caso particular de Lindsay Clancy.

<|emotion:contemplation|> ¿Qué papel tiene la psicosis posparto? La psicosis posparto es una condición psiquiátrica grave que puede aparecer después del parto. Puede incluir alteraciones importantes de la percepción de la realidad.

<|emotion:awe|> Sin embargo, es importante evitar una conclusión incorrecta. Tener depresión posparto no significa tener psicosis posparto. Son condiciones diferentes. Tampoco significa que una persona con psicosis posparto automáticamente sea incapaz de responsabilidad criminal. La cuestión jurídica depende de las leyes aplicables y de la evidencia médica concreta del caso.

<|emotion:contemplation|> Durante el juicio de Clancy surgió otro caso relevante en Massachusetts. La Corte Suprema Judicial de Massachusetts ordenó un nuevo juicio en el caso de Latarsha Sanders. La decisión estuvo relacionada con la exclusión de determinados registros psiquiátricos que podían ser relevantes para la defensa. El juez William Sullivan está relacionado con ambos procedimientos.

<|emotion:confusion|> Esto no significa que Clancy vaya a recibir automáticamente un nuevo juicio. Tampoco significa que el resultado del caso Clancy esté predeterminado. Pero constituye un desarrollo jurídico que merece seguimiento porque involucra cuestiones relacionadas con evidencia de salud mental y defensa criminal.

<|emotion:contemplation|> La evidencia disponible no permite describir el caso como sencillo. La atribución física de los acontecimientos y la cuestión de la responsabilidad criminal son problemas diferentes.

<|emotion:sadness|> La pregunta central del juicio puede resumirse así: ¿qué estaba ocurriendo psicológicamente con Lindsay Clancy en el momento exacto de los hechos? No basta con demostrar que estaba deprimida. No basta con demostrar que tomaba medicamentos. No basta con demostrar que había sido hospitalizada. Tampoco basta con demostrar que podía mantener una conversación normal.

<|emotion:contemplation|> El jurado debe valorar la totalidad de la evidencia y determinar si se cumplen los elementos legales de los cargos. El caso Lindsay Clancy combina tres áreas extremadamente complejas: evidencia forense, psiquiatría y derecho penal.

<|emotion:sadness|> La evidencia disponible demuestra que existía un historial significativo de deterioro psicológico. Sin embargo, también existe evidencia que cuestiona que Clancy estuviera sufriendo una psicosis que eliminara su responsabilidad criminal.

<|emotion:helplessness|> Por eso el resultado dependerá probablemente de la interpretación que el jurado haga de los testimonios de los expertos, los registros médicos, el diario, la evidencia física, las comunicaciones y el comportamiento de Clancy antes y después de los hechos.

<|emotion:contemplation|> Al siete de agosto de dos mil veintiséis, el juicio continúa. No hay veredicto. No hay conclusión judicial definitiva sobre la responsabilidad criminal de Lindsay Clancy.

<|emotion:sadness|> Lo que sí queda es una historia que obliga a reflexionar sobre cómo identificamos las crisis de salud mental, cómo distinguimos la enfermedad de la responsabilidad, y hasta qué punto una sociedad está dispuesta a escuchar lo que ocurre bajo la superficie de una familia que parece funcionar.

<|emotion:contemplation|> Este episodio no intenta dar una respuesta. Solo intenta contar, con el respeto que merecen las víctimas, las complejidades de un caso donde la tragedia y el derecho se encuentran en un mismo tribunal.
""".strip()


def validate_tags():
    tags = re.findall(r"<\|([a-z]+:[a-z_]+)\|>", SCRIPT)
    invalid = [t for t in tags if t not in HIGGS_TAGS]
    if invalid:
        raise ValueError(f"Invalid Higgs tags: {invalid}")
    print(f"OK: {len(tags)} Higgs tags, all valid")
    words = len(SCRIPT.split())
    minutes = words / 150
    print(f"Palabras: {words}, duración estimada: {minutes:.1f} min")


def create_episode():
    payload = {
        "title": "El caso Lindsay Clancy: ¿enfermedad mental o responsabilidad criminal?",
        "type": "podcast",
        "source_text": SCRIPT,
        "voice_id": "clone:alejandra",
        "target_duration_minutes": 17,
        "background_music": "arctsound-mysterious-suspense-background-no-copyright-music-252023",
        "bg_music_volume": -18.0,
    }
    req = urllib.request.Request(
        f"{API_BASE}/api/episodes",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


if __name__ == "__main__":
    validate_tags()
    episode = create_episode()
    print(json.dumps(episode, indent=2, ensure_ascii=False))
