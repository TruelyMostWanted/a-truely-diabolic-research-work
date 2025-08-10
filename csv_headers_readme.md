# SCRUM Optimization Data – CSV Structure

This document describes the data format for the input files of an optimization model in a SCRUM-based software company.  
Five different CSV files are used: **Entities**, **Relations**, **Goals**, **Conditions**, and **Decision Variables**.

---

## 1. Entities

**File name:** `entities.csv`

| Column          | Type    | Description |
|-----------------|---------|-------------|
| `ID`            | String  | Unique identifier of the entity (within this file) |
| `Name`          | String  | Readable name of the entity |
| `Description`   | String  | Description or additional information |
| `Attribute0`–`Attribute8` | String/Numeric | Up to 9 additional properties of the entity, meaning is project-specific |

**Note:**  
- `Name` is used for references in other files (not `ID`).  
- The attributes are generically named to keep a simple CSV structure.  

---

## 2. Relations

**File name:** `relations.csv`

| Column           | Type    | Description |
|------------------|---------|-------------|
| `ID`             | String  | Unique identifier of the relation |
| `Name`           | String  | Readable name of the relation |
| `Description`    | String  | Description or additional information |
| `FromEntity`     | String  | Name of the source entity (must exist in `entities.csv`) |
| `ToEntity`       | String  | Name of the target entity (must exist in `entities.csv`) |
| `FromCardinality`| String  | Cardinality of the relation from the source side (e.g., `1`, `n`) |
| `ToCardinality`  | String  | Cardinality of the relation from the target side |
| `Weight`         | Numeric | Optional weight or strength of the relation |

---

## 3. Goals

**File name:** `goals.csv`

| Column           | Type    | Description |
|------------------|---------|-------------|
| `ID`             | String  | Unique identifier of the goal |
| `Name`           | String  | Readable name of the goal |
| `Description`    | String  | Description or additional information |
| `IsSum`          | Boolean | `true` = aggregation over multiple values, `false` = single value |
| `GoalType`       | String  | Goal type: `Max` or `Min` |
| `EntityName`     | String  | Name of the entity the goal refers to |
| `EntityAttribute`| String  | Attribute of the entity being optimized |
| `CriteriaType`   | String  | Type of Criteria (`2`(Must-Match), `1`(May-Match), `0`(Cannot-Match)) |
| `Weight`         | Numeric | Weight of the goal in multi-objective optimization |

---

## 4. Conditions (Constraints)

**File name:** `conditions.csv`

| Column           | Type    | Description |
|------------------|---------|-------------|
| `ID`             | String  | Unique identifier of the condition |
| `Name`           | String  | Readable name of the condition |
| `Description`    | String  | Description or additional information |
| `IsSum`          | Boolean | `true` = aggregation over multiple values, `false` = single value |
| `GoalType`       | String  | `Max`, `Min` or other comparison types (depending on the model) |
| `EntityName`     | String  | Name of the entity the condition refers to |
| `EntityAttribute`| String  | Attribute of the entity being checked |
| `CriteriaType`   | String  | Type of Criteria (`2`(Must-Match), `1`(May-Match), `0`(Cannot-Match)) |
| `Weight`         | Numeric | Weight: empty or ∞ for HardConstraint, positive value for SoftConstraint |

**Note:**  
- **HardConstraint**: leave `Weight` empty or use a very high value (∞).  
- **SoftConstraint**: `Weight` > 0, value is treated as penalty cost in the objective function.

---

## 5. Decision Variables

**File name:** `decision_variables.csv`

| Column        | Type    | Description |
|---------------|---------|-------------|
| `ID`          | String  | Unique identifier of the decision variable |
| `Name`        | String  | Readable name of the decision variable |
| `Description` | String  | Description or additional information |
| `DataType`    | String  | `Binary`, `Integer`, or `Real` |
| `Domain`      | String  | Value domain (e.g., `{0,1}` or `{A,B,C}`) |
| `MinValue`    | Numeric | Lower bound (if applicable) |
| `MaxValue`    | Numeric | Upper bound (if applicable) |

---

## General Notes

- **References** between files use the `Name` of an entity or relation, not the `ID`.  
- CSV files should be UTF-8 encoded.  
- Numeric fields should use `.` as the decimal separator.  
- Empty values in optional fields can be left blank.  
- Comments are not allowed in CSV files. Keep notes in separate documentation.

---
