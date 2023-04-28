from pydantic import BaseModel
from typing import Optional, Any

examp = [{'Id': 71, 'Name': 'universal', 'Type': 1, 'EndpointId': 2, 'SwarmId': 'c99ty3x3rso84f5llnjb259x4',
          'EntryPoint': 'docker-compose.yml', 'Env': None,
          'ResourceControl': {'Id': 70, 'ResourceId': '2_universal', 'SubResourceIds': [], 'Type': 6,
                              'UserAccesses': [], 'TeamAccesses': [], 'Public': False, 'AdministratorsOnly': True,
                              'System': False}, 'Status': 1, 'ProjectPath': '/data/compose/71',
          'CreationDate': 1682670869, 'CreatedBy': 'dp-admin', 'UpdateDate': 0, 'UpdatedBy': '',
          'AdditionalFiles': None, 'AutoUpdate': None, 'GitConfig': None, 'FromAppTemplate': False, 'Namespace': '',
          'IsComposeFormat': False},
         {'Id': 72, 'Name': 'faq_2b6d70d8', 'Type': 1, 'EndpointId': 2, 'SwarmId': 'c99ty3x3rso84f5llnjb259x4',
          'EntryPoint': 'docker-compose.yml', 'Env': None,
          'ResourceControl': {'Id': 71, 'ResourceId': '2_faq_2b6d70d8', 'SubResourceIds': [], 'Type': 6,
                              'UserAccesses': [], 'TeamAccesses': [], 'Public': False, 'AdministratorsOnly': True,
                              'System': False}, 'Status': 1, 'ProjectPath': '/data/compose/72',
          'CreationDate': 1682672916, 'CreatedBy': 'dp-admin', 'UpdateDate': 0, 'UpdatedBy': '',
          'AdditionalFiles': None, 'AutoUpdate': None, 'GitConfig': None, 'FromAppTemplate': False, 'Namespace': '',
          'IsComposeFormat': False}]


class ResourceControl(BaseModel):
    Id: int
    ResourceId: str
    SubResourceIds: list  # TODO: add list element type
    Type: int
    UserAccesses: list  # TODO: add list element type
    TeamAccesses: list  # TODO: add list element type
    Public: bool
    AdministratorsOnly: bool
    System: bool


class Stack(BaseModel):
    Id: int
    Name: str
    Type: int
    EndpointId: int
    SwarmId: str
    EntryPoint: str
    Env: Optional[Any]  # TODO: make type more specific
    ResourceControl: ResourceControl
    Status: int
    ProjectPath: str
    CreationDate: int
    CreatedBy: str
    UpdateDate: int
    UpdatedBy: str
    AdditionalFiles: Optional[Any]  # TODO: make type more specific
    AutoUpdate: Optional[Any]  # TODO: make type more specific
    GitConfig: Optional[Any]  # TODO: make type more specific
    FromAppTemplate: bool
    Namespace: str
    IsComposeFormat: bool
