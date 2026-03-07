'''
Function:
    Implementation of RandomIPGenerator
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import random
import requests
import ipaddress
from bisect import bisect
from typing import List, Optional, Sequence


'''RandomIPGenerator'''
class RandomIPGenerator:
    def __init__(self, default_ipv4_prefixes: Optional[Sequence[str]] = None, default_ipv6_prefixes: Optional[Sequence[str]] = None, max_attempts: int = 10000):
        self.max_attempts = max_attempts
        self.default_ipv4_prefixes: List[str] = list(default_ipv4_prefixes or [])
        self.default_ipv6_prefixes: List[str] = list(default_ipv6_prefixes or [])
    '''ipv4'''
    def ipv4(self, prefix: Optional[str] = None) -> str:
        if prefix is None and self.default_ipv4_prefixes:
            prefix = random.choice(self.default_ipv4_prefixes)
        if prefix is not None:
            return self._randomipv4inprefix(prefix)
        else:
            return self._randomglobalipv4()
    '''ipv6'''
    def ipv6(self, prefix: Optional[str] = None) -> str:
        if prefix is None and self.default_ipv6_prefixes:
            prefix = random.choice(self.default_ipv6_prefixes)
        if prefix is not None:
            return self._randomipv6inprefix(prefix)
        else:
            return self._randomglobalipv6()
    '''randomipv4scn'''
    def randomipv4scn(self, num_samples: int = 1) -> List[str]:
        def buildsampler_func(blocks):
            cum, s = [], 0
            for _, c in blocks: s += c; cum.append(s)
            total = s
            def sample(n=10):
                out = []
                for _ in range(n):
                    r = random.randrange(total)
                    idx = bisect(cum, r)
                    base, count = blocks[idx]
                    ip = ipaddress.IPv4Address(base + random.randrange(count))
                    out.append(str(ip))
                return out
            return sample
        blocks = self._loadcnipv4blocks()
        sampler = buildsampler_func(blocks)
        return sampler(num_samples)
    '''addrandomipv4toheaders'''
    def addrandomipv4toheaders(self, headers: dict = None, prefix: Optional[str] = None) -> dict:
        assert isinstance(headers, dict), f'input "headers" should be "dict", but get {type(headers)}'
        random_ip = self.ipv4(prefix=prefix)
        headers.update({
            "X-Forwarded-For": random_ip, "X-Real-IP": random_ip, "Forwarded": f"for={random_ip};proto=https",
        })
        return headers
    '''_loadcnipv4blocks'''
    def _loadcnipv4blocks(self):
        text = requests.get("https://ftp.apnic.net/stats/apnic/delegated-apnic-extended-latest", timeout=30).text.splitlines()
        blocks = []
        for line in text:
            if not line or line.startswith("#"): continue
            parts = line.strip().split("|")
            if len(parts) < 7: continue
            _, cc, rtype, start, value, _, status = parts[:7]
            if cc != "CN" or rtype != "ipv4": continue
            if status not in ("allocated", "assigned"): continue
            base = int(ipaddress.IPv4Address(start))
            count = int(value)
            if count > 0: blocks.append((base, count))
        if not blocks: raise RuntimeError("No CN IPv4 blocks found. Check APNIC file format/URL.")
        return blocks
    '''_randomipv4inprefix'''
    def _randomipv4inprefix(self, prefix: str) -> str:
        net = ipaddress.IPv4Network(prefix, strict=False)
        if net.prefixlen <= 30:
            network_int = int(net.network_address)
            broadcast_int = int(net.broadcast_address)
            if broadcast_int - network_int <= 2: candidate_int = random.randint(network_int, broadcast_int)
            else: candidate_int = random.randint(network_int + 1, broadcast_int - 1)
        else:
            offset = random.randrange(net.num_addresses)
            candidate_int = int(net.network_address) + offset
        addr = ipaddress.IPv4Address(candidate_int)
        return str(addr)
    '''_randomglobalipv4'''
    def _randomglobalipv4(self) -> str:
        attempts = 0
        while attempts < self.max_attempts:
            attempts += 1
            candidate_int = random.getrandbits(32)
            addr = ipaddress.IPv4Address(candidate_int)
            if addr.is_global: return str(addr)
        return str(addr)
    '''_randomipv6inprefix'''
    def _randomipv6inprefix(self, prefix: str) -> str:
        net = ipaddress.IPv6Network(prefix, strict=False)
        host_bits = 128 - net.prefixlen
        rand_host = random.getrandbits(host_bits)
        addr_int = int(net.network_address) + rand_host
        addr = ipaddress.IPv6Address(addr_int)
        return str(addr)
    '''_randomglobalipv6'''
    def _randomglobalipv6(self) -> str:
        attempts = 0
        while attempts < self.max_attempts:
            attempts += 1
            candidate_int = random.getrandbits(128)
            addr = ipaddress.IPv6Address(candidate_int)
            if addr.is_global: return str(addr)
        return str(addr)