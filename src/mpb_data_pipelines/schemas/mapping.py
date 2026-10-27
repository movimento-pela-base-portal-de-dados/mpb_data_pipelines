"""Mapeamento entre colunas de planilhas de origem e campos do schema CKAN."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from mpb_data_pipelines.schemas.constants import (
    CHOICE_PRESETS,
    CKAN_REQUIRED_DATASET_FIELDS,
    PESQUISA_MAPPING_FILE,
    ROLE_ADMIN,
    ROLES,
    TARGET_DATASET,
    TARGET_IGNORE,
    TARGET_RESOURCE,
    TARGETS,
)


class MappingError(Exception):
    pass


@dataclass(frozen=True)
class ColumnMapping:
    column: str
    header: str
    target: str
    field_name: str | None = None
    resource: str | None = None
    preset: str | None = None
    validators: str | None = None
    required: bool = False
    separators: tuple[str, ...] = ()
    choices: tuple[str, ...] = ()
    aliases: dict[str, tuple[str, ...]] = field(default_factory=dict)
    access_roles: tuple[str, ...] = ()
    note: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class Role:
    name: str
    login: bool
    edit: bool


@dataclass(frozen=True)
class DerivedField:
    field_name: str
    target: str
    preset: str | None = None
    value: str | None = None
    source_column: str | None = None
    rule: str | None = None


@dataclass(frozen=True)
class SchemaMapping:
    dataset_type: str
    sheet: str
    header_row: int
    null_values: tuple[str, ...]
    columns: tuple[ColumnMapping, ...]
    derived_fields: tuple[DerivedField, ...]
    resources: dict[str, dict[str, str]]
    roles: dict[str, Role] = field(default_factory=dict)

    def dataset_field_names(self) -> set[str]:
        names = {c.field_name for c in self.columns if c.target == TARGET_DATASET}
        names |= {d.field_name for d in self.derived_fields if d.target == TARGET_DATASET}
        return names


def _parse_column(raw: dict) -> ColumnMapping:
    return ColumnMapping(
        column=raw["column"],
        header=raw["header"],
        target=raw["target"],
        field_name=raw.get("field_name"),
        resource=raw.get("resource"),
        preset=raw.get("preset"),
        validators=raw.get("validators"),
        required=raw.get("required", False),
        separators=tuple(raw.get("separators") or ()),
        choices=tuple(choice["value"] for choice in raw.get("choices") or ()),
        aliases={alias: tuple(values) for alias, values in (raw.get("aliases") or {}).items()},
        access_roles=tuple(raw.get("access_roles") or ()),
        note=raw.get("note"),
        reason=raw.get("reason"),
    )


def validate_mapping(mapping: SchemaMapping) -> None:
    columns = [c.column for c in mapping.columns]
    if duplicated := {c for c in columns if columns.count(c) > 1}:
        raise MappingError(f"colunas repetidas: {sorted(duplicated)}")

    if missing := set(ROLES) - set(mapping.roles):
        raise MappingError(f"cargos sem definição em roles: {sorted(missing)}")

    targets: set[tuple[str, str | None, str | None]] = set()
    for c in mapping.columns:
        if unknown := set(c.access_roles) - set(mapping.roles):
            raise MappingError(f"coluna {c.column}: access_roles com cargo desconhecido {unknown}")
        if len(set(c.access_roles)) != len(c.access_roles):
            raise MappingError(f"coluna {c.column}: access_roles com cargo repetido")
        if c.target not in TARGETS:
            raise MappingError(f"coluna {c.column}: destino inválido {c.target!r}")
        if c.target == TARGET_IGNORE:
            if not c.reason:
                raise MappingError(f"coluna {c.column}: destino ignore sem reason")
            continue
        if ROLE_ADMIN not in c.access_roles:
            raise MappingError(f"coluna {c.column}: access_roles sem o cargo {ROLE_ADMIN}")
        if not c.field_name:
            raise MappingError(f"coluna {c.column}: sem field_name")
        if c.target == TARGET_RESOURCE and c.resource not in mapping.resources:
            raise MappingError(f"coluna {c.column}: recurso desconhecido {c.resource!r}")
        if (c.target, c.resource, c.field_name) in targets:
            raise MappingError(f"coluna {c.column}: campo {c.field_name!r} já mapeado")
        targets.add((c.target, c.resource, c.field_name))
        if c.preset in CHOICE_PRESETS and not c.choices:
            raise MappingError(f"coluna {c.column}: preset {c.preset} sem choices")
        for alias, values in c.aliases.items():
            if unknown := set(values) - set(c.choices):
                raise MappingError(f"coluna {c.column}: alias {alias!r} usa {sorted(unknown)}")

    for d in mapping.derived_fields:
        if d.source_column is not None and d.source_column not in columns:
            raise MappingError(f"campo {d.field_name}: coluna {d.source_column} não existe")

    if missing := set(CKAN_REQUIRED_DATASET_FIELDS) - mapping.dataset_field_names():
        raise MappingError(f"campos obrigatórios do CKAN sem mapeamento: {sorted(missing)}")


def load_mapping(path: Path = PESQUISA_MAPPING_FILE) -> SchemaMapping:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    mapping = SchemaMapping(
        dataset_type=raw["dataset_type"],
        sheet=raw["source"]["sheet"],
        header_row=raw["source"]["header_row"],
        null_values=tuple(raw.get("null_values") or ()),
        columns=tuple(_parse_column(column) for column in raw["columns"]),
        derived_fields=tuple(DerivedField(**d) for d in raw.get("derived_fields") or ()),
        resources=raw.get("resources") or {},
        roles={name: Role(name=name, **perms) for name, perms in (raw.get("roles") or {}).items()},
    )
    validate_mapping(mapping)
    return mapping
