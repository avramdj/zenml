#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.


from hypothesis import given
from hypothesis.strategies import text

from zenml.enums import SecretsManagerFlavor, StackComponentType
from zenml.io.fileio import file_exists
from zenml.secret.arbitrary_secret_schema import ArbitrarySecretSchema
from zenml.secrets_managers.local.local_secrets_manager import (
    LocalSecretsManager,
)
from zenml.utils import yaml_utils
from zenml.utils.secrets_manager_utils import decode_secret_dict


def test_local_secrets_manager_attributes():
    """Tests that the basic attributes of the local secrets manager are set
    correctly."""
    test_secrets_manager = LocalSecretsManager()
    assert test_secrets_manager.supports_local_execution is True
    assert test_secrets_manager.supports_remote_execution is False
    assert test_secrets_manager.type == StackComponentType.SECRETS_MANAGER
    assert test_secrets_manager.flavor == SecretsManagerFlavor.LOCAL


def test_local_secrets_manager_creates_file():
    """Tests that the initialization of the local secrets manager creates
    a yaml file at the right location."""
    test_secrets_manager = LocalSecretsManager()

    secrets_file = test_secrets_manager.secrets_file
    assert file_exists(secrets_file)


@given(name=text(min_size=1), key=text(min_size=1), value=text(min_size=1))
def test_create_key_value(name: str, key: str, value: str):
    """Tests that the local secrets manager creates a secret."""
    test_secrets_manager = LocalSecretsManager()
    some_secret_name = name
    some_arbitrary_schema = ArbitrarySecretSchema(
        name=some_secret_name, arbitrary_kv_pairs={key: value}
    )

    test_secrets_manager.register_secret(some_arbitrary_schema)

    secret_store_items = yaml_utils.read_yaml(test_secrets_manager.secrets_file)
    encoded_secret = secret_store_items[some_secret_name]
    decoded_secret = decode_secret_dict(encoded_secret)
    assert decoded_secret[key] == value


@given(name=text(min_size=1), key=text(min_size=1), value=text(min_size=1))
def test_fetch_key_value(name: str, key: str, value: str):
    """Tests that a local secrets manager can fetch the right secret value."""
    test_secrets_manager = LocalSecretsManager()
    some_secret_name = name
    some_arbitrary_schema = ArbitrarySecretSchema(
        name=some_secret_name, arbitrary_kv_pairs={key: value}
    )

    test_secrets_manager.register_secret(some_arbitrary_schema)

    fetched_schema = test_secrets_manager.get_secret(some_secret_name)
    assert fetched_schema.content[key] == value


@given(
    name=text(min_size=1),
    new_value=text(min_size=1),
    old_value=text(min_size=1),
)
def test_update_key_value(name: str, old_value: str, new_value: str):
    """Tests that a local secrets manager updates a key's secret value."""
    test_secrets_manager = LocalSecretsManager()
    some_secret_name = name
    some_arbitrary_schema = ArbitrarySecretSchema(
        name=some_secret_name, arbitrary_kv_pairs={"key1": old_value}
    )

    test_secrets_manager.register_secret(some_arbitrary_schema)

    updated_arbitrary_schema = ArbitrarySecretSchema(
        name=some_secret_name, arbitrary_kv_pairs={"key1": new_value}
    )
    test_secrets_manager.update_secret(updated_arbitrary_schema)

    fetched_schema = test_secrets_manager.get_secret(some_secret_name)
    assert fetched_schema.content["key1"] == new_value


@given(name=text(min_size=1), key=text(min_size=1), value=text(min_size=1))
def test_delete_key_value(name: str, key: str, value: str):
    """Tests that a local secret manager deletes a secret."""
    test_secrets_manager = LocalSecretsManager()
    some_secret_name = name
    some_arbitrary_schema = ArbitrarySecretSchema(
        name=some_secret_name, arbitrary_kv_pairs={key: value}
    )

    test_secrets_manager.register_secret(some_arbitrary_schema)
    test_secrets_manager.delete_secret(some_secret_name)

    secret_store_items = yaml_utils.read_yaml(test_secrets_manager.secrets_file)
    assert secret_store_items[some_secret_name] is None
