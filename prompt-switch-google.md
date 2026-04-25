# Prompt Para Google Stitch (Diseño Frontend de FinanzApp)

Quiero que actúes como **Product Designer/UI Designer** usando **Google Stitch** para diseñar el frontend de FinanzApp.  
Google Stitch en este contexto se usa como herramienta de **diseño front-end** (UX/UI), no como análisis de backend.

Objetivo:
Diseñar una experiencia moderna, clara y mobile-first para una app de finanzas personales con estas capacidades:
- Usuarios (perfil, moneda, zona horaria)
- Cuentas financieras (bank, cash, credit_card, digital_wallet, investment, savings)
- Categorías (ingresos/gastos, jerarquía, icono/color)
- Transacciones (income, expense, transfer, adjustment, debt_payment)
- Recurrencias
- Presupuestos
- Metas de ahorro
- Tags
- Adjuntos
- Journal entries (doble partida)
- Conciliación bancaria
- Módulos futuros: deudas, facturas recurrentes, inversiones

Contexto técnico para handoff:
- Backend: FastAPI
- API base: `/api/v1`
- El diseño debe ser implementable en una SPA web responsiva.

Quiero que entregues:
1. Mapa de pantallas clave (IA de producto): onboarding, dashboard, cuentas, transacciones, presupuestos, metas, reportes, configuración.
2. User flows prioritarios: crear cuenta, registrar gasto, transferir entre cuentas, crear presupuesto, registrar aporte a meta.
3. Sistema de diseño base: tipografía, paleta, spacing, tokens y estados (default/hover/disabled/error/success).
4. Librería de componentes UI: app shell, cards KPI, tablas/listas, formularios, filtros, date pickers, modales, toasts, empty states.
5. Propuesta de layout responsive (mobile, tablet, desktop) con jerarquía visual consistente.
6. Principios UX para finanzas: claridad de saldo, feedback inmediato, prevención de errores, accesibilidad WCAG AA.
7. Copys sugeridos para CTAs y mensajes críticos (errores de validación, estados vacíos, confirmaciones).
8. Plan de handoff a desarrollo front: naming de componentes, estados, variantes y especificaciones listas para implementación.

Criterios de calidad:
- Priorización de usabilidad y legibilidad de datos financieros.
- Diseño consistente para CRUDs complejos.
- Navegación simple para usuarios no técnicos.
- Estilo visual profesional, limpio y orientado a confianza.
