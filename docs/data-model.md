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
```

`RobotSolution` — технический продукт. `DeploymentCase` — контекст внедрения. `SourceEvidence` — источник и статус доказательства. Разделение предотвращает перенос результата одного внедрения в ТТХ продукта без основания.

Пользовательское изменение параметра сохраняет исходное и текущее значение, автора, время и статус `assumed`.

