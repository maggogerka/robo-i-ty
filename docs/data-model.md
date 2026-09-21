# Модель данных

```mermaid
erDiagram
  USER ||--o{ PROJECT : owns
  OBJECT_TYPE ||--o{ PARAMETER_DEFINITION : defines
  PROJECT ||--o{ PROJECT_PARAMETER_VALUE : contains
  ROBOT_SOLUTION ||--o{ DEPLOYMENT_CASE : evidenced_by
  PROJECT ||--o{ MATCHING_RUN : calculates
  MATCHING_RUN ||--o{ MATCHING_CANDIDATE : ranks
  ROBOT_SOLUTION ||--o{ MATCHING_CANDIDATE : references
  PROJECT ||--o{ ECONOMIC_SCENARIO : compares
  ECONOMIC_SCENARIO ||--o{ ECONOMIC_ASSUMPTION : records
  ECONOMIC_SCENARIO ||--o{ ECONOMIC_RESULT : produces
  PROJECT ||--o| PLAN : has
  PLAN ||--o{ PLAN_ELEMENT : contains
  PROJECT ||--o{ SIMULATION_RUN : simulates
  SIMULATION_RUN ||--o{ SIMULATION_METRIC : measures
```

`RobotSolution` — технический продукт. `DeploymentCase` — контекст внедрения. `SourceEvidence` — источник и статус доказательства. Разделение предотвращает перенос результата одного внедрения в ТТХ продукта без основания.

Пользовательское изменение параметра сохраняет исходное и текущее значение, автора, время и статус `assumed`.

`Plan` имеет номер ревизии, размеры в метрах и статус источника. `PlanElement` хранит тип, геометрию и внешний ключ в пределах плана; комбинация проекта и ключа уникальна. Схема P0 поддерживает storage, obstacle, pickup, dropoff и charger.

`SimulationRun` неизменно сохраняет ревизию плана, версию модели, полный снимок входа и результата. `SimulationMetric` хранит значение, единицу и статус. Поэтому отчёт может отличить актуальную симуляцию от запуска старой ревизии.

Будущий распознаватель сначала создаёт отдельный `DraftPlan` с provenance/confidence; эта сущность не добавлена в БД до реализации безопасной загрузки и ручного подтверждения.