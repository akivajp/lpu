#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
  test the module: lpu.common.config
"""

from lpu.common import config
from lpu.common import logging

logger = logging.getColorLogger(__name__)
dprint = logger.debug_print

if __name__ == '__main__':
    dprint(config)
    conf = config.Config()
    dprint(len(conf))
    dprint(conf)
    dprint(conf.to_json())
    conf.data.x = 100
    dprint(conf)
    conf["y"] = list(range(3))
    dprint(conf)
    conf.data["z"] = {}
    dprint(conf)
    dprint(conf.to_json())
    dprint(conf.to_json(indent=2))
    dprint(conf.to_json(indent=2, purge=True))
    conf.data.z.z1 = "Z1"
    dprint(len(conf.data))
    dprint(conf)
    dprint(conf.to_json(indent=2))
    dprint(conf.to_json(indent=2, purge=True))
    dprint(conf["z.z1"])
    dprint(conf.get("z.z1"))
    try:
      dprint(conf["z.z2"])
    except Exception as e:
      logger.exception(e)
    dprint(conf.get("z.z2"))
    conf["d1.d2.d3"] = "DDD"
    dprint(conf.to_json(indent=2))
    conf2 = config.Config(conf)
    dprint(conf2)
    conf2.data.x = 200
    dprint(conf2)
    dprint(conf2.data.x)
    dprint(conf2.to_json(indent=2))
    dprint(conf2.data.y)
    dprint(conf2.to_json(indent=2))
    dprint(conf2.data.z)
    dprint(conf2.to_json(indent=2))
    dprint(conf2.to_json(indent=2, purge=True))
    dprint(conf2.to_json(indent=2, upstream=True))
    conf2.data.z.z2 = "Z2"
    dprint(conf.to_json(indent=2, purge=True))
    dprint(conf2.to_json(indent=2, purge=True))
    logger.info(conf2.to_json(indent=2, upstream=True))
