import csv
import logging
import os
import pprint

from linkml.generators.projectgen import ProjectGenerator, ProjectConfiguration
from linkml_runtime.dumpers import yaml_dumper
from linkml_runtime.utils.schema_as_dict import schema_as_dict
from linkml_runtime.utils.schemaview import SchemaView
from linkml.utils.helpers import write_to_file

from schemasheets.schemamaker import SchemaMaker, get_metamodel, SchemaSheetRowException

# todo what about assertions into read only slots?
#   linkml2schemasheets-template --source-path "https://w3id.org/linkml/meta.yaml" --output-path meta.tsv --report-style exhaustive > meta_template_report.txt

# definition_uri
# from_schema
# generation_date
# imported_from
# metamodel_version
# source_file
# source_file_date
# source_file_size

SCHEMA_NAME = 'mixs_test'

ROOT = os.path.abspath(os.path.dirname(__file__))  # /Users/MAM/Documents/gitrepos/schemasheets/tests/test_121
INPUT_DIR = os.path.join(ROOT, 'input')
OUTPUT_DIR = os.path.join(ROOT, 'output')

# PROBLEM_DIR = os.path.join(INPUT_DIR, 'problem_cases')

SCHEMA_DEF_TSV = os.path.join(INPUT_DIR, 'schema_def.tsv')
PREFIX_DEFS_TSV = os.path.join(INPUT_DIR, 'prefix_defs.tsv')
SUBSET_DEFS_TSV = os.path.join(INPUT_DIR, 'subset_defs.tsv')

SCHEMA_YAML = os.path.join(OUTPUT_DIR, f"{SCHEMA_NAME}.yaml")


def test_mixs_generation():
    sm = SchemaMaker(use_attributes=False,
                     unique_slots=True,
                     # default_name=SCHEMA_NAME,
                     )
    schema = sm.create_schema([
        SCHEMA_DEF_TSV,
        PREFIX_DEFS_TSV,
        SUBSET_DEFS_TSV,
    ])
    schema = sm.repair_schema(schema)
    print(yaml_dumper.dumps(schema))

    # yaml_str = yaml_dumper.dumps(schemaview.schema)
    # print(yaml_str)
    # write_to_file(SCHEMA_YAML, yaml_str)
