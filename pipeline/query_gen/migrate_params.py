#!/usr/bin/env python3
"""
Migration script: Rename shorthand parameter keys to full descriptive names
in the management template JSON file.

Mapping (short -> descriptive):
  L   -> Label       (standalone label)
  L1  -> Label1
  L2  -> Label2
  L3  -> Label3
  L4  -> Label4
  L5  -> Label5
  GL  -> GroupLabel
  SL  -> StartLabel
  EL  -> EndLabel
  RL  -> RefLabel
  P   -> Prop        (standalone property)
  P1  -> Prop1
  P2  -> Prop2
  BP  -> BaseProp
  SP  -> StartProp
  NP  -> NumProp
  GP  -> GroupProp
  R   -> Rel         (standalone relationship)
  R1  -> Rel1
  R2  -> Rel2
  R3  -> Rel3
  RP  -> RelProp
  V   -> Val
  SV  -> StartVal
  NV  -> NumVal
"""
import json
import re
import sys
from pathlib import Path
from collections import OrderedDict

# Mapping from old shorthand to new descriptive name
# Order matters: longer names first to avoid partial replacements
PARAM_RENAME_MAP = OrderedDict([
    # Labels
    ("L1", "Label1"),
    ("L2", "Label2"),
    ("L3", "Label3"),
    ("L4", "Label4"),
    ("L5", "Label5"),
    ("GL", "GroupLabel"),
    ("SL", "StartLabel"),
    ("EL", "EndLabel"),
    ("RL", "RefLabel"),
    ("L",  "Label"),      # standalone L last (after L1-L5)
    # Properties
    ("P1", "Prop1"),
    ("P2", "Prop2"),
    ("BP", "BaseProp"),
    ("SP", "StartProp"),
    ("NP", "NumProp"),
    ("GP", "GroupProp"),
    ("P",  "Prop"),       # standalone P last (after P1, P2)
    # Relationships
    ("R1", "Rel1"),
    ("R2", "Rel2"),
    ("R3", "Rel3"),
    ("RP", "RelProp"),
    ("R",  "Rel"),        # standalone R last (after R1-R3, RP)
    # Values
    ("SV", "StartVal"),
    ("V",  "Val"),        # standalone V last
    # NumVal variants
    ("NV1", "NumVal1"),
    ("NV2", "NumVal2"),
    ("NV3", "NumVal3"),
    ("NV4", "NumVal4"),
    ("NV5", "NumVal5"),
    ("NV",  "NumVal"),
])


def rename_in_string(s: str, mapping: dict) -> str:
    """
    Rename $PARAM references in a Cypher query string.
    Uses word-boundary matching to avoid partial replacements.
    Processes longer keys first.
    """
    # Sort by key length descending so longer names match first
    sorted_items = sorted(mapping.items(), key=lambda x: len(x[0]), reverse=True)
    for old, new in sorted_items:
        # Replace $OLD with $NEW, respecting word boundaries
        # The $ prefix is part of the pattern; after the name we need a non-word char or end-of-string
        pattern = re.compile(r'\$' + re.escape(old) + r'(?=\b|[^A-Za-z0-9_]|$)')
        s = pattern.sub('$' + new, s)
    return s


def rename_params_in_dict(params: dict, mapping: dict) -> dict:
    """Rename parameter keys in a parameters dict."""
    new_params = {}
    for key, val in params.items():
        new_key = mapping.get(key, key)
        new_params[new_key] = val
    return new_params


def migrate_template_file(input_path: str, output_path: str):
    """Read template JSON, rename all shorthand params, write output."""
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for op_group in data:
        for tmpl in op_group.get("templates", []):
            # Rename in parameters dict
            if "parameters" in tmpl:
                tmpl["parameters"] = rename_params_in_dict(tmpl["parameters"], PARAM_RENAME_MAP)

            # Rename in template strings
            if isinstance(tmpl.get("template"), list):
                tmpl["template"] = [rename_in_string(s, PARAM_RENAME_MAP) for s in tmpl["template"]]
            elif isinstance(tmpl.get("template"), str):
                tmpl["template"] = rename_in_string(tmpl["template"], PARAM_RENAME_MAP)

            # Rename in validation string
            if "validation" in tmpl and isinstance(tmpl["validation"], str):
                tmpl["validation"] = rename_in_string(tmpl["validation"], PARAM_RENAME_MAP)

            # Rename in pre_validation / post_validation (if present)
            for field in ("pre_validation", "post_validation"):
                if field in tmpl and isinstance(tmpl[field], str):
                    tmpl[field] = rename_in_string(tmpl[field], PARAM_RENAME_MAP)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Migrated: {input_path} -> {output_path}")


if __name__ == "__main__":
    base = Path(__file__).parent
    input_file = base / "query_template" / "template_managemet.json"
    output_file = base / "query_template" / "template_managemet.json"  # overwrite in-place

    if not input_file.exists():
        print(f"ERROR: {input_file} not found")
        sys.exit(1)

    migrate_template_file(str(input_file), str(output_file))
    print("Done. Verify the output and then update the Python sampling code.")
