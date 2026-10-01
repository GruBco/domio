import ipaddress
import platform
from pathlib import Path
from socket import AddressFamily
from typing import List, Dict, Union, Optional

import psutil
from psutil._common import snicaddr, snicstats

from lib.config.errors import ConfigError


def is_linux_physical_interface(interface: str) -> bool:
    symlink_path = str(Path("/sys/class/net").joinpath(interface).resolve())
    return symlink_path.find('virtual') == -1


def is_windows_physical_interface(interface: str) -> bool:
    """Queries WMI for network details to determine if interface is physical
    or virtual.
    """
    import wmi

    c = wmi.WMI()
    query = (f"select NetConnectionID "
             f"from Win32_NetworkAdapter "
             f"where NetEnabled=True "
             f"and NetConnectionStatus=2 "
             f"and AdapterTypeID=0 "
             f"and PhysicalAdapter=True "
             f"and NetConnectionID='{interface}'")

    ncid = [wo.NetConnectionID for wo in c.query(query)]

    return len(ncid) > 0 and interface in ncid


def calculate_broadcast_address(address: snicaddr) -> str:
    """Calculates broadcast address from address and netmask.
    """
    return str(
        ipaddress.ip_network(f"{address.address}/{address.netmask}",
                             strict=False)
        .broadcast_address
    )


def resolve_broadcast_address_for_platforms(address: snicaddr) -> str:
    """Under windows psutil doesn't include broadcast address in snicaddr
    object and needs to be calculated.
    """
    if platform.system() == 'Windows':
        return calculate_broadcast_address(address)
    else:
        return str(address.broadcast)


def create_ipv4_candidate(
    interface: str,
    addresses: List[snicaddr],
    stats: snicstats
) -> Optional[Dict[str, Union[str, int]]]:
    """Gets interface and ipv4 addresses data from specified addresses.

    :param interface: Interface for which to determine information.
    :param addresses: List of addressed grouped by family as received by
    psutil.net_if_addrs.
    :param stats: Stats from interface received by psutil.net_if_stats.
    :return: Dictionary with interface, addr, broadcast and speed values.
    """
    ret = [
        {
            'interface': interface,
            'addr': address.address,
            'broadcast': resolve_broadcast_address_for_platforms(address),
            'speed': stats.speed
        }
        for address in addresses
        if address.family == AddressFamily.AF_INET
    ]
    return ret[0] if ret else None


def get_address_candidates() -> List[Dict[str, str]]:
    """Gets list of candidates sorted by rank (lower is better).

    :return: List of interface name - interface info pairs.
    """
    candidates: List[Dict] = []
    stats = psutil.net_if_stats()

    for ifc, addresses in psutil.net_if_addrs().items():
        ipv4 = create_ipv4_candidate(ifc, addresses, stats.get(ifc))
        if (
            ipv4 and
            ipv4.get('broadcast') and
            # On windows loopback interface has broadcast and needs to be
            # filtered out by ip address.
            ipv4.get('address') != '127.0.0.1'
        ):
            ipv4['rank'] = 1

            if platform.system() == 'Linux':
                if not is_linux_physical_interface(ifc):
                    ipv4['rank'] += 100000
            elif platform.system() == 'Windows':
                if not is_windows_physical_interface(ifc):
                    ipv4['rank'] += 100000

            ipv4['rank'] -= ipv4['speed']

            candidates.append(ipv4)

    return sorted(candidates, key=lambda x: x['rank'])


def resolve_broadcast_address() -> str:
    """Tries to resolve the broadcast address for this machine.

    :return: Resolved ip address or throws ConfigError if no broadcast address
    is found.
    """
    candidate: Optional[str] = None

    candidates = get_address_candidates()

    if len(candidates) != 0:
        candidate = candidates[0]['broadcast']

    if candidate:
        return candidate
    else:
        raise ConfigError("Failed to automatically resolve broadcast address")
