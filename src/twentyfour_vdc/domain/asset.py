from dataclasses import dataclass


@dataclass
class Asset:
    building: str
    room: str
    hostname: str
    ip_address: str
    mac_address: str
