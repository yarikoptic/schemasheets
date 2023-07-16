# import os
import pprint

from click import command, option
from jsonasobj2 import as_dict
from linkml_runtime import SchemaView
from linkml_runtime.dumpers import yaml_dumper
from schemasheets.conf.configschema import ColumnSettings
from schemasheets.schema_exporter import SchemaExporter
from schemasheets.schemasheet_datamodel import TableConfig, ColumnConfig

# todo: include read only slots?

# todo: check metamodel if element is deprecated
#  (if it can be included in the report, the deprecation status will be reported!)
#   like subclass_of, subproperty_of ?

# todo check for inlining in addition to checking if a range class has a identifier slot?

# todo offer a concise report based on the slots that are actually used
#  in the SlotDefinitions and ClassDefinitions in the source schema

# todo slots which might require multiple columns for multiple inner keys

root_classes = ['slot_definition', "class_definition"]  # hard coding the intention to do a class slot usage report

# todo could these be semantically derived from the root_classes? other than lexical string splitting?
boilerplate_cols = ['slot', 'class']

# these a slots whose ranges are classes with identifier slots, but they still can't be included in the report
blacklist = ['attributes', 'slot_usage', 'name', 'instantiates', 'slots', ]

# this salves these slots (by name) from untemplateables
requires_column_settings = {
    "examples values": {
        "name": "examples",
        "ikm_slot": "value",  # todo: what about description?
        "ikm_class": "example",
        "internal_separator": "|",

    },
    "structured_pattern": {
        "name": "structured_pattern",
        "ikm_slot": "syntax",  # todo what about interpolated and partial_match
        "ikm_class": "pattern_expression",
        "internal_separator": "|",

    },
    "unit symbol": {
        "name": "unit",
        "ikm_slot": "symbol",
        # todo what about symbol, exact mappings, ucum_code, derivation, has_quantity_kind, iec61360code
        "ikm_class": "UnitOfMeasure",
        "internal_separator": "|",
    },
}


def tabulate_unique_values(list_):
    """
    tabulate the number of appearances of each unique values in a list

    Args:
        list_ (list): The list to tabulate.

    Returns:
        dict: A dict mapping each unique value to the number of times it appears in the list.
    """

    unique_values = set(list_)
    value_counts = {}
    for value in unique_values:
        count = list_.count(value)
        value_counts[value] = count

    sorted_value_counts = sorted(value_counts.items(), key=lambda x: x[1], reverse=True)

    return sorted_value_counts


# todo add annotations discovery
def discover_source_usage(source_view):
    discovered_meta_slots = []
    discovered_annotations = []
    source_classes = source_view.all_classes()
    for ck, cv in source_classes.items():
        cv_dict = cv.__dict__
        for cvdk, cvdv in cv_dict.items():
            if cvdv:
                discovered_meta_slots.append(cvdk)

        class_annotations = list(source_view.get_class(ck).annotations.keys())  # TODO this isn't well tested yet
        for ca in class_annotations:
            discovered_annotations.append(ca)

        for cis in source_view.class_induced_slots(ck):
            cis_dict = cis.__dict__

            for cisk, cisv in cis_dict.items():
                if cisv:
                    discovered_meta_slots.append(cisk)

            cis_annotations_dict = as_dict(cis.annotations)
            for a in cis_annotations_dict:
                discovered_annotations.append(a)

    return discovered_meta_slots, discovered_annotations


@command()
@option("--meta-path", "-m", default="https://w3id.org/linkml/meta",
        help="A filesystem or URL path to the LinkML metamodel schema.")
@option("--meta-staging-path", "-s", default="meta_merged.yaml",
        help="A filesystem path for saving the merged  LinkML metamodel locally.")
@option("--source-path", "-i", required=True,
        help="A filesystem or URL path to the schema that should be reported on.")
@option("--output-path", "-o", default="populated_with_generated_spec.tsv")
def cli(meta_path, source_path, output_path, meta_staging_path):
    """
    A CLI tool to generate a slot usage schemasheet from the LinkML metamodel and a source schema.
    """

    print(meta_path)
    print(source_path)

    columns_dict = {}

    # we discover which class-range slots have an identifying slot and then exclude the blacklist slots
    identifiables = {}

    slot_scan_results = {}

    # these are slots whose range is a class lacking an identifying slot
    untemplateables = {}

    discovered_cols = []
    slot_ranges = []

    # in some cases it will be better to get this from a local filesystem, not a URL...
    # todo: add script/targets for downloading and merging

    meta_view = SchemaView(meta_path, merge_imports=True)

    # not really necessary
    yaml_dumper.dump(meta_view.schema, meta_staging_path)

    source_view = SchemaView(source_path, merge_imports=True)

    (discovered_source_slots, discovered_annotations) = discover_source_usage(source_view)
    discovered_source_slots = list(set(discovered_source_slots))
    discovered_source_slots.sort()

    discovered_annotations = list(set(discovered_annotations))
    discovered_annotations.sort()

    discovered_source_slots = list(set(discovered_source_slots) - set(blacklist))
    discovered_source_slots.sort()
    discovered_source_slots = boilerplate_cols + discovered_source_slots
    pprint.pprint(discovered_source_slots)

    root_classes.sort()

    meta_types = meta_view.schema.types
    meta_type_names = list(meta_types.keys())

    meta_enum_names = list(meta_view.all_enums().keys())
    meta_enum_names.sort()

    print("\n")
    for current_root in root_classes:
        current_induced_slots = meta_view.class_induced_slots(current_root)
        for cis in current_induced_slots:

            temp_dict = {"range": cis.range, "multivalued": cis.multivalued, "type_range": cis.range in meta_type_names}
            if cis.name not in slot_scan_results:
                slot_scan_results[cis.name] = temp_dict

            # # todo make this a debug logger message
            # else:
            #     if slot_scan_results[cis.name] == temp_dict:
            #         continue
            #     else:
            #         print(f"Redefining {cis.name} from {slot_scan_results[cis.name]} to {temp_dict}")

    for c in boilerplate_cols:
        columns_dict[c] = ColumnConfig(name=c,
                                       maps_to=c,
                                       is_element_type=True,
                                       settings=ColumnSettings()
                                       )

    for rcs_k, rcs_v in requires_column_settings.items():
        temp_settings = ColumnSettings()
        if "internal_separator" in rcs_v:
            temp_settings.internal_separator = rcs_v["internal_separator"]
        if "ikm_class" in rcs_v and "ikm_slot" in rcs_v:
            temp_settings.inner_key = rcs_v["ikm_slot"]
        columns_dict[rcs_k] = ColumnConfig(
            name=rcs_v["name"],
            is_element_type=False,
            maps_to=rcs_v["name"],
            metaslot=meta_view.get_slot(rcs_v["name"]),
            settings=temp_settings
        )
        if "ikm_class" in rcs_v and "ikm_slot" in rcs_v:
            columns_dict[rcs_k].inner_key_metaslot = meta_view.induced_slot(rcs_v["ikm_slot"], rcs_v["ikm_class"])

    for ssk, ssv in slot_scan_results.items():
        if ssv["range"] not in meta_type_names and ssv["range"] not in meta_enum_names:
            slot_ranges.append(ssv["range"])

    slot_ranges.sort()

    tabulation_results = tabulate_unique_values(slot_ranges)

    for tabulation_result in tabulation_results:
        current_range = tabulation_result[0]
        # current_count = tabulation_result[1]
        current_identifier = meta_view.get_identifier_slot(current_range)
        if current_identifier:
            identifiables[current_range] = current_identifier.name
        else:
            pass

    requires_column_settings_names = []
    for rcs_k, rcs_v in requires_column_settings.items():
        requires_column_settings_names.append(rcs_v["name"])

    for ssrk, ssrv in slot_scan_results.items():
        current_range = ssrv["range"]
        if current_range in meta_type_names or current_range in meta_enum_names:
            discovered_cols.append(ssrk)
        elif current_range in identifiables:
            if ssrk in blacklist:
                print(f"Skipping {ssrk} because it is in the blacklist")
            else:
                discovered_cols.append(ssrk)
        elif ssrk in requires_column_settings_names:
            continue
        else:
            untemplateables[ssrk] = ssrv

    for da in discovered_annotations:
        columns_dict[da] = ColumnConfig(
            name="annotations",
            is_element_type=False,
            maps_to="annotations",
            metaslot=meta_view.get_slot("annotations"),
            settings=ColumnSettings(inner_key=da),
        )

    pprint.pprint(untemplateables)

    discovered_cols.sort()

    for c in discovered_cols:
        c_slug = c.replace(" ", "_")
        ms = meta_view.get_slot(c)
        mv = False
        if ms:
            mv = ms.multivalued
        if mv:
            cs = ColumnSettings(internal_separator="|")
        else:
            cs = ColumnSettings()
        cc = ColumnConfig(
            maps_to=c,
            metaslot=ms,
            name=c_slug,
            settings=cs,
        )
        columns_dict[c] = cc  # use verbatim elements (not slugged) in first row?

    new_tc = TableConfig(
        column_by_element_type={'slot': 'slot', 'class': 'class'},
        columns=columns_dict
    )

    current_exporter = SchemaExporter()
    current_exporter.export(
        schemaview=source_view,
        table_config=new_tc,
        to_file=output_path,
    )


if __name__ == "__main__":
    cli()