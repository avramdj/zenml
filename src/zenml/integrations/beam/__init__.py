#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
from zenml.integrations.integration import Integration
from zenml.utils.source_utils import import_class_by_path


from zenml.integrations.constants import BEAM
class BeamIntegration(Integration):
    NAME = BEAM
    REQUIREMENTS = ["apache-beam"]

    @classmethod
    def activate(cls):
        import_class_by_path(
            "zenml.integrations.beam.materializers.beam_materializer.BeamMaterializer"
        )


BeamIntegration.check_installation()
