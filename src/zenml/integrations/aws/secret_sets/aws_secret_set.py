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
from typing import Optional

from pydantic import BaseModel

from zenml.enums import SecretSetFlavor
# from zenml.secret_sets.secret_set_class_registry import (
#     register_secret_set_class,
# )


# @register_secret_set_class(
#     SecretSetFlavor.AWS,
# )
class AWSSecretSet(BaseModel):

    id: str
    value: str
    token: Optional[str]

    @property
    def flavor(self) -> SecretSetFlavor:
        """The secret set flavor."""
        return SecretSetFlavor.AWS
