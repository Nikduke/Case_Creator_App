from __future__ import annotations

from case_builder_app.models import ExclusionCombination, Project, RuleClause
from case_builder_app.services.text_tokens import parse_token_text


def resolve_exclusion_token(project: Project, token: str) -> RuleClause:
    if "=" in token:
        case_part_label, value_token = [item.strip() for item in token.split("=", 1)]
        case_part = next((item for item in project.case_parts if item.label == case_part_label), None)
        if case_part is None:
            raise ValueError(f"Unknown case part in exclusion: {case_part_label}")
        value = next((item for item in case_part.values if item.token == value_token), None)
        if value is None:
            raise ValueError(f"Unknown value '{value_token}' for case part '{case_part_label}'.")
        return RuleClause(case_part_id=case_part.id, value_id=value.id)

    matches: list[tuple[str, str, str]] = []
    for case_part in project.case_parts:
        for value in case_part.values:
            if value.token == token:
                matches.append((case_part.id, case_part.label, value.id))

    if not matches:
        raise ValueError(f"Unknown exclusion token: {token}")
    if len(matches) > 1:
        labels = ", ".join(match[1] for match in matches)
        raise ValueError(f"Ambiguous token '{token}'. Use CasePart=Value. Matching case parts: {labels}")

    case_part_id, _label, value_id = matches[0]
    return RuleClause(case_part_id=case_part_id, value_id=value_id)


def parse_exclusion_text(project: Project, text: str) -> list[ExclusionCombination]:
    raw_lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not raw_lines:
        raw_lines = [text.strip()] if text.strip() else []
    if not raw_lines:
        raise ValueError("Enter at least one token for the excluded combination.")

    combinations: list[ExclusionCombination] = []
    for raw_line in raw_lines:
        normalized = raw_line.replace(" ", ",")
        tokens = parse_token_text(normalized)
        if not tokens:
            continue

        current_clauses: list[RuleClause] = []
        seen_case_parts: set[str] = set()
        for token in tokens:
            clause = resolve_exclusion_token(project, token)
            if clause.case_part_id in seen_case_parts:
                if current_clauses:
                    combinations.append(ExclusionCombination(clauses=current_clauses))
                current_clauses = [clause]
                seen_case_parts = {clause.case_part_id}
                continue
            current_clauses.append(clause)
            seen_case_parts.add(clause.case_part_id)

        if current_clauses:
            combinations.append(ExclusionCombination(clauses=current_clauses))

    if not combinations:
        raise ValueError("Enter at least one token for the excluded combination.")
    return combinations
