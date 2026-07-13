import pytest

from case_builder_app.models import (
    CasePart,
    CaseValue,
    ConditionalRule,
    ExclusionCombination,
    LayerChange,
    MMBlocks,
    MMLimit,
    ParameterChange,
    Project,
    ProjectSettings,
    RuleClause,
)
from case_builder_app.services.generator import GenerationError, GenerationService
from case_builder_app.services.validation import ValidationService


def test_generation_applies_exclusions_and_conditional_priority() -> None:
    part_s = CasePart(label="S")
    s1 = CaseValue(token="S1")
    s2 = CaseValue(token="S2")
    s1.changes.use_parameters = True
    s2.changes.use_parameters = True
    s1.changes.parameters.append(ParameterChange(definition="Main", parameter="P", value="1"))
    s2.changes.parameters.append(ParameterChange(definition="Main", parameter="P", value="2"))
    part_s.values = [s1, s2]

    part_q = CasePart(label="Q")
    q1 = CaseValue(token="Q1")
    q2 = CaseValue(token="Q2")
    q2.changes.use_layers = True
    q2.changes.layers.append(LayerChange(section="Layers", layer_type="Extra", target="TC9", state="Enable"))
    part_q.values = [q1, q2]

    exclusion = ExclusionCombination(
        clauses=[
            RuleClause(case_part_id=part_s.id, value_id=s2.id),
            RuleClause(case_part_id=part_q.id, value_id=q2.id),
        ]
    )

    rule = ConditionalRule(name="override", priority=10)
    rule.clauses = [RuleClause(case_part_id=part_s.id, value_id=s1.id), RuleClause(case_part_id=part_q.id, value_id=q2.id)]
    rule.changes.use_parameters = True
    rule.changes.parameters.append(ParameterChange(definition="Main", parameter="P", value="9"))

    project = Project(
        settings=ProjectSettings(),
        case_parts=[part_s, part_q],
        exclusions=[exclusion],
        conditional_rules=[rule],
    )

    cases, stats = GenerationService().generate(project)

    assert stats.total_combinations == 4
    assert stats.excluded_combinations == 1
    assert stats.final_cases == 3
    names = {case.name: case for case in cases}
    assert names["S1_Q2"].parameters[("Main", "P")] == "9"
    assert names["S1_Q2"].layer_changes[("Layers", "Extra", "TC9")] == "Enable"


def test_validation_rejects_duplicate_ids_and_invalid_name_order() -> None:
    first = CasePart(label="First", id="duplicate")
    first.values = [CaseValue(token="A", id="value-id")]
    second = CasePart(label="Second", id="duplicate")
    second.values = [CaseValue(token="B", id="value-id")]
    project = Project(case_parts=[first, second])
    project.settings.case_name_order = ["duplicate", "missing", "duplicate"]

    result = ValidationService().validate_project(project)

    assert result.is_valid is False
    assert "Duplicate case part ID: duplicate" in result.errors
    assert "Unknown case-name order entry: missing" in result.errors
    assert "Duplicate case-name order entry: duplicate" in result.errors


def test_validation_rejects_invalid_conditional_rule_references() -> None:
    case_part = CasePart(label="Scenario", id="part-id", values=[CaseValue(token="S1", id="value-id")])
    rule = ConditionalRule(name="broken", match_mode="SOME")
    rule.clauses = [RuleClause(case_part_id="missing-part", value_id="missing-value")]
    project = Project(case_parts=[case_part], conditional_rules=[rule])

    result = ValidationService().validate_project(project)

    assert result.is_valid is False
    assert "Conditional rule 'broken' has an invalid match mode." in result.errors
    assert "Conditional rule 'broken' references an unknown case part." in result.errors


def test_lower_case_part_overrides_parameter_set_by_upper_case_part() -> None:
    part_upper = CasePart(label="Upper")
    upper_value = CaseValue(token="U1")
    upper_value.changes.use_parameters = True
    upper_value.changes.parameters.append(ParameterChange(definition="Main", parameter="P", value="1"))
    part_upper.values = [upper_value]

    part_lower = CasePart(label="Lower")
    lower_value = CaseValue(token="L1")
    lower_value.changes.use_parameters = True
    lower_value.changes.parameters.append(ParameterChange(definition="Main", parameter="P", value="2"))
    part_lower.values = [lower_value]

    project = Project(case_parts=[part_upper, part_lower])

    cases, stats = GenerationService().generate(project)

    assert stats.final_cases == 1
    assert cases[0].parameters[("Main", "P")] == "2"


def test_lower_case_part_overrides_cb_state_set_by_upper_case_part() -> None:
    part_upper = CasePart(label="Upper")
    upper_value = CaseValue(token="U1")
    upper_value.changes.use_cb = True
    upper_value.changes.cb.off.append("CB_A")
    part_upper.values = [upper_value]

    part_lower = CasePart(label="Lower")
    lower_value = CaseValue(token="L1")
    lower_value.changes.use_cb = True
    lower_value.changes.cb.on.append("CB_A")
    part_lower.values = [lower_value]

    project = Project(case_parts=[part_upper, part_lower])

    cases, stats = GenerationService().generate(project)

    assert stats.final_cases == 1
    assert cases[0].cb_states["CB_A"] == "ON"


def test_case_name_order_does_not_change_application_order() -> None:
    part_a = CasePart(label="A")
    a1 = CaseValue(token="A1")
    a1.changes.use_cb = True
    a1.changes.cb.on.append("CB_66_BUS")
    part_a.values = [a1]

    part_ex = CasePart(label="Ex")
    f = CaseValue(token="F")
    f.changes.use_cb = True
    f.changes.cb.off.append("CB_66_BUS")
    part_ex.values = [f]

    project = Project(case_parts=[part_a, part_ex])
    project.settings.case_name_order = [part_ex.id, part_a.id]

    cases, stats = GenerationService().generate(project)

    assert stats.final_cases == 1
    assert cases[0].name == "F_A1"
    assert cases[0].cb_states["CB_66_BUS"] == "OFF"


def test_legacy_project_load_prunes_hidden_same_as_base_cb_overrides() -> None:
    payload = {
        "base_case": {
            "changes": {
                "use_cb": True,
                "cb": {"off": ["CB_A"], "switch": [], "on": ["CB_B"]},
            }
        },
        "case_parts": [
            {
                "label": "A",
                "values": [
                    {
                        "token": "A1",
                        "changes": {
                            "use_cb": True,
                            "cb": {"off": [], "switch": [], "on": ["CB_A", "CB_B"]},
                        },
                    }
                ],
            }
        ],
    }

    project = Project.from_dict(payload)

    assert project.case_parts[0].values[0].changes.cb.on == ["CB_A"]


def test_schema_v2_project_load_preserves_same_as_base_cb_overrides() -> None:
    payload = {
        "schema_version": 2,
        "base_case": {
            "changes": {
                "use_cb": True,
                "cb": {"off": ["CB_A"], "switch": [], "on": ["CB_B"]},
            }
        },
        "case_parts": [
            {
                "label": "A",
                "values": [
                    {
                        "token": "A1",
                        "changes": {
                            "use_cb": True,
                            "cb": {"off": [], "switch": [], "on": ["CB_A", "CB_B"]},
                        },
                    }
                ],
            }
        ],
    }

    project = Project.from_dict(payload)

    assert project.case_parts[0].values[0].changes.cb.on == ["CB_A", "CB_B"]


def test_disabled_change_section_is_ignored() -> None:
    part = CasePart(label="V")
    value = CaseValue(token="V1")
    value.changes.parameters.append(ParameterChange(definition="Main", parameter="AC_Vgridpu", value="1.05"))
    part.values = [value]

    project = Project(case_parts=[part])

    cases, stats = GenerationService().generate(project)

    assert stats.final_cases == 1
    assert cases[0].parameters == {}


def test_incomplete_resolved_fault_level_raises_generation_error_without_complete_base() -> None:
    part = CasePart(label="FL")
    value = CaseValue(token="F1")
    value.changes.use_fault_level = True
    value.changes.fault_level.rpos = "0.1"
    value.changes.fault_level.xpos = "0.2"
    part.values = [value]

    project = Project(case_parts=[part])
    result = ValidationService().validate_project(project)

    assert result.is_valid

    with pytest.raises(GenerationError) as exc_info:
        GenerationService().generate(project)

    assert "Incomplete resolved fault-level values" in str(exc_info.value)


def test_validation_requires_mm_limits_for_used_voltage_levels() -> None:
    project = Project(
        settings=ProjectSettings(),
        mm_blocks=MMBlocks(
            elements=["MM_230_OFT", "MM_66_ONS"],
            limits_by_voltage=[
                MMLimit(voltage="230", un="230", um="245", sdpf_lg="460", sdpf_ll="460", siwl_lg="850", siwl_ll="850", liwl="1050")
            ],
        )
    )

    result = ValidationService().validate_project(project)

    assert result.is_valid is False
    assert "Missing MM limit row for voltage '66'." in result.errors


def test_exclusion_rule_can_remove_multiple_exact_forbidden_combinations() -> None:
    part_s = CasePart(label="S")
    s1 = CaseValue(token="S1")
    s2 = CaseValue(token="S2")
    part_s.values = [s1, s2]

    part_v = CasePart(label="V")
    v1 = CaseValue(token="V1")
    v2 = CaseValue(token="V2")
    part_v.values = [v1, v2]

    part_x = CasePart(label="X")
    x3 = CaseValue(token="V3")
    x4 = CaseValue(token="V4")
    part_x.values = [x3, x4]

    exclusions = [
        ExclusionCombination(
            clauses=[
                RuleClause(case_part_id=part_s.id, value_id=s1.id),
                RuleClause(case_part_id=part_v.id, value_id=v1.id),
                RuleClause(case_part_id=part_x.id, value_id=x3.id),
            ]
        ),
        ExclusionCombination(
            clauses=[
                RuleClause(case_part_id=part_s.id, value_id=s2.id),
                RuleClause(case_part_id=part_v.id, value_id=v2.id),
                RuleClause(case_part_id=part_x.id, value_id=x3.id),
            ]
        ),
    ]

    project = Project(case_parts=[part_s, part_v, part_x], exclusions=exclusions)

    cases, stats = GenerationService().generate(project)

    assert stats.total_combinations == 8
    assert stats.excluded_combinations == 2
    assert stats.final_cases == 6
    names = {case.name for case in cases}
    assert "S1_V1_V3" not in names
    assert "S2_V2_V3" not in names
    assert "S1_V2_V3" in names
    assert "S2_V1_V3" in names


def test_exclusion_rule_can_remove_all_cases_for_single_value() -> None:
    part_s = CasePart(label="S")
    s1 = CaseValue(token="S1")
    s2 = CaseValue(token="S2")
    part_s.values = [s1, s2]

    part_v = CasePart(label="V")
    v1 = CaseValue(token="V1")
    v2 = CaseValue(token="V2")
    part_v.values = [v1, v2]

    exclusion = ExclusionCombination(
        clauses=[RuleClause(case_part_id=part_s.id, value_id=s1.id)],
    )

    project = Project(case_parts=[part_s, part_v], exclusions=[exclusion])

    cases, stats = GenerationService().generate(project)

    assert stats.total_combinations == 4
    assert stats.excluded_combinations == 2
    assert stats.final_cases == 2
    names = {case.name for case in cases}
    assert "S1_V1" not in names
    assert "S1_V2" not in names
    assert "S2_V1" in names
    assert "S2_V2" in names


def test_base_case_applies_defaults_and_optional_name_prefix() -> None:
    part = CasePart(label="Scenario")
    value = CaseValue(token="S1")
    value.changes.use_parameters = True
    value.changes.parameters.append(ParameterChange(definition="Main", parameter="P", value="2"))
    part.values = [value]

    project = Project(case_parts=[part])
    project.base_case.label = "Reenergisation"
    project.base_case.token = "C72"
    project.base_case.include_in_case_name = True
    project.base_case.changes.use_parameters = True
    project.base_case.changes.parameters = [ParameterChange(definition="Main", parameter="P", value="1")]
    project.base_case.changes.use_cb = True
    project.base_case.changes.cb.on.append("CB_A")

    cases, stats = GenerationService().generate(project)

    assert stats.final_cases == 1
    assert cases[0].name == "C72_S1"
    assert cases[0].parameters[("Main", "P")] == "2"
    assert cases[0].cb_states["CB_A"] == "ON"


def test_layer_override_can_replace_base_row_identity_in_generated_case() -> None:
    part = CasePart(label="Scenario")
    value = CaseValue(token="S1")
    value.changes.use_layers = True

    base_row = LayerChange(section="Sweep_Components", layer_type="Extra", target="FS_OSSHV1", state="Enable")
    value.changes.layers.append(
        LayerChange(
            base_row_id=base_row.id,
            section="",
            layer_type="Main",
            target="",
            state="Disable",
        )
    )
    part.values = [value]

    project = Project(case_parts=[part])
    project.base_case.changes.use_layers = True
    project.base_case.changes.layers = [base_row]

    cases, stats = GenerationService().generate(project)

    assert stats.final_cases == 1
    assert ("Sweep_Components", "Extra", "FS_OSSHV1") not in cases[0].layer_changes
    assert cases[0].layer_changes[("Sweep_Components", "Main", "FS_OSSHV1")] == "Disable"
