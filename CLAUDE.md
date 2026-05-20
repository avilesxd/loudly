# Loudly — instrucciones para la IA

## Commits

Este proyecto usa **Conventional Commits**. Cada commit que hagas debe seguir este formato:

```
<tipo>: <descripción en imperativo, minúsculas>
```

### Tipos y su efecto en el versionado automático

| Tipo | Cuándo usarlo | Bump de versión |
|---|---|---|
| `feat:` | Nueva funcionalidad visible para el usuario | MINOR → `1.1.0` |
| `fix:` | Corrección de un bug | PATCH → `1.0.1` |
| `perf:` | Mejora de rendimiento sin cambio de API | PATCH → `1.0.1` |
| `refactor:` | Reestructuración interna sin cambio de comportamiento | ninguno |
| `test:` | Agregar o corregir tests | ninguno |
| `docs:` | Solo documentación | ninguno |
| `chore:` | Tareas de mantenimiento (deps, config, scripts) | ninguno |
| `ci:` | Cambios en workflows de GitHub Actions | ninguno |
| `build:` | Cambios en el sistema de build (PyInstaller, etc.) | ninguno |

Para un **cambio que rompe compatibilidad** (MAJOR), agrega `!` después del tipo:

```
feat!: cambiar formato de archivos de sesión
```

O incluye `BREAKING CHANGE:` en el cuerpo del commit.

### Reglas de estilo

- Descripción en **inglés**, pero consistente dentro del commit.
- Sin punto final.
- Sin mayúscula al inicio de la descripción.
- Máximo ~72 caracteres en la primera línea.
- Si el cambio abarca múltiples archivos con propósitos distintos, **separa en varios commits**.

### Ejemplos correctos

```
feat: add export to MP3 from batch window
fix: prevent crash when reference track is missing
refactor: extract audio analysis into separate module
test: add unit tests for loudness normalization
chore: update dependencies to latest patch versions
docs: add setup instructions for Windows
```

### Ejemplos incorrectos

```
fixes things                   ← sin tipo
feat: Added new button.        ← mayúscula + punto final
update stuff                   ← no describe qué ni por qué
feat: new feature and fix bug  ← mezcla dos tipos en uno
```

## Versionado automático

Al hacer push a `main`, el workflow `auto-version.yml` analiza los commits desde el último tag y publica un release si corresponde. No es necesario correr ningún script manualmente.

Si necesitas forzar una versión específica: `python scripts/bump_version.py <version>` (ej: `2.0.0`).
