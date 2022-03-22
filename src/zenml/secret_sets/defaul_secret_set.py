#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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

from zenml.enums import SecretSetFlavor
from zenml.secret_sets.base_secret_set import BaseSecretSet
# from zenml.secret_sets.secret_set_class_registry import (
#     register_secret_set_class,
# )


# @register_secret_set_class(
#     SecretSetFlavor.DEFAULT,
# )
class DefaultSecretSet(BaseSecretSet):
    @property
    def flavor(self) -> SecretSetFlavor:
        """The secret set flavor."""
        return SecretSetFlavor.DEFAULT
