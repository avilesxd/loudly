# Security Policy

## Versiones soportadas

| Versión | Soportada          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reportar una vulnerabilidad

Si encontrás una vulnerabilidad de seguridad, seguí estos pasos:

### 1. No lo divulgues públicamente

Por favor, no abras un issue público para vulnerabilidades de seguridad.

### 2. Reportá por email

Enviá los detalles a: **nacho72001@gmail.com**

Incluí:

- Descripción de la vulnerabilidad
- Pasos para reproducirla
- Impacto potencial
- Posibles soluciones (opcional)

### 3. Tiempos de respuesta

- **Respuesta inicial**: dentro de 48 horas
- **Actualización de estado**: dentro de 7 días
- **Corrección**: varía según la severidad (los casos críticos tienen prioridad)

## Medidas de seguridad

### Auditorías automáticas

- **Dependabot**: PRs automáticos de actualización de dependencias
- **GitHub Security Advisories**: alertas automáticas por vulnerabilidades conocidas

### Dependencias

Solo se incluyen dependencias esenciales en `requirements.txt`. Las de
desarrollo y build están separadas.

### Política de actualizaciones

- **Parches de seguridad**: aplicados de inmediato
- **Actualizaciones menores**: revisadas y aplicadas semanalmente
- **Actualizaciones mayores**: testeadas antes de adoptar

## Limitaciones conocidas

1. **Procesamiento local**: Loudly procesa todo el audio localmente, sin enviar
   datos a servidores externos.
2. **Sin autenticación**: aplicación standalone de usuario único, sin cuentas.
3. **Sin red**: opera completamente offline.

## Reconocimientos

Agradecemos a los investigadores de seguridad que reporten vulnerabilidades de
forma responsable:

- *(Nadie aún — ¡sé el primero!)*
