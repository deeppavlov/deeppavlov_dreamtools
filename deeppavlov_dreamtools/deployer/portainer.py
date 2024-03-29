from logging import getLogger
from pathlib import Path
from typing import List, Union
from urllib.parse import urljoin

import requests
import urllib3
import yaml

from deeppavlov_dreamtools.deployer.models import Stack

# TODO: remove when insecure request cause will be eliminated
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = getLogger(__file__)


class SwarmClient:
    # TODO: refactor requests methods calls to get rid of arguments duplication
    # TODO: add ecr login through api
    def __init__(self, portainer_url: str, api_key: str):
        # TODO: consider adding `app` path to portainer url
        self.portainer_url = portainer_url
        self.api_key = api_key
        self.endpoint_id = self._get_endpoint_id()
        self.swarm_id = self._get_swarm_id()

    def _request(self, method, path, headers=None, verify=False, **kwargs):  # TODO: consider making proper certs
        url = urljoin(self.portainer_url, path)
        headers = headers or {"X-API-Key": self.api_key}
        resp = requests.request(method, url, headers=headers, verify=verify, **kwargs)
        # TODO: replace raise_for_status with something more accurate than not restricts further response usage.
        # TODO: maybe add raise_for_status: bool arg
        try:
            resp.raise_for_status()
        except requests.exceptions.HTTPError:
            raise requests.exceptions.HTTPError(f"{resp.status_code}\n{resp.text}")
        return resp

    def _get(self, path, **kwargs):
        return self._request("get", path, **kwargs)

    def _post(self, path, **kwargs):
        return self._request("post", path, **kwargs)

    def _delete(self, path, **kwargs):
        return self._request("delete", path, **kwargs)

    def _put(self, path, **kwargs):
        return self._request("put", path, **kwargs)

    def _get_swarm_id(self):
        resp = self._get(f"/api/endpoints/{self.endpoint_id}/docker/swarm")
        return resp.json()["ID"]

    def _get_endpoint_id(self):
        # TODO: make proper endpoints handling in case we will face more than one endpoint
        endpoints = self._get("/api/endpoints").json()
        if len(endpoints) != 1:
            raise ValueError(f"Expected only one Portainer endpoint, got {len(endpoints)}:\n{endpoints}")
        return endpoints[0]["Id"]

    def create_stack(self, file: Union[str, Path], stack_name: str) -> Stack:
        # TODO: add/replace with creating stack with string
        ans = self._post(
            "/api/stacks",
            params={
                "type": 1,
                "method": "file",
                "SwarmID": self.swarm_id,
                "endpointId": self.endpoint_id,
                "Name": stack_name,
            },
            files={"file": open(file, "rb")},
        )
        return Stack.parse_obj(ans.json())

    def get_stacks(self) -> List[Stack]:
        return [Stack.parse_obj(s) for s in self._get("/api/stacks").json()]

    def delete_stack(self, stack_id):
        return self._delete(f"/api/stacks/{stack_id}", params={"external": True, "endpointId": self.endpoint_id})

    def update_stack(self, stack_id: int, file: Union[str, Path], prune: bool = True, pull_image: bool = True):
        """
        Args:
            stack_id: Stack identifier.
            file: Stack file.
            prune: Whether nor not prune (remove) services that are no longer in the updated stack.
            pull_image: Force a pulling to current image with the original tag though the image is already the latest.
        """
        with open(file) as fin:
            stack_file_content = fin.read()
        return self._put(
            f"/api/stacks/{stack_id}",
            params={
                "id": stack_id,
                "endpointId": self.endpoint_id,
            },
            json={
                "prune": prune,
                "pullImage": pull_image,
                "stackFileContent": stack_file_content,
            },
        )

    def get_stack_file(self, stack_id):
        ans = self._get(f"/api/stacks/{stack_id}/file")
        return yaml.safe_load(ans.json()["StackFileContent"])

    def get_reservations(self) -> int:
        """Gets all deployed stacks memory reservations."""
        reservations = {}
        for stack in self.get_stacks():
            file = self.get_stack_file(stack.Id)
            mem = [s.get('deploy', {}).get('resources', {}).get('reservations', {}).get('memory', {}) for s in
                   file['services'].values()]
            reservations[stack.Name] = sum([int(m) for m in mem if m])
        reservations['total_reserves'] = sum(reservations.values())
        return reservations

    def get_used_ports(self):
        stacks = self.get_stacks()
        stack_files = []
        for stack in stacks:
            if stack.Status != 1:
                continue
            try:
                stack_files.append(self.get_stack_file(stack.Id))
            except requests.exceptions.HTTPError as e:
                logger.error(f'Got {repr(e)} error for stack.Id == {stack.Id}')
        return {
            stack.Id: file["services"]["agent"]["ports"][0]["published"] for stack, file in zip(stacks, stack_files)
        }
