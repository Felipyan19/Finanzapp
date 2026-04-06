# Plan Maestro MVP: Diagnóstico Mensual de Finanzas Personales

## 1. Resumen Ejecutivo

Objetivo del MVP (60 días): responder al cierre de cada mes, con evidencia, por qué bajó la liquidez, dónde se concentró el gasto y qué acciones concretas tomar para mejorar el ahorro neto.

Decisiones de producto ya fijadas:
- Objetivo principal: diagnóstico mensual.
- Métrica de éxito: ahorro + claridad (top 3 causas del gasto).
- Carga de datos: solo manual.
- Cobertura: total personal (todas las cuentas, tarjetas y billeteras).
- Moneda: moneda base + tasa de conversión.
- Salida inicial: API + dashboard simple.
- Calidad de dato por transacción: clasificación completa.
- Conciliación: semanal.
- Alertas: umbral por categoría (80% y 100%).

Diagnóstico del estado actual de la app:
- Base sólida para registro: cuentas, categorías, transacciones, presupuestos, metas y deudas.
- Brecha principal: falta capa de diagnóstico financiero causal y accionable (drivers, desvíos, riesgo de liquidez, costo financiero).
- Gap técnico detectado: inconsistencia de import de routers (`app.main` referencia `app.api.v1`, mientras el código visible está en `app/api/endpoints`).

## 2. Implementación por Bloques

### Bloque A: Datos, normalización y calidad

1. Extender modelo de transacciones para exigir dimensiones analíticas:
- `category_id`
- `subcategory_id` (o jerarquía equivalente)
- `payment_method` (tarjeta, débito, efectivo, wallet, transferencia)
- `merchant`
- `purpose_tag` (etiqueta objetivo)

2. Multi-moneda consistente:
- Mantener moneda original en cada transacción.
- Persistir `fx_rate` aplicado y `base_amount` (monto convertido a moneda base del usuario).
- Crear tabla de tasas FX diarias por par de moneda.

3. Conciliación semanal:
- Crear entidad de conciliación por cuenta/tarjeta/wallet con:
  - `expected_balance`
  - `actual_balance`
  - `difference`
  - `reconciled_at`
  - `status`
- Reglas de calidad:
  - No marcar cierre mensual como confiable si hay diferencias críticas sin resolver.

### Bloque B: Motor de diagnóstico mensual

1. Construir servicio de cierre mensual que calcule:
- Ingreso total, gasto total y flujo neto.
- Tasa de ahorro neto.
- Top 3 drivers de gasto por:
  - categoría/subcategoría
  - comercio
  - medio de pago
- Variación vs mes anterior y promedio móvil de 3 meses.
- Distribución gasto fijo vs variable.
- Costo financiero mensual (intereses de deuda) y peso sobre ingreso.

2. Reglas de negocio críticas:
- Excluir transferencias internas del gasto real.
- Separar pagos de deuda en principal (pasivo) vs interés (gasto financiero).
- Señalar automáticamente transacciones sin clasificar como riesgo de calidad.

3. Insights accionables determinísticos:
- Generar recomendaciones tipo:
  - causa detectada
  - impacto monetario
  - acción sugerida
  - prioridad (alta/media/baja)

### Bloque C: Presupuestos y control preventivo

1. Presupuestos por categoría/subcategoría con seguimiento diario.
2. Alertas por umbral:
- 80%: advertencia temprana.
- 100%: sobrepaso.
3. Alertas de desvío de flujo:
- Comparar gasto acumulado real vs gasto esperado a la fecha del mes.

### Bloque D: Dashboard simple (MVP)

1. Vista ejecutiva mensual:
- Qué pasó (resultado financiero).
- Por qué pasó (drivers).
- Qué hacer (acciones recomendadas).

2. Drill-down:
- categoría -> subcategoría -> comercio -> transacciones.

3. Panel de salud financiera:
- ahorro neto
- deuda activa total
- costo financiero mensual
- patrimonio neto básico

## 3. APIs e Interfaces

Nuevos endpoints (o equivalentes):
- `POST /api/v1/monthly-close/{user_id}?year=YYYY&month=MM`
  - Ejecuta cierre mensual y persiste snapshot de diagnóstico.
- `GET /api/v1/monthly-close/{user_id}?year=YYYY&month=MM`
  - Devuelve resumen ejecutivo, drivers y recomendaciones.
- `GET /api/v1/insights/{user_id}?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
  - Devuelve insights de causas de gasto y desvíos.
- `POST /api/v1/reconciliation`
  - Registra conciliación semanal por fuente.
- `GET /api/v1/reconciliation/status?user_id=...`
  - Estado de conciliación y gaps.

Ajustes a endpoints actuales:
- `transactions`: soportar campos de clasificación completa + `fx_rate` + `base_amount`.
- `budgets/progress`: incluir umbrales y riesgo de cierre por proyección.

## 4. Pruebas y Criterios de Aceptación

Casos de prueba funcionales:
1. Cierre mensual con múltiples cuentas/tarjetas/wallets y monedas distintas.
2. Transferencias internas no afectan gasto real ni ahorro neto.
3. Pago de deuda separa interés de principal en reportes.
4. Alertas se disparan correctamente en 80% y 100% del presupuesto.
5. Conciliación semanal detecta diferencias y clasifica el cierre como no confiable cuando aplica.
6. Top 3 causas del gasto se calculan con montos y porcentajes correctos.

Criterios de aceptación del MVP:
- Al cierre mensual hay respuesta clara y automática a "dónde se fue el dinero".
- Se reporta tasa de ahorro neto y variación contra el mes anterior.
- El dashboard permite ir de resumen a detalle en pocos pasos.
- Los datos tienen trazabilidad mínima para auditar cálculos (fuente, moneda, FX, clasificación).

## 5. Supuestos y Defaults

- Producto personal (single-user), sin multi-tenant empresarial en MVP.
- Ingesta inicial totalmente manual; integraciones automáticas en fase posterior.
- Moneda base única por usuario para consolidación.
- Conciliación semanal obligatoria para calidad analítica.
- Priorización: diagnóstico mensual accionable sobre forecasting avanzado.
