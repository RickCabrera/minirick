# Fase 5.1 — Ajustes a Regla 0 antes del "adelante"

Tres correcciones a tu respuesta de Regla 0. Aplícalas y repórtame antes de codear.

---

## 1. Renombrar `PermissionError` propia

Tu propuesta sombrea la builtin `PermissionError` dentro de `admin.py`. Eso rompe cualquier `except PermissionError` que se use para otra cosa (ej. errores de filesystem).

**Cambio**:
- Renombra la excepción a `AdminPermissionError`.
- Que herede de `AdminError`, NO de la builtin.
- Así un solo `except AdminError` en el CLI atrapa ambas.
- No sombrees la builtin `PermissionError` en ningún módulo del proyecto.

Firma final:

```python
class AdminError(Exception):
    """Error genérico de operaciones admin."""


class AdminPermissionError(AdminError):
    """El usuario actual no tiene permisos para esta operación admin."""
```

---

## 2. Semántica del flag `--assignees` en `set-active`

Tu firma actual (`assignees: str | None`) es ambigua: no queda claro qué hace `--assignees ""` vs no pasar el flag. Defínelo así y documéntalo en la docstring y en el `help` de Typer:

| Invocación | Comportamiento |
|---|---|
| `minirick set-active <id>` | Solo activa. NO toca `assignees`. |
| `minirick set-active <id> --assignees ""` | Activa + asigna `[]` (tarea pública explícita). |
| `minirick set-active <id> --assignees a@b.co,c@d.co` | Activa + reemplaza `assignees` con los uuids resueltos. |

Implementación:
- `assignees is None` → no tocar el campo en el UPDATE.
- `assignees == ""` → `[]` en el UPDATE.
- `assignees = "a@b.co,c@d.co"` → split por coma + `resolve_assignees()` + UPDATE.

Docstring del comando (texto exacto que pones):

```
Marca una tarea como activa del equipo. Con --assignees reemplaza los
colaboradores asignados; sin el flag solo activa sin tocar assignees.
Usa --assignees "" (vacío) para marcar la tarea como pública.
```

`help=` del `typer.Option`:

```
Emails separados por coma. Vacío ("") = pública. Omitir = no toca.
```

---

## 3. Cache local debe sobrevivir al nuevo campo

El comando `sync` escribe las tareas en `cache/tasks.json`. Con el nuevo campo `assignees` necesito que confirmes:

- `Task.to_dict()` incluye `"assignees": self.assignees`.
- `Task.from_dict()` lee `data.get("assignees") or []`.
- Los tests existentes de serialización (`tests/test_models.py`, y cualquier otro que toque `Task` en cache) siguen verdes **sin modificarlos**.
- Si algún test existente se rompe por el nuevo campo, **no cambies el test**: ajusta los fixtures o el código para que el campo sea opcional-retrocompatible (default `[]`).

---

## Reporte esperado (solo esto, nada más)

Respóndeme con:

1. ✅/❌ para cada uno de los 3 puntos aplicados en tu plan (una línea c/u).
2. Firma final de `AdminError` y `AdminPermissionError` (copia/pega las dos clases tal como las vas a escribir).
3. Docstring final del comando `set-active` y el `help=` del flag (texto exacto).
4. Confirmación de que los tests existentes de `Task` seguirán verdes sin modificarlos.

**NO empieces a codear.** Espera mi "adelante" explícito después de este reporte.
