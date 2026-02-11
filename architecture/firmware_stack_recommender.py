"""
Firmware Stack Recommender

Recommends RTOS, middleware, and libraries based on:
- MCU resources (Flash, RAM)
- Required features (TCP/IP, USB, BLE, etc.)
- License preferences
- Architecture compatibility

Catalog includes:
- RTOS: FreeRTOS, Zephyr, ThreadX, embOS, µC/OS-III
- TCP/IP: lwIP, uIP, CycloneTCP
- USB: TinyUSB, STM32 USB Device Library
- Filesystems: FatFs, LittleFS
- Crypto: mbedTLS, WolfSSL
- GUI: LVGL, TouchGFX, emWin
- BLE: NimBLE, Zephyr BLE
"""

import asyncpg
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import uuid


class StackType(Enum):
    """Firmware stack types"""
    RTOS = "rtos"
    TCP_IP = "tcp_ip"
    USB = "usb"
    FILESYSTEM = "filesystem"
    CRYPTO = "crypto"
    GUI = "gui"
    BLE = "ble"
    LIBRARY = "library"


class LicenseType(Enum):
    """License categories"""
    PERMISSIVE = "permissive"  # MIT, BSD, Apache
    COPYLEFT = "copyleft"  # GPL, LGPL
    PROPRIETARY = "proprietary"
    ANY = "any"


@dataclass
class StackRequirement:
    """Stack requirement specification"""
    stack_type: StackType
    required_features: List[str] = None
    required_protocols: List[str] = None
    license_preference: LicenseType = LicenseType.ANY


@dataclass
class StackRecommendation:
    """Recommended firmware stack"""
    stack_id: uuid.UUID
    stack_name: str
    stack_type: str
    vendor: str
    version: str
    license: str
    flash_typical_kb: int
    ram_typical_kb: int
    features: List[str]
    protocols: List[str]
    score: float
    match_reasons: List[str]
    documentation_url: Optional[str]
    repository_url: Optional[str]


class FirmwareStackRecommender:
    """Recommend firmware stacks"""
    
    def __init__(self, db_url: str):
        self.db_url = db_url
    
    async def get_mcu_resources(self, part_id: uuid.UUID) -> Dict[str, int]:
        """Get MCU Flash and RAM"""
        conn = await asyncpg.connect(self.db_url)
        
        try:
            resources = await conn.fetchrow("""
                SELECT m.flash_kb, m.ram_kb, m.core
                FROM mcu_specs m
                WHERE m.part_id = $1
            """, part_id)
            
            if resources:
                return {
                    'flash_kb': resources['flash_kb'],
                    'ram_kb': resources['ram_kb'],
                    'core': resources['core']
                }
            return {}
            
        finally:
            await conn.close()
    
    async def find_stacks(self, stack_type: StackType,
                         max_flash_kb: Optional[int] = None,
                         max_ram_kb: Optional[int] = None,
                         required_features: List[str] = None,
                         required_protocols: List[str] = None,
                         license_preference: LicenseType = LicenseType.ANY,
                         supported_core: Optional[str] = None) -> List[StackRecommendation]:
        """
        Find firmware stacks matching criteria
        """
        conn = await asyncpg.connect(self.db_url)
        
        try:
            # Build query
            query = """
                SELECT * FROM firmware_stacks
                WHERE stack_type = $1
            """
            params = [stack_type.value]
            param_idx = 2
            
            # Resource constraints
            if max_flash_kb:
                query += f" AND flash_typical_kb <= ${param_idx}"
                params.append(max_flash_kb)
                param_idx += 1
            
            if max_ram_kb:
                query += f" AND ram_typical_kb <= ${param_idx}"
                params.append(max_ram_kb)
                param_idx += 1
            
            # Core support
            if supported_core:
                query += f" AND ${param_idx} = ANY(supported_cores)"
                params.append(supported_core)
                param_idx += 1
            
            # License filter
            if license_preference != LicenseType.ANY:
                if license_preference == LicenseType.PERMISSIVE:
                    query += f" AND license IN ('MIT', 'BSD', 'Apache 2.0', 'Apache-2.0')"
                elif license_preference == LicenseType.COPYLEFT:
                    query += f" AND license IN ('GPL', 'LGPL', 'GPLv2', 'GPLv3')"
                elif license_preference == LicenseType.PROPRIETARY:
                    query += f" AND license = 'Proprietary'"
            
            query += " ORDER BY popularity_score DESC, maturity_score DESC"
            
            stacks = await conn.fetch(query, *params)
            
            recommendations = []
            
            for stack in stacks:
                # Calculate match score
                score = 0.0
                match_reasons = []
                
                # Base score from popularity and maturity
                score += (stack['popularity_score'] or 50) * 0.4
                score += (stack['maturity_score'] or 50) * 0.3
                score += (stack['community_score'] or 50) * 0.3
                
                # Feature matching
                stack_features = stack['features'] or []
                if required_features:
                    matched_features = set(required_features) & set(stack_features)
                    if matched_features:
                        score += len(matched_features) * 10
                        match_reasons.append(f"Supports: {', '.join(matched_features)}")
                
                # Protocol matching
                stack_protocols = stack['protocols'] or []
                if required_protocols:
                    matched_protocols = set(required_protocols) & set(stack_protocols)
                    if matched_protocols:
                        score += len(matched_protocols) * 10
                        match_reasons.append(f"Protocols: {', '.join(matched_protocols)}")
                
                # Resource efficiency bonus
                if max_flash_kb and stack['flash_typical_kb']:
                    flash_usage = (stack['flash_typical_kb'] / max_flash_kb) * 100
                    if flash_usage < 50:
                        score += 10
                        match_reasons.append(f"Low Flash usage ({flash_usage:.0f}%)")
                
                if max_ram_kb and stack['ram_typical_kb']:
                    ram_usage = (stack['ram_typical_kb'] / max_ram_kb) * 100
                    if ram_usage < 50:
                        score += 10
                        match_reasons.append(f"Low RAM usage ({ram_usage:.0f}%)")
                
                # License match
                if license_preference != LicenseType.ANY:
                    match_reasons.append(f"License: {stack['license']}")
                
                recommendations.append(StackRecommendation(
                    stack_id=stack['id'],
                    stack_name=stack['stack_name'],
                    stack_type=stack['stack_type'],
                    vendor=stack['vendor'] or 'Community',
                    version=stack['version'] or 'Latest',
                    license=stack['license'] or 'Unknown',
                    flash_typical_kb=stack['flash_typical_kb'] or 0,
                    ram_typical_kb=stack['ram_typical_kb'] or 0,
                    features=stack_features,
                    protocols=stack_protocols,
                    score=score,
                    match_reasons=match_reasons,
                    documentation_url=stack['documentation_url'],
                    repository_url=stack['repository_url']
                ))
            
            # Sort by score
            recommendations.sort(key=lambda x: x.score, reverse=True)
            return recommendations
            
        finally:
            await conn.close()
    
    async def recommend_for_mcu(self, part_id: uuid.UUID,
                                requirements: List[StackRequirement],
                                max_results: int = 5) -> Dict[str, List[StackRecommendation]]:
        """
        Recommend firmware stacks for an MCU
        
        Returns:
            {
                'rtos': [recommendations],
                'tcp_ip': [recommendations],
                ...
            }
        """
        # Get MCU resources
        resources = await self.get_mcu_resources(part_id)
        
        if not resources:
            return {}
        
        # Reserve 30% of Flash and 40% of RAM for application
        available_flash = int(resources['flash_kb'] * 0.7)
        available_ram = int(resources['ram_kb'] * 0.6)
        
        recommendations = {}
        
        for req in requirements:
            stacks = await self.find_stacks(
                stack_type=req.stack_type,
                max_flash_kb=available_flash,
                max_ram_kb=available_ram,
                required_features=req.required_features,
                required_protocols=req.required_protocols,
                license_preference=req.license_preference,
                supported_core=resources.get('core')
            )
            
            recommendations[req.stack_type.value] = stacks[:max_results]
        
        return recommendations
    
    async def add_firmware_stack(self, stack_name: str, stack_type: str,
                                vendor: str, license: str,
                                flash_typical_kb: int, ram_typical_kb: int,
                                supported_cores: List[str],
                                features: List[str] = None,
                                protocols: List[str] = None,
                                documentation_url: str = None,
                                repository_url: str = None) -> uuid.UUID:
        """Add a firmware stack to the database"""
        conn = await asyncpg.connect(self.db_url)
        
        try:
            stack_id = await conn.fetchval("""
                INSERT INTO firmware_stacks (
                    stack_name, stack_type, vendor, license,
                    flash_typical_kb, ram_typical_kb,
                    supported_cores, features, protocols,
                    documentation_url, repository_url,
                    popularity_score, maturity_score, community_score
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                RETURNING id
            """, stack_name, stack_type, vendor, license,
                flash_typical_kb, ram_typical_kb,
                supported_cores, features or [], protocols or [],
                documentation_url, repository_url,
                70, 80, 75)  # Default scores
            
            return stack_id
            
        finally:
            await conn.close()


# Example usage
async def main():
    import os
    
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius")
    recommender = FirmwareStackRecommender(db_url)
    
    # Example: Recommend stacks for an MCU
    # requirements = [
    #     StackRequirement(
    #         stack_type=StackType.RTOS,
    #         required_features=['preemptive', 'tickless'],
    #         license_preference=LicenseType.PERMISSIVE
    #     ),
    #     StackRequirement(
    #         stack_type=StackType.TCP_IP,
    #         required_protocols=['IPv4', 'TCP', 'UDP', 'HTTP']
    #     ),
    #     StackRequirement(
    #         stack_type=StackType.USB,
    #         required_features=['device', 'cdc']
    #     )
    # ]
    # 
    # recommendations = await recommender.recommend_for_mcu(part_id, requirements)
    # 
    # for stack_type, stacks in recommendations.items():
    #     print(f"\n{stack_type.upper()}:")
    #     for stack in stacks:
    #         print(f"  {stack.stack_name} ({stack.vendor})")
    #         print(f"    Flash: {stack.flash_typical_kb}KB, RAM: {stack.ram_typical_kb}KB")
    #         print(f"    Score: {stack.score:.1f}")
    #         print(f"    Reasons: {', '.join(stack.match_reasons)}")


if __name__ == "__main__":
    import asyncio
    import sys
    
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
