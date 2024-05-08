import os
import yaml
import argparse
import sys
import re

def search_object_group(group_name, obj_name2, directory):
    objects = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".yml"):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                        if group_name in data:
                            for obj in data[group_name]['objects']:
                                objects.append(obj)
                                object_path2 = os.path.join(objects_dir, obj_name2)
                                if os.path.exists(object_path2):
                                    for filename in os.listdir(object_path2):
                                        if filename.endswith(".yml"):
                                            file_path = os.path.join(object_path2, filename)
                                            with open(file_path, 'r') as file:
                                                data = yaml.safe_load(file)
                                                if obj in data:
                                                    print("Found {} in file: {}".format(obj, filename))
                                                    print(yaml.dump({obj: data[obj]}))
                except (yaml.YAMLError, UnicodeDecodeError) as e:
                    print(f"Error processing file {filepath}: {e}")
    return objects

def parse_yaml_files(device_groups_directory, object_groups_ietf_directory, object_groups_ieee_directory, object_groups_other_directory, objects_dir, group_name=None):
    group_objects = {}
    for root, dirs, files in os.walk(device_groups_directory):
        for file in files:
            if file.endswith(".yml"):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                        for name, object_groups in data.items():
                            if group_name is None or name == group_name:
                                print(f"START OF {name}::")
                                print(f"Group Name: {name}")
                                group_objects[name] = {'object_groups': {}, 'objects': []}
                                for obj_group in object_groups.get('object_groups', []):
                                    obj_name1 = obj_group.split('_')
                                    obj_name2 = obj_name1[0]
                                    object_path2 = os.path.join(objects_dir, obj_name2, obj_name1[1]) if len(obj_name1) > 1 else None
                                    group_objects[name]['object_groups'][obj_group] = search_object_group(obj_group, obj_name2, object_groups_ietf_directory) \
                                        if obj_group.startswith('ietf') else \
                                        search_object_group(obj_group, obj_name2, object_groups_ieee_directory) if obj_group.startswith('ieee') else \
                                        search_object_group(obj_group, obj_name2, object_groups_other_directory)
                                    group_objects[name]['objects'].extend(group_objects[name]['object_groups'][obj_group])
                except (yaml.YAMLError, UnicodeDecodeError) as e:
                    print(f"Error processing file {filepath}: {e}")
    return group_objects

def read_oid_descriptions(file_path):
    descriptions = {}
    try:
        with open(file_path, 'r') as file:
            description_data = yaml.safe_load(file)
        for oid, description in description_data.items():
            descriptions[oid] = description.strip()
    except yaml.YAMLError as e:
        print(f"Error reading {file_path}: {e}")
    return descriptions

def insert_descriptions(original_file, descriptions):
    updated_lines = []
    with open(original_file, 'r') as file:
        lines = file.readlines()
        for line in lines:
            updated_lines.append(line)
            if line.strip().startswith('oid:'):
                oid_value = line.split(':')[-1].strip()
                if oid_value in descriptions:
                    # Determine indentation level of the OID
                    indentation = len(re.match(r'^(\s*)', line).group(1))
                    # Insert description with the same indentation
                    description_lines = descriptions[oid_value].split('\n')
                    for desc_line in description_lines:
                        updated_lines.append(' ' * indentation + desc_line + '\n')
    with open(original_file, 'w') as file:
        file.writelines(updated_lines)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enter an option", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-g", "--group", action="store", help="Add group name should be one of: vyos, ubiquiti_edgemax, ubiquiti_unifi, synology, samsung_printer, openwrt, mikrotik_routeros, mikrotik_switchos, macos, linux, juniper_ex, juniper_qfx, juniper_mx, juniper_srx, generic, cisco_c1000, cisco_c2960l, calix_axos, arista")
    parser.add_argument("-a", "--all", action="store_true", help="Print everything")
    parser.add_argument("-o", "--output", action="store", help="Output file", default=None)
    args = parser.parse_args()

    # Define the directory paths
    device_groups_directory = '/etc/elastiflow/snmp/device_groups/'
    object_groups_ietf_directory = '/etc/elastiflow/snmp/object_groups/ietf/'
    object_groups_ieee_directory = '/etc/elastiflow/snmp/object_groups/ieee/'
    object_groups_other_directory = '/etc/elastiflow/snmp/object_groups/'
    objects_dir = '/etc/elastiflow/snmp/objects/'

    if args.output:
        sys.stdout = open(args.output, "w")

    try:
        if args.all:
            group_objects = parse_yaml_files(device_groups_directory, object_groups_ietf_directory, object_groups_ieee_directory, object_groups_other_directory, objects_dir)
        elif args.group:
            group_objects = parse_yaml_files(device_groups_directory, object_groups_ietf_directory, object_groups_ieee_directory, object_groups_other_directory, objects_dir, args.group)
            if args.group in group_objects:
                print(f"START OF {args.group}::")
                print(f"Group Name: {args.group}")
                for obj_group in group_objects[args.group]['object_groups']:
                    print(f"Object Group: {obj_group}")
                    for obj in group_objects[args.group]['object_groups'][obj_group]:
                        print(f"Object: {obj}")
        else:
            print("Please specify -h/--help or -a/--all (to print all currently defined mibs) or specify a group name using -g/--group option.")
    finally:
        if args.output:
            sys.stdout.close()
            sys.stdout = sys.__stdout__

    if args.output:
        descriptions = read_oid_descriptions("description.yml")
        insert_descriptions(args.output, descriptions)
    else:
        descriptions = read_oid_descriptions("description.yml")
        insert_descriptions("output.txt", descriptions)
        with open("output.txt", "r") as tmp_output:
            sys.stdout = sys.__stdout__
            print(tmp_output.read())
