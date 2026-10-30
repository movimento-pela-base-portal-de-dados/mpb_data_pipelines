from dataclasses import replace
from string import ascii_uppercase

import pytest

from mpb_data_pipelines.schemas.mapping import MappingError, load_mapping, validate_mapping
from tests.constants import BLUE_COLUMNS, GREEN_COLUMNS, LINK_COLUMNS, METADADOS_HEADERS


def test_pesquisa_mapping_is_valid() -> None:
    mapping = load_mapping()
    assert mapping.dataset_type == "pesquisa"
    assert mapping.sheet == "Metadados"


def test_pesquisa_mapping_covers_every_column() -> None:
    mapping = load_mapping()
    expected = {
        column: header
        for column, header in zip(ascii_uppercase, METADADOS_HEADERS, strict=False)
        if column not in LINK_COLUMNS
    }
    assert {c.column: c.header for c in mapping.columns} == expected


def test_alias_must_point_to_a_choice() -> None:
    mapping = load_mapping()
    etapa = next(c for c in mapping.columns if c.field_name == "etapa")
    broken = replace(etapa, aliases={"Todas": ("ensino_superior",)})
    columns = tuple(broken if c is etapa else c for c in mapping.columns)
    with pytest.raises(MappingError, match="alias"):
        validate_mapping(replace(mapping, columns=columns))


def test_resource_column_must_reference_known_resource() -> None:
    mapping = load_mapping()
    with pytest.raises(MappingError, match="recurso desconhecido"):
        validate_mapping(replace(mapping, resources={}))


def test_required_ckan_field_must_be_mapped() -> None:
    mapping = load_mapping()
    columns = tuple(c for c in mapping.columns if c.field_name != "tag_string")
    with pytest.raises(MappingError, match="tag_string"):
        validate_mapping(replace(mapping, columns=columns))


def test_access_roles_must_not_repeat() -> None:
    mapping = load_mapping()
    title = next(c for c in mapping.columns if c.field_name == "title")
    broken = replace(title, access_roles=("publico", "admin", "admin"))
    columns = tuple(broken if c is title else c for c in mapping.columns)
    with pytest.raises(MappingError, match="access_roles"):
        validate_mapping(replace(mapping, columns=columns))


def test_roles_permissions() -> None:
    roles = load_mapping().roles
    assert {name: (r.login, r.edit) for name, r in roles.items()} == {
        "publico": (False, False),
        "comum": (True, False),
        "admin": (True, True),
    }


def test_access_roles_must_use_known_role() -> None:
    mapping = load_mapping()
    title = next(c for c in mapping.columns if c.field_name == "title")
    broken = replace(title, access_roles=("diretor", "admin"))
    columns = tuple(broken if c is title else c for c in mapping.columns)
    with pytest.raises(MappingError, match="cargo desconhecido"):
        validate_mapping(replace(mapping, columns=columns))


def test_published_column_must_allow_admin() -> None:
    mapping = load_mapping()
    title = next(c for c in mapping.columns if c.field_name == "title")
    broken = replace(title, access_roles=("publico", "comum"))
    columns = tuple(broken if c is title else c for c in mapping.columns)
    with pytest.raises(MappingError, match="sem o cargo admin"):
        validate_mapping(replace(mapping, columns=columns))


def test_every_role_must_be_defined() -> None:
    mapping = load_mapping()
    roles = {name: r for name, r in mapping.roles.items() if name != "comum"}
    with pytest.raises(MappingError, match="comum"):
        validate_mapping(replace(mapping, roles=roles))


def test_access_roles_follow_header_color() -> None:
    mapping = load_mapping()
    published = {c.column: set(c.access_roles) for c in mapping.columns if c.target != "ignore"}
    assert {col for col in published if col in GREEN_COLUMNS} == GREEN_COLUMNS
    for column, roles in published.items():
        expected = {"comum", "admin"} if column in BLUE_COLUMNS else {"publico", "comum", "admin"}
        assert roles == expected, column


def test_derived_field_cannot_open_its_source_column() -> None:
    mapping = load_mapping()
    termos = next(d for d in mapping.derived_fields if d.field_name == "termos_busca")
    broken = replace(termos, access_roles=("publico", "comum", "admin"))
    derived = tuple(broken if d is termos else d for d in mapping.derived_fields)
    with pytest.raises(MappingError, match="abre a coluna Q"):
        validate_mapping(replace(mapping, derived_fields=derived))
