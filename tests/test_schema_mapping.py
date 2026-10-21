from dataclasses import replace
from string import ascii_uppercase

import pytest

from mpb_data_pipelines.schemas.mapping import MappingError, load_mapping, validate_mapping

# Cabeçalhos da aba Metadados, colunas A a V.
METADADOS_HEADERS = [
    "Título da Pesquisa",
    "Link acesso",
    "Tema",
    "Etapa",
    "Palavras chave",
    "Tipo de estudo",
    "Formato do arquivo",
    "Ano",
    "Observatório",
    "Público",
    "Tópico",
    "Objetivo",
    "Apoio",
    "Realização",
    "Recorte",
    "Resumo",
    "Tradução",
    "Relatório",
    "Sumário",
    "Resumo",
    "Ficha site",
    "OBS",
]


def test_pesquisa_mapping_is_valid() -> None:
    mapping = load_mapping()
    assert mapping.dataset_type == "pesquisa"
    assert mapping.sheet == "Metadados"


def test_pesquisa_mapping_covers_every_column() -> None:
    mapping = load_mapping()
    expected = dict(zip(ascii_uppercase, METADADOS_HEADERS, strict=False))
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
