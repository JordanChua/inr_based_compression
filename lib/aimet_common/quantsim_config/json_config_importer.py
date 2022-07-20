# /usr/bin/env python3.5
# -*- mode: python -*-
# =============================================================================
#  @@-COPYRIGHT-START-@@
#
#  Copyright (c) 2020, Qualcomm Innovation Center, Inc. All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are met:
#
#  1. Redistributions of source code must retain the above copyright notice,
#     this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions and the following disclaimer in the documentation
#     and/or other materials provided with the distribution.
#
#  3. Neither the name of the copyright holder nor the names of its contributors
#     may be used to endorse or promote products derived from this software
#     without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
#  AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
#  IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
#  ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
#  LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
#  CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
#  SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
#  INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
#  CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
#  ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
#  POSSIBILITY OF SUCH DAMAGE.
#
#  SPDX-License-Identifier: BSD-3-Clause
#
#  @@-COPYRIGHT-END-@@
# =============================================================================
""" Utilities for importing and validating json configuration file """

import json
from typing import Dict, List, Union
from jsonschema import validate

from lib.aimet_common.quantsim_config.quantsim_config_schema import QUANTSIM_CONFIG_SCHEMA
from lib.aimet_common.utils import AimetLogger

logger = AimetLogger.get_area_logger(AimetLogger.LogAreas.Quant)

ConfigType = Dict[str, Union[str, bool]]
ParamType = Dict[str, ConfigType]
OpType = Dict[str, Union[str, bool, ParamType]]
OpTypeType = Dict[str, OpType]
SupergroupType = Dict[str, List[str]]
DefaultsType = Dict[str, ConfigType]
ConfigDictType = Dict[str, Union[DefaultsType, ParamType, OpType, List[SupergroupType], ConfigType]]


class ConfigDictKeys:
    """ Class holding variables mapping to strings used in quantsim config dictionary keys """
    DEFAULTS = "defaults"
    PARAMS = "params"
    OP_TYPE = "op_type"
    SUPERGROUPS = "supergroups"
    MODEL_INPUT = "model_input"
    MODEL_OUTPUT = "model_output"
    OPS = "ops"
    OP_LIST = "op_list"
    IS_INPUT_QUANTIZED = "is_input_quantized"
    IS_OUTPUT_QUANTIZED = "is_output_quantized"
    IS_QUANTIZED = "is_quantized"
    IS_SYMMETRIC = "is_symmetric"
    STRICT_SYMMETRIC = "strict_symmetric"
    UNSIGNED_SYMMETRIC = "unsigned_symmetric"


class JsonConfigImporter:
    """ Class for importing and validating json configuration file """

    @classmethod
    def import_json_config_file(cls, config_file: str) -> ConfigDictType:
        """
        Import json config file, run syntax and semantic validation, and return configs as a dictionary
        :param config_file: Config file to parse
        :return: Quantsim configs dictionary
        """
        try:
            with open(config_file) as configs:
                try:
                    quantsim_configs = json.load(configs)
                except json.decoder.JSONDecodeError:
                    logger.error('Error parsing json config file')
                    raise AssertionError
        except IOError:
            logger.error('Could not open json config file')
            raise AssertionError

        _validate_syntax(quantsim_configs)
        _convert_configs_values_to_bool(quantsim_configs)
        _validate_semantics(quantsim_configs)
        return quantsim_configs


def _validate_syntax(quantsim_config: ConfigDictType):
    """
    Validate config dict syntax, ensuring keys and values are as expected.  Throw an exception if anything is amiss.
    :param quantsim_config: Configuration dictionary to validate
    """
    validate(quantsim_config, schema=QUANTSIM_CONFIG_SCHEMA)


def _validate_semantics(quantsim_config: ConfigDictType):
    """
    Validate config dict syntax, ensuring keys and values are as expected.  Throw an exception if anything is amiss.
    :param quantsim_config: Configuration dictionary to validate
    """

    # Currently, for default configs, only IS_OUTPUT_QUANTIZED = True is supported
    default_op_configs = quantsim_config[ConfigDictKeys.DEFAULTS][ConfigDictKeys.OPS]
    if ConfigDictKeys.IS_INPUT_QUANTIZED in default_op_configs:
        logger.error('Currently IS_INPUT_QUANTIZED setting in default configs is not supported')
        raise NotImplementedError
    if ConfigDictKeys.IS_OUTPUT_QUANTIZED in default_op_configs and not \
            default_op_configs[ConfigDictKeys.IS_OUTPUT_QUANTIZED]:
        logger.error('Currently IS_OUTPUT_QUANTIZED false setting in default configs is not supported')
        raise NotImplementedError

    # Currently, for op_type configs, only IS_INPUT_QUANTIZED = True is supported
    op_type_configs = quantsim_config[ConfigDictKeys.OP_TYPE]
    for op_type_config in op_type_configs.values():
        if ConfigDictKeys.IS_INPUT_QUANTIZED in op_type_config and not \
                op_type_config[ConfigDictKeys.IS_INPUT_QUANTIZED]:
            logger.error('IS_INPUT_QUANTIZED false in op configs is currently unsupported.')
            raise NotImplementedError

    # For model input configs, only IS_INPUT_QUANTIZED = True is supported
    model_input_configs = quantsim_config[ConfigDictKeys.MODEL_INPUT]
    if ConfigDictKeys.IS_INPUT_QUANTIZED in model_input_configs:
        if not model_input_configs[ConfigDictKeys.IS_INPUT_QUANTIZED]:
            logger.error('IS_INPUT_QUANTIZED for model input can only be set to True')
            raise NotImplementedError

    # For model output configs, only IS_OUTPUT_QUANTIZED = True is supported
    model_output_configs = quantsim_config[ConfigDictKeys.MODEL_OUTPUT]
    if ConfigDictKeys.IS_OUTPUT_QUANTIZED in model_output_configs:
        if not model_output_configs[ConfigDictKeys.IS_OUTPUT_QUANTIZED]:
            logger.error('IS_OUTPUT_QUANTIZED for model output can only be set to True')
            raise NotImplementedError


def _convert_configs_values_to_bool(dictionary: Dict):
    """
    Recursively traverse all key value pairs in dictionary and set any string values representing booleans to
    booleans.
    :param dictionary: Dictionary to set values to True or False if applicable
    """
    for key, value in dictionary.items():
        if value == 'True':
            dictionary[key] = True
        elif value == 'False':
            dictionary[key] = False
        elif isinstance(value, List):
            for item in value:
                if isinstance(item, Dict):
                    _convert_configs_values_to_bool(item)
        elif isinstance(value, Dict):
            _convert_configs_values_to_bool(value)
        else:
            pass
