# pool-keeper

*[Read in English](README.md)*

Una skill para agentes (Claude Code y Codex) que construye y mantiene una **base de
conocimiento sobre una persona**: cada documento archivado, cada dato extraído con su fuente,
sin duplicados y sin borrar nunca nada. Cualquier agente puede leer la base y saber casi todo lo
relevante sobre la persona — para escribir un CV, preparar una entrevista o simplemente
responder "¿qué hice el mes pasado?". Nunca inventa un dato.

```
tú:     [adjuntas un CV viejo, un certificado y un contrato]  añade a mi base
agente: ✅ Archivado: S014 (CV), S015 (certificado), S016 (contrato)
        📊 Resultado: 23 puntos nuevos · 6 enriquecidos · 1 conflicto nuevo
        ⚠ Para revisar: el contrato dice que empezaste en marzo de 2024 y tu CV dice febrero. ¿Cuál es?

tú:     hoy entrevisté a 3 candidatos y arreglé el cuadrante de turnos
agente: 📓 J0107–J0108 registradas (#entrevista ×3, #turnos).

tú:     analiza mis cambios de GitHub de esta semana
agente: GitHub: 4 unidades de trabajo en acme/api y acme/web (2 PR fusionadas, PAY-12, PAY-15);
        7 commits de ruido omitidos. Nueva evidencia de habilidad: Redis. Detalle en CHANGELOG.md.
```

## Qué hace

- **Archiva cada fuente** (CV, certificado, contrato, SOP, horario, captura, ZIP, respuestas en
  el chat) con control de duplicados por SHA-256, y **extrae todos los datos** a archivos por
  tema: perfil, experiencia (un archivo por puesto), educación, habilidades con evidencia,
  certificaciones e idiomas, banco de logros, narrativa y posicionamiento, banco de historias
  STAR, palabras clave.
- **Integra sin duplicar y sin borrar**: mismo dato → una etiqueta de fuente más; más detalle →
  el punto se enriquece en su sitio; contradicción → se guardan ambos valores y se marca. Las
  frases originales se conservan siempre literalmente.
- **Lleva la cuenta de lo que no se sabe**: huecos, conflictos entre fuentes, cosas por las que
  se preguntó y que la persona nunca ha hecho. Pregunta como mucho una cosa por informe, nunca
  una lista.
- **Diario de actividad**: cuéntale lo que hiciste, cualquier día, en cualquier idioma; luego
  pregunta "¿cuántas veces hice…?" y obtén un conteo exacto y con fuentes.
- **Historial de GitHub**: tus commits y PR (varias cuentas e identidades), sin ruido, agrupados
  en unidades de trabajo con claves de Jira, registrados una sola vez — una segunda pasada nunca
  duplica.
- **Aprende cómo escribes** (patrones de tus propios documentos) y **aprende de tus
  correcciones** (pega el texto de la IA y la versión que querías).
- **Dominios opcionales**: preferencias y valores, metas, disponibilidad, vida personal.
- **Trabaja con otras skills**: cv-tailor (y cualquier skill que siga el mismo contrato) puede
  guardar en tu base lo que le confirmas, a través de pool-keeper.
- **Habla tu idioma**: la conversación, los nombres de archivo y los títulos de la base pueden
  estar en idiomas distintos (inglés, español e indonesio incluidos; cualquier otro traduciendo).

## Instalación

Requisitos: Python 3.9+ (solo la biblioteca estándar — nada que instalar). Opcional: `gh`
(GitHub), `git` (bases que hacen commit tras cada cambio).

**Claude Code, como plugin**

```
/plugin marketplace add cris-dangithub/pool-keeper
/plugin install pool-keeper@pool-keeper
```

**Codex y/o Claude Code, desde un clon**

```bash
git clone https://github.com/cris-dangithub/pool-keeper
cd pool-keeper
./install.sh            # Windows: .\install.ps1
```

Enlaza `skills/pool-keeper` en `~/.codex/skills` y `~/.claude/skills` y ejecuta `pk doctor`.
También puedes copiar `skills/pool-keeper` en `.claude/skills/` de un proyecto.

## Primer uso

Di "configura pool-keeper" (o simplemente adjunta tu CV). La configuración pregunta, de una en
una:

1. el idioma en que te habla (se pregunta en inglés);
2. de quién es la base;
3. dónde guardarla (una carpeta nueva);
4. el idioma de los archivos de la base;
5. dominios opcionales (preferencias, metas, disponibilidad, vida personal) y, si quieres, tus
   cuentas de GitHub y las identidades con que haces commit;
6. tu país (para consultar fuentes oficiales);
7. cuántas preguntas quieres (por defecto: como mucho una por informe).

Después escribe la base y ofrece la primera ingesta. A partir de ahí: adjunta archivos, cuenta
cosas, dicta tu día o pregunta "¿qué falta?".

## Tus datos

- **La base es una carpeta normal de archivos Markdown que es tuya**, donde tú elijas. Nada se
  guarda en este repositorio ni se envía a ningún sitio. Varias personas = varias bases; un
  pequeño registro (`~/.pool-keeper/pools.json`) recuerda dónde están.
- Los datos sensibles (números de identificación, datos bancarios, contraseñas, nombres de
  otras personas en tus documentos de trabajo) nunca se copian a la base; quedan solo en tus
  archivos originales.
- Lo marcado `🔒 privado` (p. ej. repositorios privados) es solo para tus propios agentes y
  nunca se pone en textos para terceros.
- El acceso a GitHub es de solo lectura y usa las cuentas ya conectadas en `gh`.

```
mi-base/
  .pool-keeper/config.json        # idiomas, estructura, dominios, fuentes de GitHub
  CLAUDE.md, AGENTS.md            # cómo debe leer y actualizar la base cualquier agente
  README.md  CHANGELOG.md
  00_resumen_rapido.md  01_perfil.md
  10_experiencia/2024_acme.md
  20_educacion.md  30_habilidades.md  40_certificaciones_idiomas.md  50_logros.md
  55_diario/2026-10.md  55_diario/README.md
  60_narrativa_posicionamiento.md  62_historias.md  65_estilo_escritura/  70_otros.md
  75_… 78_… (dominios opcionales)  80_palabras_clave.md  90_preguntas_abiertas.md
  fuentes/INDICE.md  fuentes/2026-10-09_cv/{archivo original, extracted.txt}
```

## Estructura del repositorio

```
.claude-plugin/            manifiestos del plugin y del marketplace
skills/pool-keeper/        la skill (es lo que cargan los agentes)
  SKILL.md                 punto de entrada y reglas que nunca se rompen
  references/              guías paso a paso que se cargan cuando hacen falta
  scripts/                 pool, ids, extract, journal, github, lint, status, doctor
  templates/layout/        nombres de archivo por idioma (en, es, id)
  templates/strings/       títulos y marcas por idioma
  templates/pool/          plantillas de los archivos de la base
  templates/instructions/  el bloque de CLAUDE.md / AGENTS.md y el puntero del gestor
  pk.py                    lanzador: `python pk.py <comando>`
examples/sample-pool/      una base ficticia pequeña (diario, fuente de GitHub, conflicto, "nunca hecho")
tests/                     pruebas con pytest (sin red; GitHub mediante un fixture JSON)
```

## Desarrollo

```bash
python -m pip install pytest
python -m pytest tests -q
python skills/pool-keeper/pk.py doctor
python skills/pool-keeper/pk.py lint --pool examples/sample-pool
```

## Licencia

MIT.
