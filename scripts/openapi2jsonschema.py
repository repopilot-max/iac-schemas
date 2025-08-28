#!/usr/bin/env python3

# Derived from https://github.com/instrumenta/openapi2jsonschema
import yaml
import json
import sys
import os
import glob
import argparse
import urllib.request
if 'DISABLE_SSL_CERT_VALIDATION' in os.environ:
    import ssl
    ssl._create_default_https_context = ssl._create_unverified_context

def test_additional_properties():
    for test in iter([{
        "input": {"something": {"properties": {}}},
        "expect": {'something': {'properties': {}, "additionalProperties": False}}
    },{
        "input": {"something": {"somethingelse": {}}},
        "expect": {'something': {'somethingelse': {}}}
    }]):
        assert additional_properties(test["input"]) == test["expect"]

def additional_properties(data, skip=False):
    "This recreates the behaviour of kubectl at https://github.com/kubernetes/kubernetes/blob/225b9119d6a8f03fcbe3cc3d590c261965d928d0/pkg/kubectl/validation/schema.go#L312"
    if isinstance(data, dict):
        if "properties" in data and not skip:
            if "additionalProperties" not in data:
                data["additionalProperties"] = False
        for _, v in data.items():
            additional_properties(v)
    return data

def test_replace_int_or_string():
    for test in iter([{
        "input": {"something": {"format": "int-or-string"}},
        "expect": {'something': {'oneOf': [{'type': 'string'}, {'type': 'integer'}]}}
    },{
        "input": {"something": {"format": "string"}},
        "expect": {"something": {"format": "string"}},
    }]):
        assert replace_int_or_string(test["input"]) == test["expect"]

def replace_int_or_string(data):
    new = {}
    try:
        for k, v in iter(data.items()):
            new_v = v
            if isinstance(v, dict):
                if "format" in v and v["format"] == "int-or-string":
                    new_v = {"oneOf": [{"type": "string"}, {"type": "integer"}]}
                else:
                    new_v = replace_int_or_string(v)
            elif isinstance(v, list):
                new_v = list()
                for x in v:
                    new_v.append(replace_int_or_string(x))
            else:
                new_v = v
            new[k] = new_v
        return new
    except AttributeError:
        return data

def allow_null_optional_fields(data, parent=None, grand_parent=None, key=None):
    new = {}
    try:
        for k, v in iter(data.items()):
            new_v = v
            if isinstance(v, dict):
                new_v = allow_null_optional_fields(v, data, parent, k)
            elif isinstance(v, list):
                new_v = list()
                for x in v:
                    new_v.append(allow_null_optional_fields(x, v, parent, k))
            elif isinstance(v, str):
                is_non_null_type = k == "type" and v != "null"
                has_required_fields = grand_parent and "required" in grand_parent
                if is_non_null_type and not has_required_fields:
                    new_v = [v, "null"]
            new[k] = new_v
        return new
    except AttributeError:
        return data

def append_no_duplicates(obj, key, value):
    """
    Given a dictionary, lookup the given key, if it doesn't exist create a new array.
    Then check if the given value already exists in the array, if it doesn't add it.
    """
    if key not in obj:
        obj[key] = []
    if value not in obj[key]:
        obj[key].append(value)

def write_schema_file(schema, filename, output_dir):
    schema = additional_properties(schema, skip=not os.getenv("DENY_ROOT_ADDITIONAL_PROPERTIES"))
    schema = replace_int_or_string(schema)
    schemaJSON = json.dumps(schema, indent=2)

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Create full output path
    output_path = os.path.join(output_dir, os.path.basename(filename))
    
    with open(output_path, "w") as f:
        print(schemaJSON, file=f)
    
    print(f"JSON schema written to {output_path}")

def construct_value(load, node):
    # Handle nodes that start with '='
    # See https://github.com/yaml/pyyaml/issues/89
    if not isinstance(node, yaml.ScalarNode):
        raise yaml.constructor.ConstructorError(
            "while constructing a value",
            node.start_mark,
            "expected a scalar, but found %s" % node.id, node.start_mark
        )
    yield str(node.value)

def get_yaml_files(path):
    """Get all YAML files from a directory or return a single file."""
    if os.path.isdir(path):
        # Get all .yaml and .yml files in the directory
        yaml_files = glob.glob(os.path.join(path, "*.yaml"))
        yaml_files.extend(glob.glob(os.path.join(path, "*.yml")))
        return yaml_files
    else:
        # Assume it's a file or URL
        return [path]

def process_yaml_file(crd_file, output_dir):
    print(f"Processing {crd_file}...")
    
    if crd_file.startswith("http"):
        f = urllib.request.urlopen(crd_file)
    else:
        f = open(crd_file)
    
    with f:
        defs = []
        yaml.SafeLoader.add_constructor(u'tag:yaml.org,2002:value', construct_value)
        for y in yaml.load_all(f, Loader=yaml.SafeLoader):
            if y is None:
                continue
            if "items" in y:
                defs.extend(y["items"])
            if "kind" not in y:
                continue
            if y["kind"] != "CustomResourceDefinition":
                continue
            else:
                defs.append(y)

        for y in defs:
            filename_format = os.getenv("FILENAME_FORMAT", "{kind}_{version}")
            filename = ""
            if "spec" in y and "versions" in y["spec"] and y["spec"]["versions"]:
                for version in y["spec"]["versions"]:
                    if "schema" in version and "openAPIV3Schema" in version["schema"]:
                        filename = filename_format.format(
                            kind=y["spec"]["names"]["kind"],
                            group=y["spec"]["group"].split(".")[0],
                            fullgroup=y["spec"]["group"],
                            version=version["name"],
                        ).lower() + ".json"

                        schema = version["schema"]["openAPIV3Schema"]
                        write_schema_file(schema, filename, output_dir)
                    elif "validation" in y["spec"] and "openAPIV3Schema" in y["spec"]["validation"]:
                        filename = filename_format.format(
                            kind=y["spec"]["names"]["kind"],
                            group=y["spec"]["group"].split(".")[0],
                            fullgroup=y["spec"]["group"],
                            version=version["name"],
                        ).lower() + ".json"

                        schema = y["spec"]["validation"]["openAPIV3Schema"]
                        write_schema_file(schema, filename, output_dir)
            elif "spec" in y and "validation" in y["spec"] and "openAPIV3Schema" in y["spec"]["validation"]:
                filename = filename_format.format(
                    kind=y["spec"]["names"]["kind"],
                    group=y["spec"]["group"].split(".")[0],
                    fullgroup=y["spec"]["group"],
                    version=y["spec"]["version"],
                ).lower() + ".json"

                schema = y["spec"]["validation"]["openAPIV3Schema"]
                write_schema_file(schema, filename, output_dir)

def parse_args():
    parser = argparse.ArgumentParser(description='Convert OpenAPI CRD schemas to JSON Schema')
    parser.add_argument('inputs', nargs='+', help='Files or directories containing YAML CRD definitions')
    parser.add_argument('-o', '--output-dir', default='.', help='Directory to write output JSON schema files (default: current directory)')
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    
    if not args.inputs:
        print('Missing input parameter.\nUsage: %s [FILES_OR_DIRECTORIES]' % sys.argv[0])
        exit(1)

    # Process all input paths
    files_processed = 0
    for input_path in args.inputs:
        yaml_files = get_yaml_files(input_path)
        for yaml_file in yaml_files:
            process_yaml_file(yaml_file, args.output_dir)
            files_processed += 1
    
    print(f"Processing complete. Processed {files_processed} files.")
    exit(0)
