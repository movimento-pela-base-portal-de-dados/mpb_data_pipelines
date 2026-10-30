"""Constantes do pacote schemas."""

from pathlib import Path

PESQUISA_MAPPING_FILE = Path(__file__).with_name("pesquisa.yaml")

TARGET_DATASET = "dataset"
TARGET_RESOURCE = "resource"
TARGET_IGNORE = "ignore"
TARGETS = (TARGET_DATASET, TARGET_RESOURCE, TARGET_IGNORE)

ROLE_PUBLICO = "publico"
ROLE_COMUM = "comum"
ROLE_ADMIN = "admin"
ROLES = (ROLE_PUBLICO, ROLE_COMUM, ROLE_ADMIN)

CHOICE_PRESETS = ("select", "multiple_select", "multiple_checkbox", "radio")

# Campos que o schema do mpb-ckan exige em todo conjunto de dados.
CKAN_REQUIRED_DATASET_FIELDS = ("title", "name", "tag_string", "owner_org")
