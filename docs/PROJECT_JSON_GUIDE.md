# Project JSON Guide

Project files use suffix:

```text
.casebuilder.json
```

Current schema version:

```json
{
  "schema_version": 2
}
```

## Top-Level Structure

Typical top-level keys:

- `schema_version`
- `name`
- `settings`
- `mm_blocks`
- `base_case`
- `case_parts`
- `conditional_rules`
- `exclusions`
- `selected_case_lists`

Exact serialized shape is defined in `src/case_builder_app/models.py`.

Persisted objects use generated IDs for internal references. Case-part and case-value IDs are used by name ordering, branch selection, and rule clauses; change-row IDs support inherited-row editing. Do not duplicate or manually replace IDs unless the related references are updated as well.

## Settings

`settings` stores project-level options:

- `simple_export_enabled`;
- `case_name_order`;
- `input_data` settings.

Project name, MM block data, exclusions, conditional rules, and saved selected-case lists are top-level project fields, not settings fields.

## Base Case

`base_case` stores starting values. Case values apply sparse changes on top of this.

## Case Parts

Each case part has:

- `label`
- `values`

Each case value has:

- `token`
- `changes`

Case part order controls logic order.

Case-name order is stored separately and only controls exported case name tokens.

## Changes

Each value stores sparse changes only. Missing fields mean inherit current resolved state.

Current change areas include:

- CB state;
- fault level;
- constants;
- layer states;
- residual flux.

## CB State Semantics

CB state has lanes:

- `off`
- `switch`
- `on`

Schema v2 preserves explicit local CB overrides even if the lane equals Base Case state. This matters because same-as-base placement can be a real user choice.

Older project files without `schema_version` are treated as legacy. Legacy same-as-base hidden CB writes may be pruned when loaded because older UI could store values the user could not see.

## Branch Inheritance

Generator applies changes in order:

```text
Base Case -> case part 1 value -> case part 2 value -> ... -> generated case
```

For later case parts, previous values create branch-specific inherited states.

Example:

```text
A3 changes CB_66_StA to ON.
C23 does not mention CB_66_StA.
C23 under A3 inherits CB_66_StA = ON.
```

## Exclusions

Exclusions remove generated case combinations. Each exclusion row is a set of tokens that must all be present for the generated case to be excluded.

## Conditional Rules

Conditional rules are stored at the project top level and are applied by the generator when present. The current UI does not create or edit them; preserve them when loading and saving existing project files.

`match_mode` must be `ALL` or `ANY`. Each complete clause must reference an existing case-part ID and value ID. The Check workflow validates these references before generation.

## Input_Data

`settings.input_data` stores values written to the exported `Input_Data` sheet.

Study list may include:

- `frequency_sweep`
- `switching`
- `fault`

When switching and fault are both selected, export forces `Switch type = Sequential`.

`Residual Flux` is written as `Yes` only when:

- selected studies include `switching`;
- `settings.input_data.residual_flux` is `Yes`.

Sequential timing formulas are written into the exported workbook, with cached numeric values added after save for external pandas/openpyxl readers.

## MM Blocks

MM block settings are project-level.

MM names are parsed by voltage token from names like:

```text
MM_230_OFT
```

MM rows sort by voltage high to low, then natural element name. Non-numeric voltage sorts last.

## Saved Selected-Case Lists

Saved selected-case lists are stored in project JSON and used by the selected export dialog.

These lists affect selected export only. They do not change generated cases.

## Compatibility Notes

- Current app writes schema version `2`.
- Loader keeps backward compatibility for the legacy `res_flux_enabled` field and does not write it back.
- Do not hand-edit project JSON unless needed.
- If hand-editing, run tests and load/save the file in the app after edits.
