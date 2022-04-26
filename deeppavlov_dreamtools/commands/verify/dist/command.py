# import re
# from pathlib import Path
# from textwrap import shorten
# from typing import Union, Tuple, Optional, Dict, Iterable
#
# from deeppavlov_dreamtools.distconfigs.generics import AnyConfig
# from deeppavlov_dreamtools.utils import (
#     create_logger,
# )
# from deeppavlov_dreamtools.constants import (
#     DELIMITER,
#     REQUIRED_CONFIG_NAMES,
#     OPTIONAL_CONFIG_NAMES,
#     ALL_CONFIG_NAMES,
# )
#
# logger = create_logger("verify_dist")
#
#
# def get_all_configs(
#     assistant_dist_dir: Union[Path, str],
#     pipeline_conf: bool = True,
#     compose_override: bool = True,
#     compose_dev: bool = True,
#     compose_proxy: bool = True,
#     compose_local: bool = True,
#     load_all: bool = True,
#     load_required: bool = True,
#     load_optional: bool = True,
# ):
#     all_configs = {}
#     assistant_dist_dir = Path(assistant_dist_dir)
#
#     config_names = []
#     if load_all:
#         config_names = ALL_CONFIG_NAMES
#     else:
#         if load_required:
#             config_names += REQUIRED_CONFIG_NAMES
#         if load_optional:
#             config_names += OPTIONAL_CONFIG_NAMES
#
#     for name in config_names:
#         config_path = (assistant_dist_dir / name).resolve()
#         config = load_config(config_path)
#         all_configs[config_path] = config
#
#     return all_configs
#
#
# def discover_unique_container_names(
#     configs: Dict[Path, AnyConfig]
# ):
#     all_container_names = []
#     for config in configs.values():
#         all_container_names += list(config.container_names)
#
#     return set(all_container_names)
#
#
# def compare_names(all_container_names: Iterable, configs: Dict[Path, AnyConfig]):
#     names_diff = {}
#
#     for path, config in configs.items():
#         diff = set(all_container_names) - set(config.container_names)
#         names_diff[path] = list(diff)
#
#     return names_diff
#
#
# def compare_ports(all_container_names: Iterable, configs: Dict[Path, AnyConfig]):
#     ports_diff = {n: {} for n in all_container_names}
#
#     for container_name in all_container_names:
#         for path, container_dict in configs.items():
#             container_args = container_dict.get(container_name)
#             if container_args:
#                 args_with_ports = []
#
#                 for k, port in iter_field_keys_values(container_args, "url"):
#                     args_with_ports.append({"key": k, "text": port, "value": port})
#
#                 for k, port in iter_field_keys_values(container_args, "SERVICE_PORT"):
#                     args_with_ports.append({"key": k, "text": port, "value": port})
#
#                 for k, cmd in iter_field_keys_values(container_args, "command"):
#                     if isinstance(cmd, str) and not cmd.startswith("nginx"):
#                         try:
#                             port = re.findall(
#                                 r"-p (\d{3,6})|--port (\d{3,6})|\d+?.\d+?.\d+?.\d+?:(\d{3,6})",
#                                 cmd,
#                             )[0]
#                             args_with_ports.append(
#                                 {
#                                     "key": k,
#                                     "text": cmd,
#                                     "value": port[0] or port[1] or port[2],
#                                 }
#                             )
#                         except IndexError:
#                             pass
#
#                 for k, port_map in iter_field_keys_values(container_args, "ports"):
#                     args_with_ports.append(
#                         {"key": k, "text": port_map, "value": port_map[0].split(":")[0]}
#                     )
#
#                 for k, envs in iter_field_keys_values(container_args, "environment"):
#                     for e in envs:
#                         if e.startswith("PORT="):
#                             args_with_ports.append(
#                                 {"key": k, "text": e, "value": e.split("=")[-1]}
#                             )
#
#                 if args_with_ports:
#                     ports_diff[container_name][path] = args_with_ports
#
#     for name, diff in ports_diff.items():
#         all_port_definitions = []
#
#         for path, ports in diff.items():
#             all_port_definitions += ports
#         try:
#             if all(
#                 int(p["value"]) == int(all_port_definitions[0]["value"])
#                 for p in all_port_definitions
#                 if p["value"]
#             ):
#                 ports_diff[name] = {}
#         except ValueError:
#             pass
#
#     return ports_diff
#
#
# def dist(
#     name: str,
#     dream_root: Union[Path, str],
#     load_all: bool = True,
#     load_required: bool = True,
#     load_optional: bool = True,
# ):
#     dist_dir = Path(dream_root) / "assistant_dists" / name
#     if not dist_dir.exists():
#         raise Exception(f"{dist_dir} is not a Dream distribution")
#
#     configs = get_all_configs(dist_dir, load_all, load_required, load_optional)
#     all_container_names = discover_unique_container_names(configs)
#
#     config_names = ", ".join(c.name for c in configs.keys())
#     yield f"Verifying {len(configs.keys())} configs inside {dist_dir}: {config_names}"
#
#     names_diff = compare_names(all_container_names, configs)
#
#     yield f"Found {len(all_container_names)} container definitions"
#     yield DELIMITER
#     for path, diff in names_diff.items():
#         diff = [d for d in diff if d not in ["agent", "mongo"]]
#         if diff:
#             diff_str = ", ".join(diff)
#             diff_str = shorten(diff_str, width=100, break_on_hyphens=False)
#             yield f"{path.name:<30}{len(diff)} missing: {diff_str}"
#         else:
#             yield f"{path.name:<30}OK"
#
#     yield DELIMITER
#     ports_diff = compare_ports(all_container_names, configs)
#     ports_diff.pop("agent")
#     ports_diff.pop("mongo")
#
#     if all(d == {} for d in ports_diff.values()):
#         yield f"All port definitions OK"
#     else:
#         for container_name, diff in ports_diff.items():
#             if diff:
#                 diffs = []
#                 for path, ports in diff.items():
#                     diff_str = ", ".join(f"{p['key']}: {p['text']}" for p in ports)
#                     diff_str = f"{path.name} ({diff_str})"
#                     diffs.append(diff_str)
#                 diffs = ", ".join(diffs)
#
#                 yield f"{container_name:<30}Inconsistent port definitions in {diffs}"
