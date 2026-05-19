# Guía de contribución

¡Gracias por tu interés en contribuir a **Loudly**! Toda ayuda es bienvenida,
ya sea corrigiendo bugs, mejorando el código o proponiendo nuevas funcionalidades.

---

## Política de ramas

Todo el trabajo de desarrollo debe hacerse en ramas de feature.
**Los commits directos a `main` no están permitidos.**

Todos los cambios deben enviarse mediante Pull Request y pasar los checks
automáticos antes de ser mergeados.

---

## Cómo contribuir

### 1. Fork del repositorio

Hacé clic en el botón "Fork" en la esquina superior derecha.

### 2. Cloná tu fork

```bash
git clone https://github.com/tu-usuario/loudly.git
cd loudly
```

### 3. Creá tu entorno virtual

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 4. Creá una rama de feature

**Convenciones de nombre:**

- `feature/descripcion` — nuevas funcionalidades
- `fix/descripcion-del-bug` — correcciones
- `docs/que-cambio` — documentación
- `refactor/que-se-refactorizo` — refactoring
- `test/que-se-testea` — tests

```bash
git checkout main
git pull origin main
git checkout -b feature/tu-funcionalidad
```

### 5. Hacé tus cambios y verificá la calidad

```bash
# Linter y formato
ruff check .
ruff format .

# Tests
pytest tests/
```

### 6. Commiteá siguiendo Conventional Commits

```bash
git commit -m "feat: agregar soporte para exportar en MP3"
git commit -m "fix: corregir crash al cargar archivos con espacios en el nombre"
```

Los tipos válidos son: `feat`, `fix`, `docs`, `style`, `refactor`, `test`,
`chore`, `perf`, `ci`, `build`.

### 7. Abrí un Pull Request

Usá el template de PR provisto, describiá qué cambiaste y por qué, y asegurate
de que todos los checks de CI pasen.

---

## Tests

- Los tests viven en `tests/`
- Nombralos como `test_*.py`
- Correrlos con `pytest tests/`
- Apuntá a mantener la cobertura existente al agregar nueva funcionalidad

---

## Preguntas

Abrí un
[issue](https://github.com/avilesxd/loudly/issues/new?template=feature_request.md)
o iniciá una
[discusión](https://github.com/avilesxd/loudly/discussions).

---

¡Gracias por ayudar a mejorar Loudly! 🎧
