"""The register table and the reader that walks it."""

import asyncio

from pyModbusTCP.constants import MB_EXCEPT_ERR
from pyModbusTCP.constants import MB_TIMEOUT_ERR

import thermia_genesis_modbus.const as const
from thermia_genesis_modbus import ThermiaGenesis


def test_every_register_lies_in_a_declared_range():
    """A register outside its model's ranges cannot be placed in a read block."""
    stray = [
        (model, name)
        for name, meta in const.REGISTERS.items()
        for model in (const.MODEL_MEGA, const.MODEL_INVERTER)
        if meta[model]
        and not any(
            low <= meta[const.KEY_ADDRESS] <= high
            for low, high in const.REGISTER_RANGES[model][meta[const.KEY_REG_TYPE]]
        )
    ]
    assert stray == []


def test_no_two_registers_share_an_address():
    seen = {}
    for name, meta in const.REGISTERS.items():
        seen.setdefault((meta[const.KEY_REG_TYPE], meta[const.KEY_ADDRESS]), []).append(
            name
        )
    assert {k: v for k, v in seen.items() if len(v) > 1} == {}


class FakeClient:
    """Answers input registers from a table; refuses or drops chosen blocks."""

    def __init__(self, values, refuse=(), error=MB_EXCEPT_ERR):
        self.values = values
        self.refuse = set(refuse)
        self.error = error
        self._last = 0
        self.reads = []

    def is_open(self):
        return True

    def close(self):
        pass

    def read_input_registers(self, start, length):
        self.reads.append((start, length))
        if start in self.refuse:
            self._last = self.error
            return None
        self._last = 0
        return [self.values.get(start + i, 0) for i in range(length)]

    def last_error(self):
        return self._last

    def last_except_txt(self, verbose=False):
        return "illegal data address"


def pump(client):
    thermia = ThermiaGenesis("192.0.2.10", kind=const.MODEL_MEGA, delay=0)
    thermia._client = client
    return thermia


WANTED = [
    const.ATTR_INPUT_CALCULATED_DEMAND_HEAT,
    const.ATTR_INPUT_CURRENT_POWER_OUTPUT,
    const.ATTR_INPUT_CURRENT_CONSUMED_POWER,
    const.ATTR_INPUT_CONSUMED_ELECTRICAL_ENERGY,
    const.ATTR_INPUT_DELIVERED_HEAT_ENERGY,
    const.ATTR_INPUT_REPORTED_COP,
    const.ATTR_INPUT_ENERGY_FROM_NATURAL_SOURCE,
]
# Raw words as a Calibra returned them: demand -1.01, 4.25 kW out, 1.43 kW in.
RAW = {30: 65435, 157: 425, 158: 143, 331: 16, 332: 67, 333: 42, 334: 53}


def test_power_and_energy_registers_are_scaled():
    data = asyncio.run(pump(FakeClient(RAW)).async_update(only_registers=WANTED))
    assert data == {
        const.ATTR_INPUT_CALCULATED_DEMAND_HEAT: -1.01,
        const.ATTR_INPUT_CURRENT_POWER_OUTPUT: 4.25,
        const.ATTR_INPUT_CURRENT_CONSUMED_POWER: 1.43,
        const.ATTR_INPUT_CONSUMED_ELECTRICAL_ENERGY: 16,
        const.ATTR_INPUT_DELIVERED_HEAT_ENERGY: 67,
        const.ATTR_INPUT_REPORTED_COP: 4.2,
        const.ATTR_INPUT_ENERGY_FROM_NATURAL_SOURCE: 53,
    }


def test_a_refused_block_costs_only_its_own_registers():
    """A pump without the power registers still reports everything else."""
    client = FakeClient(RAW, refuse={157})
    data = asyncio.run(pump(client).async_update(only_registers=WANTED))
    assert const.ATTR_INPUT_CURRENT_POWER_OUTPUT not in data
    assert const.ATTR_INPUT_CURRENT_CONSUMED_POWER not in data
    assert data[const.ATTR_INPUT_CALCULATED_DEMAND_HEAT] == -1.01
    assert data[const.ATTR_INPUT_DELIVERED_HEAT_ENERGY] == 67
    assert (331, 4) in client.reads


def test_a_dead_connection_still_stops_the_read():
    """No answer at all is not a refusal: do not wait out every later block."""
    client = FakeClient(RAW, refuse={157}, error=MB_TIMEOUT_ERR)
    data = asyncio.run(pump(client).async_update(only_registers=WANTED))
    assert const.ATTR_INPUT_DELIVERED_HEAT_ENERGY not in data
    assert (331, 4) not in client.reads
