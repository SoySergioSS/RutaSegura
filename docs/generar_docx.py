import sys
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

SHOTS = sys.argv[1]
SALIDA = sys.argv[2]

doc = Document()
sec = doc.sections[0]
sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
sec.left_margin = sec.right_margin = Cm(2.5)
sec.top_margin = sec.bottom_margin = Cm(2.5)

AZUL = RGBColor(0x1F, 0x3A, 0x5F)
GRIS = RGBColor(0x55, 0x5E, 0x6E)

st = doc.styles["Normal"]
st.font.name = "Calibri"
st.font.size = Pt(11)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
st.paragraph_format.space_after = Pt(6)
st.paragraph_format.line_spacing = 1.15
for nombre, tam, antes in (("Heading 1", 15, 18), ("Heading 2", 13, 12), ("Heading 3", 11.5, 10)):
    h = doc.styles[nombre]
    h.font.name = "Calibri"
    h.font.size = Pt(tam)
    h.font.bold = True
    h.font.color.rgb = AZUL
    h.paragraph_format.space_before = Pt(antes)
    h.paragraph_format.space_after = Pt(6)
    h.paragraph_format.keep_with_next = True
    rpr = h.element.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts"); rpr.append(fonts)
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        fonts.set(qn(a), "Calibri")
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        if fonts.get(qn(a)) is not None:
            del fonts.attrib[qn(a)]


# ---------------------------------------------------------------- utilidades
def P(texto="", negrita_inicial=None, alin="justify", cursiva=False, tam=None, color=None, despues=None):
    p = doc.add_paragraph()
    if alin == "justify":
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    elif alin == "center":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if negrita_inicial:
        r = p.add_run(negrita_inicial); r.bold = True
        if tam: r.font.size = Pt(tam)
    r = p.add_run(texto)
    r.italic = cursiva
    if tam: r.font.size = Pt(tam)
    if color: r.font.color.rgb = color
    if despues is not None: p.paragraph_format.space_after = Pt(despues)
    return p


def rico(partes, alin="justify", estilo=None):
    """partes: lista de (texto, 'b'|'i'|'')"""
    p = doc.add_paragraph(style=estilo) if estilo else doc.add_paragraph()
    if alin == "justify": p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    for t, f in partes:
        r = p.add_run(t)
        r.bold = "b" in f
        r.italic = "i" in f
    return p


def B(texto, negrita=None, nivel=0):
    p = doc.add_paragraph(style="List Bullet" if nivel == 0 else "List Bullet 2")
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(3)
    if negrita:
        r = p.add_run(negrita); r.bold = True
    p.add_run(texto)
    return p


def N(texto, negrita=None):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.left_indent = Cm(1.2)
    p.paragraph_format.first_line_indent = Cm(-1.2)
    p.paragraph_format.space_after = Pt(3)
    if negrita:
        r = p.add_run(negrita); r.bold = True
    p.add_run(texto)
    return p


def H(texto, nivel):
    return doc.add_heading(texto, level=nivel)


def sombrear(celda, color):
    tcPr = celda._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), color)
    tcPr.append(shd)


contador = {"tabla": 0, "figura": 0}


def leyenda(tipo, texto):
    contador[tipo] += 1
    etiqueta = "Tabla" if tipo == "tabla" else "Figura"
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(f"{etiqueta} {contador[tipo]}"); r.bold = True; r.font.size = Pt(10)
    p2 = doc.add_paragraph()
    p2.paragraph_format.space_after = Pt(4)
    p2.paragraph_format.keep_with_next = True
    r = p2.add_run(texto); r.italic = True; r.font.size = Pt(10)


def nota(texto):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(10)
    r = p.add_run("Nota. "); r.italic = True; r.font.size = Pt(9); r.font.color.rgb = GRIS
    r = p.add_run(texto); r.font.size = Pt(9); r.font.color.rgb = GRIS


def T(titulo, encabezado, filas, anchos, fuente=None, tam=9.5):
    leyenda("tabla", titulo)
    t = doc.add_table(rows=1, cols=len(encabezado))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for i, txt in enumerate(encabezado):
        c = t.rows[0].cells[i]
        c.text = ""
        r = c.paragraphs[0].add_run(txt); r.bold = True; r.font.size = Pt(tam); r.font.color.rgb = RGBColor(255, 255, 255)
        sombrear(c, "1F3A5F")
    for k, fila in enumerate(filas):
        cells = t.add_row().cells
        for i, txt in enumerate(fila):
            cells[i].text = ""
            par = cells[i].paragraphs[0]
            if isinstance(txt, tuple):
                r = par.add_run(txt[0]); r.bold = True
            else:
                r = par.add_run(str(txt))
            r.font.size = Pt(tam)
            par.paragraph_format.space_after = Pt(0)
            if k % 2 == 1:
                sombrear(cells[i], "EEF2F7")
    for fila in t.rows:
        for i, w in enumerate(anchos):
            fila.cells[i].width = Cm(w)
    # repetir encabezado
    trPr = t.rows[0]._tr.get_or_add_trPr()
    th = OxmlElement("w:tblHeader"); th.set(qn("w:val"), "true"); trPr.append(th)
    if len(t.rows) <= 13:  # mantener tablas cortas en una sola pagina
        for fila in t.rows[:-1]:
            for c in fila.cells:
                for par in c.paragraphs:
                    par.paragraph_format.keep_with_next = True
    for fila in t.rows:
        trPr = fila._tr.get_or_add_trPr()
        cs = OxmlElement("w:cantSplit"); cs.set(qn("w:val"), "true"); trPr.append(cs)
    nota(fuente or "Elaboración propia.")
    return t


def F(ruta, titulo, ancho=15.5, fuente=None):
    leyenda("figura", titulo)
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(ruta, width=Cm(ancho))
    nota(fuente or "Elaboración propia.")


def formula(texto, etiqueta):
    t = doc.add_table(rows=1, cols=2)
    t.autofit = False
    c0, c1 = t.rows[0].cells
    c0.width, c1.width = Cm(14), Cm(2)
    c0.text = ""; c1.text = ""
    p = c0.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(texto); r.italic = True; r.font.size = Pt(11.5); r.font.name = "Cambria Math"
    p = c1.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.add_run(f"({etiqueta})")
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def codigo(lineas):
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    c = t.rows[0].cells[0]
    c.width = Cm(16)
    sombrear(c, "F4F6F9")
    c.text = ""
    p = c.paragraphs[0]
    for i, l in enumerate(lineas):
        r = p.add_run(l); r.font.name = "Consolas"; r.font.size = Pt(9)
        if i < len(lineas) - 1:
            r.add_break()
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def salto():
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def campo(parrafo, instr):
    r = parrafo.add_run()
    f1 = OxmlElement("w:fldChar"); f1.set(qn("w:fldCharType"), "begin")
    it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = instr
    f2 = OxmlElement("w:fldChar"); f2.set(qn("w:fldCharType"), "separate")
    t = OxmlElement("w:t"); t.text = "Clic derecho → Actualizar campo para generar el índice."
    f3 = OxmlElement("w:fldChar"); f3.set(qn("w:fldCharType"), "end")
    r._r.append(f1); r._r.append(it); r._r.append(f2); r._r.append(t); r._r.append(f3)


# ================================================================= CARATULA
for _ in range(1):
    doc.add_paragraph()
P("UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS", alin="center", tam=16, despues=2).runs[0].bold = True
P("Universidad del Perú, Decana de América", alin="center", cursiva=True, tam=11, color=GRIS, despues=14)
P("FACULTAD DE INGENIERÍA DE SISTEMAS E INFORMÁTICA", alin="center", tam=13, despues=40).runs[0].bold = True
P("EXAMEN PARCIAL", alin="center", tam=14, color=AZUL, despues=30).runs[0].bold = True
p = P("FOCOS DE ALERTA", alin="center", tam=24, color=AZUL, despues=6); p.runs[0].bold = True
P("Sistema georreferenciado de registro ciudadano de factores físicos de riesgo y generación de rutas "
  "seguras mediante trazado de rutas en mapa", alin="center", tam=13, despues=6)
P("Caso de aplicación: zona piloto Canto Rey – Los Jardines – Bayóvar, San Juan de Lurigancho, Lima",
  alin="center", cursiva=True, tam=11, color=GRIS, despues=50)

tc = doc.add_table(rows=4, cols=2)
tc.alignment = WD_TABLE_ALIGNMENT.CENTER
datos = [("Curso:", "______________________________________"),
         ("Docente:", "______________________________________"),
         ("Integrantes:", "______________________________________\n______________________________________\n"
                          "______________________________________\n______________________________________\n"
                          "______________________________________"),
         ("Ciclo / Sección:", "______________________________________")]
for i, (a, b) in enumerate(datos):
    tc.rows[i].cells[0].width = Cm(4); tc.rows[i].cells[1].width = Cm(10)
    tc.rows[i].cells[0].text = ""; tc.rows[i].cells[0].paragraphs[0].add_run(a).bold = True
    tc.rows[i].cells[1].text = b
for _ in range(3):
    doc.add_paragraph()
P("Lima, Perú — 2026", alin="center", tam=12).runs[0].bold = True
salto()

# ================================================================= INDICE
p = P("Índice", alin="left", tam=15, color=AZUL); p.runs[0].bold = True
campo(doc.add_paragraph(), 'TOC \\o "1-3" \\h \\z \\u')
salto()

# ================================================================= PARTE I
p = P("PARTE I", alin="center", tam=16, color=AZUL); p.runs[0].bold = True

H("1. Planteamiento del problema", 1)
H("1.1 Descripción del problema", 2)
P("La inseguridad ciudadana es el principal problema percibido por la población de Lima. Según el Instituto Nacional "
  "de Estadística e Informática, en el año 2025 el 27,6 % de la población de 15 y más años de Lima Metropolitana fue "
  "víctima de algún hecho delictivo, el 85,5 % cree que lo será en los próximos doce meses y el 62,9 % se siente "
  "inseguro al caminar solo por su zona o barrio de noche; además, el porcentaje de víctimas de hechos cometidos con "
  "arma de fuego subió de 12,4 % a 16,0 % en un año (INEI, 2026). El delito más frecuente en el área urbana es el robo o "
  "intento de robo de dinero, cartera o celular, que afecta a 16 de cada 100 personas: un delito que ocurre "
  "principalmente en la vía pública, mientras la persona se desplaza.")
P("San Juan de Lurigancho (SJL), el distrito más poblado del país con más de un millón de habitantes (INEI, 2018), "
  "concentra buena parte de esta problemática: en 2023 fue el distrito de Lima con más denuncias por robo, 5 931 entre "
  "enero y noviembre (Infobae, 2023), y en 2025 encabezó las denuncias por extorsión con más de 1 174 casos (La "
  "República, 2025). La propia central de serenazgo del distrito identificó 812 puntos críticos mediante su mapa del "
  "delito, ubicados en zonas como Zárate, Canto Rey, Bayóvar, Santa Elizabeth y Mariscal Cáceres (Chumpitaz, 2019).")
P("En los sectores de expansión urbana de SJL el territorio se ocupó antes que la infraestructura: existen calles y "
  "escaleras sin alumbrado, lotes baldíos usados como botaderos, inmuebles abandonados, paraderos sin iluminación y "
  "cámaras de videovigilancia inoperativas. La criminología ambiental ha mostrado que estos factores físicos facilitan "
  "el delito porque reducen la vigilancia natural y el control del espacio (Jeffery, 1971; Newman, 1972) y transmiten "
  "una señal de abandono que favorece el desorden (Wilson y Kelling, 1982).")
P("El problema central que aborda este proyecto es que esa información sobre el riesgo existe en el barrio, pero no "
  "existe en ningún registro útil para el peatón. Los vecinos saben qué cuadra está a oscuras o en qué esquina robaron "
  "la semana pasada, pero ese conocimiento está disperso en conversaciones y grupos de mensajería. El mapa del delito "
  "policial no es público ni se actualiza en tiempo útil, y no registra los factores físicos. Las aplicaciones de "
  "navegación de uso masivo calculan la ruta más corta o más rápida, sin considerar si atraviesa un tramo donde hubo "
  "un asalto ayer o un pasaje sin luz. En consecuencia, las personas eligen sus recorridos a pie por costumbre o por "
  "intuición, se exponen a riesgos evitables, y la municipalidad no cuenta con evidencia territorial actualizada para "
  "priorizar el alumbrado, la limpieza o el patrullaje.")
P("Si esta situación continúa, la población seguirá desplazándose expuesta a puntos de riesgo que podrían evitarse con "
  "rutas alternativas de longitud similar, y los factores físicos que facilitan el delito seguirán sin atenderse por "
  "falta de un registro que los haga visibles.")

H("1.2 Formulación del problema", 2)
H("Problema general", 3)
P("¿En qué medida un sistema georreferenciado de registro ciudadano de factores físicos de riesgo y de generación de "
  "rutas seguras reduce la exposición al riesgo en los desplazamientos peatonales de los habitantes de la zona piloto "
  "Canto Rey – Los Jardines – Bayóvar de San Juan de Lurigancho, en el año 2026?", cursiva=True)
H("Problemas específicos", 3)
N("¿De qué manera el registro ciudadano georreferenciado y la validación comunitaria permiten identificar y mantener "
  "actualizados los factores físicos de riesgo y los incidentes delictivos de la zona piloto?", "PE1. ")
N("¿Cómo se puede estimar un índice de riesgo por tramo de vía que considere el tipo de foco, su gravedad, su "
  "antigüedad, su credibilidad y la hora del recorrido?", "PE2. ")
N("¿En qué medida el trazado de rutas seguras reduce la exposición al riesgo respecto a la ruta más corta, y cuánta "
  "distancia adicional exige?", "PE3. ")
N("¿Cuál es el efecto del uso del sistema en la percepción de seguridad y cuál es su nivel de usabilidad para los "
  "habitantes de la zona piloto?", "PE4. ")

H("1.3 Antecedentes", 2)
H("1.3.1 Antecedentes a nivel global", 3)
rico([("Galbrun, Pelechrinis y Terzi (2016)", "b"), (", en ", ""), ("Urban navigation beyond shortest route: The case "
     "of safe paths", "i"), (", plantearon que la ruta más corta no es necesariamente la mejor para un peatón y "
     "formularon el problema de encontrar caminos que equilibren distancia y seguridad. Construyeron un modelo de riesgo "
     "a partir de datos abiertos de criminalidad de Chicago y Filadelfia sobre la red vial de OpenStreetMap, y "
     "propusieron algoritmos que devuelven un conjunto pequeño de rutas con distintos compromisos entre longitud y "
     "riesgo. Su aporte principal para este proyecto es demostrar que, en una red urbana real, existen rutas con mucho "
     "menor riesgo a cambio de un aumento moderado de la distancia; su limitación es que depende de datos oficiales, "
     "que en Lima no son públicos ni oportunos.", "")])
rico([("Shah, Bao, Lu y Chen (2011)", "b"), (" desarrollaron ", ""), ("CrowdSafe", "i"), (", un sistema para "
     "dispositivos móviles que combina incidentes delictivos reportados por los propios usuarios (crowdsourcing) con "
     "datos oficiales, y que ofrece rutas que evitan las zonas con más incidentes. Es uno de los primeros trabajos en "
     "unir registro ciudadano y navegación segura, y muestra la necesidad de mecanismos para filtrar reportes falsos o "
     "duplicados, aspecto que en el presente proyecto se aborda con la validación comunitaria de cada reporte.", "")])
rico([("Mata et al. (2016)", "b"), (" diseñaron un sistema de información móvil para la Ciudad de México que integra "
     "datos de criminalidad oficiales con datos obtenidos de la ciudadanía (incluidas publicaciones en redes sociales) "
     "para encontrar rutas seguras. Es un antecedente cercano a la realidad latinoamericana, con alta incidencia "
     "delictiva y subregistro de denuncias, y confirma la utilidad de complementar la información oficial con la que "
     "produce la propia población.", "")])
rico([("Viswanath y Basu (2015)", "b"), (" presentaron ", ""), ("SafetiPin", "i"), (", una aplicación usada en "
     "ciudades de la India en la que los usuarios auditan la seguridad de los espacios públicos evaluando factores "
     "físicos como el alumbrado, la visibilidad, la presencia de gente, la vigilancia y el estado de las veredas. La "
     "información recogida se entregó a los gobiernos locales y sirvió para priorizar mejoras de alumbrado. Es el "
     "antecedente más próximo en el enfoque de factores físicos de riesgo, y demuestra que el registro ciudadano "
     "puede convertirse en evidencia para la gestión municipal.", "")])
rico([("Plataformas de reporte urbano.", "b"), (" Iniciativas como FixMyStreet (mySociety, Reino Unido) permiten a los "
     "ciudadanos reportar en un mapa problemas de infraestructura (luminarias rotas, basura, baches) que se derivan a la "
     "autoridad responsable. No calculan rutas, pero validan el modelo de registro georreferenciado ciudadano como "
     "canal sostenible entre la población y el gobierno local.", "")])

H("1.3.2 Antecedentes a nivel nacional y local", 3)
rico([("Alvarado Vidal, Diaz Rivas, Salazar Huamaní y Espejo Gálvez (2024)", "b"), (", en su tesis de maestría ", ""),
      ("Modelo Prolab: “Comunidad Segura” – Aplicativo de seguridad", "i"), (" (CENTRUM PUCP), partieron de que los "
     "ciudadanos de San Juan de Lurigancho no tienen seguridad suficiente para transitar por la vía pública, y "
     "propusieron un aplicativo que reduce los incidentes mediante el reporte ciudadano y la información de rutas "
     "seguras. El trabajo valida la necesidad y la disposición de la población de SJL para usar una herramienta de "
     "este tipo, aunque se plantea como modelo de negocio y no desarrolla el algoritmo de cálculo de rutas.", "")])
rico([("Chumpitaz (2019)", "b"), (" informó que la central de operaciones del serenazgo de San Juan de Lurigancho, "
     "mediante su mapa del delito, identificó 812 puntos críticos en el distrito, concentrados en zonas como Zárate, "
     "Canto Rey, Bayóvar, 10 de Octubre, Caja de Agua, La Huayrona, Santa Elizabeth y Mariscal Cáceres. Este "
     "antecedente es relevante por dos razones: confirma que el problema tiene una expresión territorial clara, y "
     "muestra que esa información existe dentro de la institución pero no está disponible para el ciudadano que "
     "decide por dónde caminar. Tres de esas zonas (Canto Rey, Bayóvar y Santa Elizabeth) forman parte de la zona "
     "piloto de este proyecto.", "")])
rico([("Instituto Nacional de Estadística e Informática (2026)", "b"), (", en ", ""), ("Victimización en el Perú "
     "2025", "i"), (", reporta a partir de la ENAPRES que el 27,6 % de la población de 15 y más años de Lima "
     "Metropolitana fue víctima de un hecho delictivo, que solo el 21,6 % de las víctimas denunció el hecho, y que el "
     "62,9 % se siente inseguro al caminar de noche por su barrio. El bajo nivel de denuncia explica por qué los "
     "registros oficiales subestiman el riesgo real de la vía pública y justifica un canal de registro ciudadano "
     "complementario.", "")])
rico([("Registros policiales y periodísticos de SJL.", "b"), (" Con datos del Sistema de Denuncias Policiales "
     "(Sidpol), SJL fue en 2023 el distrito de Lima con más denuncias por robo (Infobae, 2023) y en 2025 el de más "
     "denuncias por extorsión (La República, 2025). Estas cifras justifican la elección del distrito, aunque no "
     "permiten identificar tramos concretos de calle, que es la escala a la que trabaja el presente sistema.", "")])

H("1.4 Justificación de la investigación", 2)
rico([("Justificación teórica. ", "b"), ("El proyecto aplica tres teorías de la criminología ambiental: la Prevención "
     "del Delito mediante el Diseño Ambiental (CPTED; Jeffery, 1971) y el espacio defendible (Newman, 1972), según las "
     "cuales el alumbrado, la visibilidad y el control del espacio influyen en la oportunidad delictiva; la teoría de "
     "las ventanas rotas (Wilson y Kelling, 1982), que vincula el deterioro físico con el desorden; y la teoría de las "
     "actividades rutinarias (Cohen y Felson, 1979), según la cual el delito ocurre cuando coinciden un agresor, una "
     "víctima y la ausencia de vigilancia. El sistema traduce estas teorías en un modelo cuantitativo que asigna pesos "
     "a cada factor y los combina con la recencia de los incidentes.", "")])
rico([("Justificación práctica. ", "b"), ("Ofrece al peatón una herramienta concreta para decidir por dónde caminar, "
     "con la ruta más segura disponible y los focos que quedan cerca de ella. A la junta vecinal y a la municipalidad "
     "les entrega un inventario georreferenciado, actualizado y exportable (CSV/GeoJSON) de factores físicos, que "
     "sirve para priorizar el mantenimiento del alumbrado, la limpieza de botaderos o la reparación de cámaras.", "")])
rico([("Justificación metodológica. ", "b"), ("Propone un índice de exposición al riesgo por ruta, medible y "
     "reproducible, y un protocolo de evaluación que compara de manera pareada la ruta segura con la ruta más corta "
     "sobre la red vial real. El código, los datos de la red y el script de evaluación quedan disponibles para que "
     "otros investigadores repliquen o ajusten el modelo en otros distritos.", "")])
rico([("Justificación social. ", "b"), ("La inseguridad al desplazarse afecta con más fuerza a quienes caminan: "
     "estudiantes, trabajadores que salen de madrugada o regresan de noche, adultos mayores y mujeres. El sistema no "
     "está limitado a un grupo: cualquier persona puede consultarlo y reportar, sin crear una cuenta ni entregar datos "
     "personales. Además, convierte la queja dispersa en un dato que la comunidad puede presentar ante la autoridad.", "")])
rico([("Justificación tecnológica. ", "b"), ("Se basa en tecnologías abiertas y de bajo costo (OpenStreetMap, Leaflet, "
     "Python, SQLite), funciona en el navegador del celular sin instalar una aplicación y puede desplegarse en un "
     "servidor económico, lo que lo hace viable para una municipalidad distrital.", "")])

H("1.5 Limitaciones de la investigación", 2)
B("El estudio se limita a una zona piloto de aproximadamente 3,3 × 3,3 km (≈ 10,9 km²) de San Juan de Lurigancho; "
  "los resultados no se pueden generalizar a todo el distrito sin un nuevo levantamiento.", "Alcance territorial: ")
B("El periodo de ejecución es de un ciclo académico (cuatro meses), con un piloto de campo de seis semanas; no se "
  "puede medir el efecto del sistema sobre la tasa de delitos, que requiere series de varios años.", "Alcance temporal: ")
B("La red vial proviene de OpenStreetMap, que puede omitir pasajes, escaleras o trochas informales de los "
  "asentamientos humanos, o incluir vías que en la práctica no son transitables.", "Calidad de la cartografía: ")
B("Los reportes ciudadanos pueden tener subregistro (zonas donde nadie reporta), sesgo (zonas que se reportan más) "
  "o reportes falsos. Se mitiga con validación comunitaria, límites por dispositivo y verificación de campo de una "
  "muestra, pero no se elimina.", "Sesgo del dato ciudadano: ")
B("El valor del sistema depende de que los vecinos lo usen; una baja participación reduciría la cobertura del "
  "mapa de riesgo. Por eso se trabaja con una junta vecinal y se mide la participación como resultado.", "Adopción: ")
B("No se integra información en tiempo real de la Policía Nacional ni del serenazgo, porque no existe un acceso "
  "público a esos datos.", "Acceso a datos oficiales: ")
B("Se requiere un celular con navegador e internet; las personas sin estos medios no pueden usar el sistema "
  "directamente.", "Brecha digital: ")
B("El sistema no publica rankings de barrios ni datos personales para no estigmatizar zonas ni exponer a "
  "personas, lo que limita ciertos análisis.", "Restricciones éticas: ")

# ================================================================= OBJETIVOS
H("2. Objetivos", 1)
H("2.1 Objetivo general", 2)
P("Desarrollar e implementar un sistema georreferenciado de registro ciudadano de factores físicos de riesgo y de "
  "generación de rutas seguras mediante trazado de rutas en mapa, para reducir la exposición al riesgo en los "
  "desplazamientos peatonales de los habitantes de la zona piloto Canto Rey – Los Jardines – Bayóvar de San Juan de "
  "Lurigancho, en el año 2026.")
H("2.2 Objetivos específicos", 2)
N("Diseñar e implementar un módulo de registro ciudadano anónimo y georreferenciado de factores físicos de riesgo e "
  "incidentes, con validación comunitaria de su vigencia.", "OE1. ")
N("Desarrollar un modelo de riesgo espacio-temporal que calcule un índice por tramo de vía según la categoría, "
  "gravedad, antigüedad y credibilidad de cada foco y la hora del recorrido.", "OE2. ")
N("Implementar un algoritmo de trazado de rutas seguras sobre la red vial real y evaluar su reducción de la "
  "exposición al riesgo y su distancia adicional frente a la ruta más corta.", "OE3. ")
N("Evaluar el efecto del uso del sistema en la percepción de seguridad de los habitantes de la zona piloto y "
  "medir su usabilidad.", "OE4. ")

# ================================================================= HIPOTESIS
H("3. Hipótesis", 1)
H("3.1 Hipótesis general", 2)
P("La implementación del sistema Focos de Alerta reduce significativamente la exposición al riesgo en los "
  "desplazamientos peatonales de los habitantes de la zona piloto de San Juan de Lurigancho.", cursiva=True)
H("3.2 Hipótesis específicas", 2)
N("El registro ciudadano georreferenciado con validación comunitaria permite identificar en la zona piloto al menos "
  "150 focos de riesgo durante el piloto, de los cuales al menos el 70 % se confirma en la verificación de campo.", "HE1. ")
N("El índice de riesgo por tramo asigna valores significativamente mayores a los tramos verificados en campo como "
  "peligrosos que a los tramos sin focos (prueba U de Mann-Whitney, α = 0,05).", "HE2. ")
N("En al menos el 70 % de los pares origen-destino evaluados, la ruta segura reduce la exposición al riesgo en 30 % "
  "o más con un aumento de distancia no mayor a 20 % respecto de la ruta más corta.", "HE3. ")
N("La percepción de seguridad de los participantes aumenta significativamente después de usar el sistema (prueba t "
  "para muestras relacionadas o Wilcoxon, α = 0,05), y la usabilidad alcanza un puntaje SUS de al menos 68.", "HE4. ")

H("3.3 Variables y operacionalización", 2)
T("Operacionalización de variables",
  ["Variable", "Dimensión", "Indicador", "Instrumento / unidad"],
  [[("VI: Sistema Focos de Alerta"), "Registro ciudadano", "N.º de reportes válidos; % confirmados en campo", "Base de datos; ficha de verificación"],
   ["", "Modelo de riesgo", "Índice de riesgo por tramo r(e)", "Motor de riesgo (adimensional)"],
   ["", "Trazado de rutas", "Tiempo de cálculo; % de rutas encontradas", "Registro del servidor (s, %)"],
   [("VD1: Exposición al riesgo en el desplazamiento"), "Exposición", "Exposición total E = Σ L(e)·r(e)", "Script de evaluación"],
   ["", "Eficiencia", "Aumento de distancia (%) y tiempo a pie (min)", "Script de evaluación"],
   ["", "Tramos críticos", "N.º de tramos con r(e) ≥ 0,5 atravesados", "Script de evaluación"],
   [("VD2: Percepción de seguridad"), "Percepción", "Puntaje medio de seguridad percibida (1–5)", "Cuestionario Likert pre/post"],
   ["", "Usabilidad", "Puntaje SUS (0–100)", "System Usability Scale"]],
  [3.6, 3.2, 5.0, 4.2])

# ================================================================= TIPO
H("4. Tipo de investigación", 1)
P("El proyecto se enmarca dentro de una investigación aplicada, ya que busca resolver un problema concreto de la "
  "realidad, la exposición de los peatones a factores de riesgo en la vía pública, mediante una solución tecnológica: "
  "un sistema de información geográfica con registro ciudadano y un algoritmo de rutas seguras. El enfoque es "
  "cuantitativo, porque las variables se miden numéricamente (índice de riesgo por tramo, exposición total de una ruta, "
  "distancia, puntajes de percepción y de usabilidad) y las hipótesis se contrastan con pruebas estadísticas.")
P("El nivel es explicativo, porque se busca establecer el efecto del sistema (variable independiente) sobre la "
  "exposición al riesgo y la percepción de seguridad (variables dependientes). El diseño es experimental en dos "
  "niveles: (a) un diseño experimental computacional de medidas pareadas, en el que cada par origen-destino se "
  "resuelve con la ruta más corta (control) y con la ruta segura (tratamiento) sobre la misma red y los mismos "
  "reportes; y (b) un diseño pre-experimental con preprueba y posprueba con un solo grupo, en el que se mide la "
  "percepción de seguridad de los participantes antes y después de seis semanas de uso. Por su temporalidad es "
  "longitudinal de corto plazo, ya que los datos de campo se recogen durante las seis semanas del piloto.")

# ================================================================= POBLACION
H("5. Población y muestra", 1)
H("5.1 Población", 2)
P("La población está conformada por los habitantes de 15 y más años del distrito de San Juan de Lurigancho, que "
  "supera el millón de habitantes según el Censo 2017 (INEI, 2018) y que se desplazan a pie por la vía pública. La "
  "población accesible son las personas que residen, estudian, trabajan o transitan habitualmente por la zona piloto.")
H("5.2 Lugar del muestreo: zona piloto", 2)
P("El estudio se realiza en la zona piloto Canto Rey – Los Jardines – Bayóvar, delimitada por el rectángulo "
  "comprendido entre las longitudes −77,015 y −76,985 y las latitudes −11,990 y −11,960 (aproximadamente 3,3 × 3,3 km "
  "y 10,9 km²). Incluye tramos de las avenidas Próceres de la Independencia, Fernando Wiesse, Canto Grande, Las Flores "
  "y El Sol, y las estaciones Los Jardines, Los Postes, San Carlos, San Martín, Santa Rosa y Bayóvar de la Línea 1 del "
  "Metro de Lima. Se eligió porque reúne zonas señaladas como críticas por el serenazgo (Chumpitaz, 2019) y alto "
  "flujo peatonal hacia el Metro, mercados y colegios.")
H("5.3 Muestra y unidades de análisis", 2)
P("El estudio trabaja con cuatro unidades de análisis, cada una con su propio criterio de selección:")
T("Unidades de análisis y tamaño de muestra",
  ["Unidad", "Qué es", "Tamaño", "Criterio de selección"],
  [[("Participantes"), "Vecinos de 15+ años que usan el sistema durante el piloto", "60 personas",
    "No probabilístico intencional, con apoyo de la junta vecinal. Para una prueba t pareada con efecto d = 0,4, α = 0,05 y potencia 0,80 se requieren 52; se suma 15 % por posibles abandonos."],
   [("Reportes (focos)"), "Factores físicos e incidentes registrados en el mapa", "Todos los del piloto (meta ≥ 150)",
    "Censal. Se verifica en campo una muestra aleatoria del 30 % de los factores físicos."],
   [("Red vial"), "Tramos de calle de OpenStreetMap", "10 737 nodos y 12 833 tramos",
    "Censal: la red completa de la zona piloto."],
   [("Rutas"), "Pares origen-destino a pie", "300 pares × 2 franjas = 600 comparaciones",
    "Aleatorio simple sobre los nodos de la red, distancia en línea recta ≥ 800 m, evaluados a las 11:00 y a las 21:00. Con 300 pares, una proporción se estima con un error de ±5,7 % al 95 % de confianza."]],
  [2.6, 4.2, 3.2, 6.0])
H("5.4 Objeto de registro: categorías de focos", 2)
P("El sistema registra dos grupos de focos. Los factores físicos son condiciones del entorno que facilitan el "
  "delito y permanecen hasta ser atendidas; los incidentes son hechos delictivos puntuales cuyo peso disminuye con "
  "el tiempo. Cada categoría tiene un peso y una vida media que se presentan en la Tabla 5.")
B("Factores físicos (8): alumbrado deficiente o apagado; lote baldío o terreno abandonado; cámara de vigilancia "
  "inoperativa; botadero o acumulación de basura; pasaje estrecho, muro ciego o escalera sin salida; inmueble "
  "abandonado; paradero inseguro o sin iluminación; vereda en mal estado o inexistente.")
B("Incidentes (4): robo al paso o arrebato; asalto con arma; acoso o intimidación; pandillaje o consumo de drogas "
  "en la vía pública.")

# ================================================================= INSTRUMENTOS
H("6. Instrumentos", 1)
H("6.1 Hardware", 2)
B("Celulares de los participantes (Android o iOS) con navegador web, GPS e internet móvil, para registrar focos y "
  "consultar rutas desde la calle.")
B("Computadora o servidor con procesador de 4 núcleos, 8 GB de RAM y conexión a internet, para alojar el servidor "
  "web y la base de datos. No se requiere procesamiento gráfico (GPU): el cálculo de una ruta toma menos de 0,1 s.")
H("6.2 Software y datos", 2)
B("Python 3.13 con el framework Flask 3.1 para el servidor y la API REST.", "Servidor: ")
B("SQLite para almacenar reportes y votos.", "Base de datos: ")
B("HTML5, CSS y JavaScript con la biblioteca Leaflet 1.9.4 y el complemento Leaflet.heat para el mapa interactivo y "
  "el mapa de calor.", "Interfaz: ")
B("OpenStreetMap: teselas del mapa base y red vial descargada mediante su API (licencia ODbL); Nominatim para "
  "buscar direcciones.", "Datos geográficos: ")
B("Algoritmo A* sobre un grafo ponderado y un modelo de riesgo con núcleo gaussiano, implementados en Python.", "Algoritmos: ")
B("pytest para pruebas unitarias y un script propio (evaluar_rutas.py) para la evaluación experimental de rutas.", "Pruebas: ")
B("Python (pandas/SciPy) o SPSS para las pruebas estadísticas.", "Análisis: ")
H("6.3 Instrumentos de recolección de datos", 2)
B("12 ítems en escala de Likert de 1 a 5 sobre la seguridad percibida al caminar de día y de noche en la zona, "
  "basados en los indicadores de percepción de la ENAPRES. Se valida por juicio de tres expertos y su confiabilidad "
  "se mide con el alfa de Cronbach (≥ 0,70). Se aplica antes y después del piloto.", "Cuestionario de percepción de seguridad: ")
B("cuestionario estándar de 10 ítems (Brooke, 1996) para medir la usabilidad del sistema.", "System Usability Scale (SUS): ")
B("formato para comprobar en el lugar una muestra de los focos registrados (existe / no existe / distinto), con "
  "fecha, hora y foto del entorno sin personas.", "Ficha de verificación de campo: ")
B("el propio sistema guarda cada reporte, voto y consulta de ruta (sin datos personales), y el script de evaluación "
  "calcula la exposición, la distancia y los tramos críticos de cada ruta.", "Registro automático del sistema: ")

# ================================================================= ARQUITECTURA
H("7. Diseño del modelo y arquitectura del sistema", 1)
P("Esta sección explica cómo funciona el sistema por dentro: su arquitectura, el modelo de datos, el modelo de "
  "riesgo, el algoritmo de rutas seguras y la interfaz. El prototipo descrito ya está implementado y funcionando "
  "sobre la red vial real de la zona piloto.")

H("7.1 Arquitectura general", 2)
P("El sistema sigue una arquitectura cliente-servidor de tres capas (Figura 1). La capa de presentación es una "
  "aplicación web que funciona en el navegador del celular o de la computadora. La capa de aplicación es un servidor "
  "Python con Flask que expone una API REST y contiene el motor de riesgo y el enrutador. La capa de datos almacena "
  "los reportes en SQLite y la red vial en un archivo precalculado a partir de OpenStreetMap.")
F(f"{SHOTS}/arquitectura.png", "Arquitectura del sistema Focos de Alerta", 16)

T("Componentes del sistema",
  ["Componente", "Responsabilidad"],
  [[("Interfaz web"), "Cuatro módulos: Ruta segura, Reportar, Focos (marcadores, mapa de calor o tramos coloreados, con filtros por categoría y antigüedad) y Estadísticas (indicadores, vías críticas y exportación)."],
   [("API REST (app.py)"), "Recibe y valida las peticiones: categoría válida, punto dentro de la zona, fecha no futura y de máximo un año, límite de 10 reportes por hora por dispositivo."],
   [("Gestión de reportes (db.py)"), "Alta de reportes y votos “sigue ahí” / “ya no existe”. Un reporte pasa a resuelto con 3 votos de “ya no existe” que superen a sus confirmaciones. Un dispositivo vota una vez por reporte."],
   [("Motor de riesgo (motor_riesgo.py)"), "Calcula la intensidad de cada reporte y el índice de riesgo de cada tramo de la red."],
   [("Enrutador (enrutador.py)"), "Carga el grafo vial, ubica el nodo más cercano al origen y al destino, y calcula con A* la ruta más corta y la ruta segura."],
   [("Índice espacial"), "Rejilla de celdas de 130 m que permite comparar cada reporte solo con los tramos cercanos, en lugar de con toda la red."],
   [("Caché de riesgo"), "Guarda el riesgo calculado por hora del día; se invalida cuando entra un reporte o un voto nuevo."],
   [("Herramientas"), "descargar_red_vial.py (OSM → grafo), generar_datos_demo.py (datos simulados) y evaluar_rutas.py (experimento)."]],
  [4.3, 11.7])

H("7.2 Modelo de datos", 2)
P("La red vial se representa como un grafo no dirigido G = (V, E), donde cada nodo v ∈ V es una intersección o "
  "punto de quiebre de una calle con sus coordenadas, y cada arista e ∈ E es un tramo transitable a pie con su "
  "longitud L(e) en metros, su tipo de vía y su nombre. Se incluyen avenidas, calles residenciales, peatonales, "
  "senderos, escaleras y vías de servicio, y se excluyen las vías marcadas como privadas o prohibidas para peatones. "
  "Los reportes se guardan en la base de datos según la Tabla 4.")
T("Estructura de la tabla de reportes",
  ["Campo", "Tipo", "Descripción"],
  [["id", "entero", "Identificador del reporte"],
   ["categoria", "texto", "Una de las 12 categorías (8 físicas y 4 de incidentes)"],
   ["lat, lon", "real", "Ubicación del foco elegida en el mapa"],
   ["severidad", "entero 1–3", "Leve, moderada o grave"],
   ["fecha_hecho / hora_hecho", "fecha / entero", "Cuándo ocurrió o se observó; la hora solo para incidentes"],
   ["descripcion", "texto ≤ 280", "Detalle opcional, sin nombres de personas"],
   ["confirmaciones / votos_resuelto", "entero", "Validación comunitaria"],
   ["estado", "texto", "activo, resuelto o descartado"],
   ["autor_hash", "texto", "Hash irreversible del dispositivo; nunca se guarda el identificador original"]],
  [4.6, 3.0, 8.4])

H("7.3 Modelo de riesgo", 2)
P("El modelo convierte cada reporte en un aporte de riesgo y lo distribuye en las calles cercanas. Primero se "
  "calcula la intensidad del reporte i:")
formula("Iᵢ = w_c · s · e^(−ln2 · edad / T½) · κ · h", "1")
P("donde w_c es el peso de la categoría, s el factor de severidad (0,6; 1,0 o 1,4), T½ la vida media de la "
  "categoría en días, κ el factor de credibilidad y h el factor horario. El término exponencial hace que el aporte "
  "se reduzca a la mitad cada T½ días: un robo pesa la mitad a las tres semanas, mientras que un poste apagado se "
  "mantiene durante meses hasta que la comunidad lo marque como resuelto. Los aportes menores al 5 % se descartan.")
formula("κ = mín(1,3 ; máx(0 ; 0,6 + 0,2·confirmaciones − 0,25·votos_resuelto))", "2")
P("El factor horario h refleja que el riesgo cambia durante el día: el alumbrado deficiente pesa 1,8 veces de noche "
  "(18:00 a 6:00) y 0,4 de día, y un incidente pesa 1,3 si la consulta se hace dentro de ±3 horas de la hora en que "
  "ocurrió y 0,8 fuera de esa franja. Luego, el riesgo de cada tramo e es la suma de los aportes de los reportes "
  "cercanos, atenuados con la distancia d(i, e) entre el reporte y el tramo mediante un núcleo gaussiano:")
formula("r(e) = Σᵢ Iᵢ · exp(−d(i,e)² / 2σ²),   para d(i,e) ≤ 130 m,   σ = 45 m", "3")
T("Parámetros por categoría",
  ["Categoría", "Grupo", "Peso w_c", "Vida media T½", "Factor noche / día"],
  [["Alumbrado deficiente", "Físico", "0,8", "120 días", "1,8 / 0,4"],
   ["Lote baldío", "Físico", "0,6", "180 días", "1,4 / 0,8"],
   ["Cámara inoperativa", "Físico", "0,4", "120 días", "1,2 / 1,0"],
   ["Botadero", "Físico", "0,5", "90 días", "1,3 / 0,9"],
   ["Pasaje estrecho / muro ciego", "Físico", "0,6", "365 días", "1,6 / 0,8"],
   ["Inmueble abandonado", "Físico", "0,7", "180 días", "1,5 / 0,9"],
   ["Paradero inseguro", "Físico", "0,6", "120 días", "1,5 / 0,9"],
   ["Vereda en mal estado", "Físico", "0,3", "365 días", "1,3 / 1,0"],
   ["Robo al paso", "Incidente", "1,0", "21 días", "±3 h: 1,3 / 0,8"],
   ["Asalto con arma", "Incidente", "1,4", "30 días", "±3 h: 1,3 / 0,8"],
   ["Acoso o intimidación", "Incidente", "0,9", "21 días", "±3 h: 1,3 / 0,8"],
   ["Pandillaje / consumo", "Incidente", "0,8", "45 días", "1,3 / 0,8 y ±3 h"]],
  [5.0, 2.2, 2.2, 2.8, 3.8],
  "Valores iniciales definidos a partir de la literatura de criminología ambiental; se calibrarán con los resultados "
  "de la verificación de campo del piloto.")

H("7.4 Algoritmo de trazado de rutas seguras", 2)
P("La ruta segura se obtiene minimizando un costo que combina la longitud del tramo y su riesgo. El parámetro λ "
  "controla la prioridad que el usuario da a la seguridad: con λ = 0 se obtiene la ruta más corta y, a medida que λ "
  "crece, el algoritmo acepta rutas más largas para evitar tramos peligrosos. En la interfaz el usuario elige una "
  "prioridad de 0 a 10, y λ = 1,5 × prioridad.")
formula("c(e) = L(e) · (1 + λ · r(e))", "4")
formula("E(ruta) = Σ_{e ∈ ruta} L(e) · r(e)        Índice de exposición = 100 · E / Σ L(e)", "5")
P("Se usa el algoritmo A* con la distancia en línea recta al destino como heurística. Esta heurística es admisible "
  "porque el costo de cada tramo nunca es menor que su longitud (c(e) ≥ L(e)), lo que garantiza que la ruta "
  "encontrada es la de menor costo. El procedimiento completo se resume en la Figura 2 y en el siguiente pseudocódigo:")
F(f"{SHOTS}/flujo.png", "Flujo de cálculo de la ruta segura", 16)
codigo([
    "ALGORITMO RutaSegura(origen, destino, prioridad, hora)",
    "  reportes ← reportes con estado = 'activo'",
    "  PARA cada reporte i:  Iᵢ ← intensidad(i, ahora, hora)           // ec. (1) y (2)",
    "  PARA cada tramo e:    r(e) ← Σ Iᵢ · exp(−d² / 2σ²)  (rejilla)    // ec. (3)",
    "  o ← nodo más cercano(origen);  d ← nodo más cercano(destino)",
    "  corta  ← A*(o, d, costo = L(e))                                  // λ = 0",
    "  segura ← A*(o, d, costo = L(e)·(1 + λ·r(e))),  λ = 1,5·prioridad // ec. (4)",
    "  PARA cada ruta: distancia, tiempo = distancia / 1,25 m/s,",
    "                  exposición E, tramos críticos (r ≥ 0,5),",
    "                  focos a menos de 60 m                             // ec. (5)",
    "  DEVOLVER segura, corta, reducción de E (%), distancia extra (%)",
])

H("7.5 Interfaz del prototipo", 2)
P("La Figura 3 muestra una consulta de ruta a las 21:00 en la zona piloto: la ruta segura (verde continuo) rodea "
  "los focos que atraviesa la ruta más corta (gris punteado). El panel indica que la exposición al riesgo se reduce "
  "en más de 99 % caminando 414 m más (+8,9 %). La Figura 4 muestra la vista de tramos, donde cada calle se colorea "
  "según su índice de riesgo, y la Figura 5 el módulo de estadísticas para el informe a la municipalidad.")
F(f"{SHOTS}/2_ruta.png", "Módulo de ruta segura: comparación entre la ruta segura y la ruta más corta (21:00)", 16,
  "Captura del prototipo con reportes simulados de demostración. Mapa base © colaboradores de OpenStreetMap.")
F(f"{SHOTS}/4_tramos.png", "Vista de tramos de calle coloreados según su índice de riesgo", 16,
  "Captura del prototipo con reportes simulados de demostración. Mapa base © colaboradores de OpenStreetMap.")
F(f"{SHOTS}/6_stats.png", "Módulo de estadísticas y exportación de datos", 16,
  "Captura del prototipo con reportes simulados de demostración.")
F(f"{SHOTS}/5_reportar.png", "Módulo de registro ciudadano de un foco de riesgo", 16,
  "Captura del prototipo. El reporte es anónimo y se ubica tocando el mapa.")

H("7.6 Privacidad y uso responsable", 2)
B("No hay cuentas de usuario ni se piden nombres, documentos o teléfonos. El dispositivo se identifica con un "
  "código aleatorio del que solo se guarda un hash, y únicamente para impedir votos repetidos y limitar el envío "
  "masivo de reportes.")
B("No se almacena la ubicación del usuario ni el origen y destino de sus consultas de ruta.")
B("Se pide no escribir nombres ni datos de personas en las descripciones, y no se publican fotos de personas.")
B("El sistema no publica rankings de barrios para evitar estigmatizar a sus habitantes.")
B("El tratamiento de datos se ajusta a la Ley N.º 29733, Ley de Protección de Datos Personales.")

H("7.7 Prueba de concepto preliminar", 2)
P("Antes del piloto de campo se verificó el funcionamiento del modelo con 131 reportes simulados, distribuidos "
  "en 11 concentraciones y 35 puntos dispersos sobre la red real de la zona piloto. Estos datos no representan "
  "hechos reales y solo sirven para comprobar que el algoritmo se comporta como se espera. Se evaluaron 300 pares "
  "origen-destino aleatorios a las 11:00 y a las 21:00 con prioridad 6 (λ = 9); de ellos, 282 tenían algún riesgo "
  "en la ruta más corta. Los resultados se presentan en la Tabla 6 y la Figura 7.")
T("Resultados de la prueba de concepto (282 pares con exposición)",
  ["Indicador", "Día (11:00)", "Noche (21:00)"],
  [["Reducción de la exposición (media / mediana)", "72,4 % / 89,6 %", "79,2 % / 94,4 %"],
   ["Aumento de distancia (media / mediana)", "7,5 % / 4,9 %", "10,0 % / 7,0 %"],
   ["Aumento de distancia (percentil 90)", "18,8 %", "22,8 %"],
   ["Tramos críticos atravesados (ruta corta → segura)", "1 322 → 172", "2 238 → 289"],
   ["Pares que cumplen la HE3 (≥ 30 % y ≤ 20 %)", "210 / 282 (74,5 %)", "216 / 282 (76,6 %)"],
   ["Tiempo de cálculo por consulta", "< 0,1 s", "< 0,1 s"]],
  [7.6, 4.2, 4.2],
  "Resultados obtenidos con reportes simulados; sirven para validar el funcionamiento del algoritmo, no para "
  "contrastar la hipótesis, que se hará con los datos reales del piloto.")
F(f"{SHOTS}/evaluacion.png", "Reducción de la exposición frente al aumento de distancia en cada par origen-destino", 15,
  "Cada punto es un par origen-destino. La zona sombreada corresponde al criterio de la HE3. Datos simulados.")
P("Con estos datos, en tres de cada cuatro pares la ruta segura reduce la exposición al menos en 30 % sin "
  "alargar el recorrido más de 20 %, lo que indica que la hipótesis HE3 es alcanzable. El efecto es mayor de noche, "
  "cuando el alumbrado deficiente y los incidentes nocturnos pesan más. Además, se ejecutaron 8 pruebas "
  "unitarias que verifican el decaimiento temporal, el efecto de los votos, el factor horario y que la ruta segura "
  "evita un foco que la ruta más corta atraviesa; todas fueron superadas.")

# ================================================================= REFERENCIAS
H("Referencias", 1)
refs = [
    [("Alvarado Vidal, G. M. F., Diaz Rivas, L. W., Salazar Huamaní, S. K., y Espejo Gálvez, J. C. (2024). ", ""),
     ("Modelo Prolab: “Comunidad Segura” – Aplicativo de seguridad", "i"),
     (" [Tesis de maestría, Pontificia Universidad Católica del Perú]. Repositorio PUCP. https://repositorio.pucp.edu.pe/index/handle/123456789/200102", "")],
    [("Brooke, J. (1996). SUS: A “quick and dirty” usability scale. En P. W. Jordan, B. Thomas, B. A. Weerdmeester y "
      "I. L. McClelland (Eds.), ", ""), ("Usability evaluation in industry", "i"), (" (pp. 189–194). Taylor & Francis.", "")],
    [("Chumpitaz, Ó. (27 de octubre de 2019). Los 812 puntos inseguros de San Juan de Lurigancho. ", ""), ("La República", "i"),
     (". https://larepublica.pe/sociedad/2019/10/27/los-812-puntos-inseguros-de-san-juan-de-lurigancho-delincuencia-homicidios-pnp-serenazgo", "")],
    [("Cohen, L. E., y Felson, M. (1979). Social change and crime rate trends: A routine activity approach. ", ""),
     ("American Sociological Review, 44", "i"), ("(4), 588–608.", "")],
    [("Galbrun, E., Pelechrinis, K., y Terzi, E. (2016). Urban navigation beyond shortest route: The case of safe paths. ", ""),
     ("Information Systems, 57", "i"), (", 160–171.", "")],
    [("Infobae. (13 de noviembre de 2023). Los distritos de Lima Metropolitana más peligrosos del 2023, según la PNP. ", ""),
     ("Infobae", "i"), (". https://www.infobae.com/peru/2023/11/13/los-distritos-de-lima-metropolitana-mas-peligrosos-del-2023-segun-la-pnp-robos-extorsiones-secuestros-y-mas/", "")],
    [("Instituto Nacional de Estadística e Informática. (2018). ", ""),
     ("Perú: Resultados definitivos de los Censos Nacionales 2017", "i"), (". INEI.", "")],
    [("Instituto Nacional de Estadística e Informática. (2026). ", ""), ("Victimización en el Perú 2025: Principales resultados", "i"),
     (". INEI. https://www.inei.gob.pe/media/MenuRecursivo/publicaciones_digitales/Est/Lib2076/libro.pdf", "")],
    [("Jeffery, C. R. (1971). ", ""), ("Crime prevention through environmental design", "i"), (". Sage.", "")],
    [("La República. (21 de octubre de 2025). San Juan de Lurigancho, el distrito más extorsionado de Lima, registra más "
      "de mil denuncias en 2025. ", ""), ("La República", "i"),
     (". https://larepublica.pe/sociedad/2025/10/21/san-juan-de-lurigancho-el-distrito-mas-extorsionado-de-lima-registra-mas-de-mil-denuncias-en-2025-ntpe-1969920", "")],
    [("Mata, F., Torres-Ruiz, M., Guzmán, G., Quintero, R., Zagal-Flores, R., Moreno-Ibarra, M., y Loza, E. (2016). "
      "A mobile information system based on crowd-sensed and official crime data for finding safe routes: A case study "
      "of Mexico City. ", ""), ("Mobile Information Systems, 2016", "i"), (", Artículo 8068209.", "")],
    [("Newman, O. (1972). ", ""), ("Defensible space: Crime prevention through urban design", "i"), (". Macmillan.", "")],
    [("Shah, S., Bao, F., Lu, C.-T., y Chen, I.-R. (2011). CROWDSAFE: Crowd sourcing of crime incidents and safe routing "
      "on mobile devices. En ", ""), ("Proceedings of the 19th ACM SIGSPATIAL International Conference on Advances in "
      "Geographic Information Systems", "i"), (" (pp. 521–524). ACM.", "")],
    [("Viswanath, K., y Basu, A. (2015). SafetiPin: An innovative mobile app to collect data on women’s safety in Indian "
      "cities. ", ""), ("Gender & Development, 23", "i"), ("(1), 45–60.", "")],
    [("Wilson, J. Q., y Kelling, G. L. (1982). Broken windows: The police and neighborhood safety. ", ""),
     ("The Atlantic Monthly, 249", "i"), ("(3), 29–38.", "")],
]
for partes in refs:
    p = rico(partes, alin="left")
    p.paragraph_format.left_indent = Cm(1.27)
    p.paragraph_format.first_line_indent = Cm(-1.27)

# ================================================================= ANEXO
sec2 = doc.add_section(WD_SECTION.NEW_PAGE)
sec2.orientation = 1
sec2.page_width, sec2.page_height = Cm(29.7), Cm(21.0)
H("Anexo: Matriz de consistencia", 1)
T("Matriz de consistencia",
  ["Problemas", "Objetivos", "Hipótesis", "Variables / indicadores"],
  [["PG: ¿En qué medida un sistema georreferenciado de registro ciudadano y rutas seguras reduce la exposición al riesgo en los desplazamientos peatonales de la zona piloto de SJL, 2026?",
    "OG: Desarrollar e implementar el sistema para reducir la exposición al riesgo en los desplazamientos peatonales de la zona piloto.",
    "HG: El sistema reduce significativamente la exposición al riesgo en los desplazamientos peatonales.",
    "VI: Sistema Focos de Alerta. VD1: Exposición al riesgo. VD2: Percepción de seguridad."],
   ["PE1: ¿Cómo el registro ciudadano y la validación comunitaria identifican y actualizan los focos?",
    "OE1: Implementar el registro ciudadano anónimo con validación comunitaria.",
    "HE1: ≥ 150 focos registrados y ≥ 70 % confirmados en campo.",
    "N.º de reportes; % confirmados."],
   ["PE2: ¿Cómo estimar un índice de riesgo por tramo?",
    "OE2: Desarrollar el modelo de riesgo espacio-temporal.",
    "HE2: El índice es mayor en tramos verificados como peligrosos (U de Mann-Whitney).",
    "Índice r(e) por tramo."],
   ["PE3: ¿Cuánto reduce la exposición la ruta segura y cuánta distancia agrega?",
    "OE3: Implementar y evaluar el trazado de rutas seguras.",
    "HE3: En ≥ 70 % de pares, ≥ 30 % menos exposición con ≤ 20 % más distancia.",
    "Exposición E; aumento de distancia; tramos críticos."],
   ["PE4: ¿Cuál es el efecto en la percepción de seguridad y la usabilidad?",
    "OE4: Evaluar la percepción de seguridad y la usabilidad.",
    "HE4: Aumento significativo de la percepción (t pareada) y SUS ≥ 68.",
    "Puntaje Likert pre/post; puntaje SUS."]],
  [6.0, 5.6, 6.0, 5.6])

# Numeracion de pagina en el pie
for s in doc.sections:
    s.footer.is_linked_to_previous = True
pf = doc.sections[0].footer.paragraphs[0]
pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
campo_r = pf
r = pf.add_run()
for tipo, txt in (("begin", None), ("instr", "PAGE"), ("separate", None), ("t", "1"), ("end", None)):
    if tipo == "instr":
        e = OxmlElement("w:instrText"); e.set(qn("xml:space"), "preserve"); e.text = txt
    elif tipo == "t":
        e = OxmlElement("w:t"); e.text = txt
    else:
        e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), tipo)
    r._r.append(e)
doc.sections[0].different_first_page_header_footer = True

# Que Word actualice el indice al abrir
upd = OxmlElement("w:updateFields"); upd.set(qn("w:val"), "true")
doc.settings.element.append(upd)

doc.core_properties.title = "Focos de Alerta - Examen Parcial"
doc.core_properties.author = "Grupo de trabajo - UNMSM FISI"
doc.save(SALIDA)
print("Guardado", SALIDA)
