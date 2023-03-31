from urllib.parse import urljoin

import requests


class SwarmClient:
    # TODO: refactor requests methods calls to get rid of arguments duplication
    def __init__(self, portainer_url: str, api_key: str):
        # TODO: consider adding `app` path to portainer url
        self.portainer_url = portainer_url
        self.api_key = api_key
        self.endpoint_id = self._get_endpoint_id()
        self.swarm_id = self._get_swarm_id()

    def _request(
            self,
            method,
            path,
            headers=None,
            verify=False,  # TODO: consider making proper certs
            **kwargs
    ):
        url = urljoin(self.portainer_url, path)
        headers = headers or {'X-API-Key': self.api_key}
        resp = requests.request(method, url, headers=headers, verify=verify, **kwargs)
        # TODO: replace raise_for_status with something more accurate than not restricts further response usage.
        # TODO: maybe add raise_for_status: bool arg
        try:
            resp.raise_for_status()
        except requests.exceptions.HTTPError:
            raise requests.exceptions.HTTPError(f'{resp.status_code}\n{resp.text}')
        return resp

    def _get(self, path, **kwargs):
        return self._request('get', path, **kwargs)

    def _post(self, path, **kwargs):
        return self._request('post', path, **kwargs)

    def _delete(self, path, **kwargs):
        return self._request('delete', path, **kwargs)

    def _get_swarm_id(self):
        resp = self._get(f'/api/endpoints/{self.endpoint_id}/docker/swarm')
        return resp.json()['ID']

    def _get_endpoint_id(self):
        # TODO: make proper endpoints handling in case we will face more than one endpoint
        endpoints = self._get('/api/endpoints').json()
        if len(endpoints) != 1:
            raise ValueError(f'Expected only one Portainer endpoint, got {len(endpoints)}:\n{endpoints}')
        return endpoints[0]['Id']

    def create_stack(self, file: str, stack_name: str):
        # TODO: add/replace with creating stack with string
        return self._post(
            '/api/stacks',
            params={'type': 2, 'method': 'file', 'SwarmID': self.swarm_id,
                    'endpointId': self.endpoint_id, 'Name': stack_name},
            files={'file': open(file, 'rb')}
        )

    def get_stacks(self):
        return self._get('/api/stacks').json()

    def delete_stack(self, stack_id):
        return self._delete(f'/api/stacks/{stack_id}', params={'external': True, 'endpointId': self.endpoint_id})
