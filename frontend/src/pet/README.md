# SCHOLARIS pet companion

The pet state machine is pure and supports `farewell`, `greeting`, `notify`, `worried`, `happy`, and `idle`.

Add an idle activity to `petIdleActivities.ts`. To add a reactive trigger, extend `PetDashboardData` and the precedence rules in `getPetState` without adding API calls or persistence.
