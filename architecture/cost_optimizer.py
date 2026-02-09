"""
Cost Optimization Engine

Implements multi-objective optimization for BOM cost reduction:
- Alternative component suggestions
- Volume pricing calculations
- Multi-vendor comparison
- Total cost of ownership analysis
"""

from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel
from dataclasses import dataclass
import asyncio


# ============================================================================
# Cost Models
# ============================================================================

@dataclass
class PricingTier:
    """Volume pricing tier"""
    min_quantity: int
    unit_price: float


@dataclass
class ComponentCost:
    """Component cost breakdown"""
    mpn: str
    manufacturer: str
    unit_price: float
    quantity: int
    extended_price: float
    pricing_tiers: List[PricingTier]
    availability: int
    lead_time_days: int


@dataclass
class BOMCostAnalysis:
    """Complete BOM cost analysis"""
    total_cost: float
    component_count: int
    unique_parts: int
    cost_breakdown: Dict[str, float]
    optimization_opportunities: List[str]
    alternative_boms: List[Dict[str, Any]]


# ============================================================================
# Cost Optimizer
# ============================================================================

class CostOptimizer:
    """Multi-objective BOM cost optimization"""
    
    def __init__(self):
        self.pricing_cache = {}
    
    async def optimize_bom(self, bom: List[Dict[str, Any]], 
                          target_quantity: int = 100) -> BOMCostAnalysis:
        """Optimize BOM for cost"""
        
        # Calculate baseline cost
        baseline_cost = sum(
            item.get("price_usd", 0) * item.get("quantity", 1) 
            for item in bom
        )
        
        # Find optimization opportunities
        opportunities = []
        alternative_boms = []
        
        # 1. Volume pricing optimization
        volume_savings = self._calculate_volume_savings(bom, target_quantity)
        if volume_savings > 0:
            opportunities.append(
                f"Volume pricing: Save ${volume_savings:.2f} at {target_quantity} units"
            )
        
        # 2. Alternative component suggestions
        for item in bom:
            alternatives = await self._find_cheaper_alternatives(item)
            if alternatives:
                cheapest = alternatives[0]
                savings = (item.get("price_usd", 0) - cheapest["price_usd"]) * item.get("quantity", 1)
                if savings > 0.10:  # Only suggest if savings > $0.10
                    opportunities.append(
                        f"Replace {item['mpn']} with {cheapest['mpn']}: Save ${savings:.2f}"
                    )
                    
                    # Create alternative BOM
                    alt_bom = bom.copy()
                    alt_bom[bom.index(item)] = cheapest
                    alt_cost = sum(
                        i.get("price_usd", 0) * i.get("quantity", 1) 
                        for i in alt_bom
                    )
                    alternative_boms.append({
                        "description": f"Lower cost ({cheapest['mpn']} instead of {item['mpn']})",
                        "bom": alt_bom,
                        "total_cost": alt_cost,
                        "savings": baseline_cost - alt_cost
                    })
        
        # 3. Multi-vendor optimization
        vendor_savings = self._optimize_vendor_selection(bom)
        if vendor_savings > 0:
            opportunities.append(
                f"Multi-vendor sourcing: Save ${vendor_savings:.2f}"
            )
        
        # Cost breakdown by category
        cost_breakdown = {}
        for item in bom:
            category = item.get("category", "Other")
            cost = item.get("price_usd", 0) * item.get("quantity", 1)
            cost_breakdown[category] = cost_breakdown.get(category, 0) + cost
        
        return BOMCostAnalysis(
            total_cost=baseline_cost,
            component_count=sum(item.get("quantity", 1) for item in bom),
            unique_parts=len(bom),
            cost_breakdown=cost_breakdown,
            optimization_opportunities=opportunities,
            alternative_boms=sorted(alternative_boms, key=lambda x: x["savings"], reverse=True)
        )
    
    def _calculate_volume_savings(self, bom: List[Dict[str, Any]], 
                                  quantity: int) -> float:
        """Calculate savings from volume pricing"""
        # Simplified - would use real pricing tiers
        if quantity >= 1000:
            return sum(item.get("price_usd", 0) * 0.15 for item in bom)  # 15% discount
        elif quantity >= 100:
            return sum(item.get("price_usd", 0) * 0.10 for item in bom)  # 10% discount
        return 0
    
    async def _find_cheaper_alternatives(self, component: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find cheaper alternative components"""
        # Simplified - would query database for alternatives
        category = component.get("category", "")
        current_price = component.get("price_usd", 0)
        
        # Sample alternatives (would query real database)
        if category == "MCU" and current_price > 5.0:
            return [{
                **component,
                "mpn": "STM32F103RBT6",
                "price_usd": 3.50,
                "description": "Lower-cost alternative (Cortex-M3, 128KB Flash)"
            }]
        elif category == "Buck Converter" and current_price > 1.0:
            return [{
                **component,
                "mpn": "LM3671",
                "price_usd": 0.80,
                "description": "Lower-cost alternative (600mA output)"
            }]
        
        return []
    
    def _optimize_vendor_selection(self, bom: List[Dict[str, Any]]) -> float:
        """Optimize vendor selection for shipping/MOQ"""
        # Simplified - would use real vendor data
        return 0.50  # Sample savings from vendor optimization


# ============================================================================
# Total Cost of Ownership (TCO) Calculator
# ============================================================================

class TCOCalculator:
    """Calculate total cost of ownership"""
    
    def calculate_tco(self, bom: List[Dict[str, Any]], 
                     production_volume: int,
                     product_lifetime_years: int = 5) -> Dict[str, Any]:
        """Calculate TCO including NRE, production, and lifecycle costs"""
        
        # BOM cost
        unit_bom_cost = sum(
            item.get("price_usd", 0) * item.get("quantity", 1) 
            for item in bom
        )
        
        # NRE (Non-Recurring Engineering) costs
        nre_costs = {
            "pcb_design": 5000,  # PCB design
            "prototypes": 2000,  # Prototype builds
            "testing": 3000,     # Testing and validation
            "certification": 5000,  # Certifications (FCC, CE, etc.)
            "tooling": 1000      # Assembly tooling
        }
        total_nre = sum(nre_costs.values())
        
        # Production costs
        assembly_cost_per_unit = 2.50  # SMT assembly
        total_production_cost = (unit_bom_cost + assembly_cost_per_unit) * production_volume
        
        # Lifecycle costs
        obsolescence_risk = self._calculate_obsolescence_risk(bom)
        support_cost = production_volume * 0.50  # Support cost per unit
        
        # Total TCO
        total_tco = total_nre + total_production_cost + support_cost
        tco_per_unit = total_tco / production_volume
        
        return {
            "nre_costs": nre_costs,
            "total_nre": total_nre,
            "unit_bom_cost": unit_bom_cost,
            "assembly_cost_per_unit": assembly_cost_per_unit,
            "total_production_cost": total_production_cost,
            "support_cost": support_cost,
            "total_tco": total_tco,
            "tco_per_unit": tco_per_unit,
            "obsolescence_risk": obsolescence_risk,
            "production_volume": production_volume,
            "product_lifetime_years": product_lifetime_years
        }
    
    def _calculate_obsolescence_risk(self, bom: List[Dict[str, Any]]) -> str:
        """Calculate component obsolescence risk"""
        # Simplified - would check actual lifecycle status
        nrnd_count = sum(1 for item in bom if item.get("status") == "nrnd")
        if nrnd_count > 0:
            return "HIGH"
        return "LOW"


# ============================================================================
# Multi-Vendor Comparison
# ============================================================================

class VendorComparator:
    """Compare pricing across multiple vendors"""
    
    def __init__(self):
        self.vendors = ["Digi-Key", "Mouser", "Arrow", "Avnet"]
    
    async def compare_vendors(self, mpn: str) -> Dict[str, Any]:
        """Compare pricing across vendors"""
        # Would integrate with real vendor APIs
        
        # Sample data
        vendor_prices = {
            "Digi-Key": {"price": 5.50, "stock": 1000, "lead_time": 0},
            "Mouser": {"price": 5.45, "stock": 500, "lead_time": 0},
            "Arrow": {"price": 5.30, "stock": 200, "lead_time": 2},
            "Avnet": {"price": 5.60, "stock": 5000, "lead_time": 0}
        }
        
        best_price = min(vendor_prices.items(), key=lambda x: x[1]["price"])
        best_availability = max(vendor_prices.items(), key=lambda x: x[1]["stock"])
        
        return {
            "mpn": mpn,
            "vendor_prices": vendor_prices,
            "best_price": best_price,
            "best_availability": best_availability,
            "recommendation": best_price[0] if best_price[1]["stock"] > 0 else best_availability[0]
        }


# ============================================================================
# Example Usage
# ============================================================================

async def main():
    """Demonstrate cost optimization"""
    
    # Sample BOM
    sample_bom = [
        {
            "category": "MCU",
            "manufacturer": "STMicroelectronics",
            "mpn": "STM32F405RGT6",
            "quantity": 1,
            "price_usd": 5.50,
            "status": "active"
        },
        {
            "category": "Buck Converter",
            "manufacturer": "Texas Instruments",
            "mpn": "TPS62160",
            "quantity": 1,
            "price_usd": 1.20,
            "status": "active"
        },
        {
            "category": "CAN Transceiver",
            "manufacturer": "Texas Instruments",
            "mpn": "SN65HVD230",
            "quantity": 1,
            "price_usd": 0.60,
            "status": "active"
        }
    ]
    
    # Cost optimization
    optimizer = CostOptimizer()
    analysis = await optimizer.optimize_bom(sample_bom, target_quantity=100)
    
    print("=" * 80)
    print("BOM Cost Analysis")
    print("=" * 80)
    print(f"Total Cost: ${analysis.total_cost:.2f}")
    print(f"Component Count: {analysis.component_count}")
    print(f"Unique Parts: {analysis.unique_parts}")
    print()
    
    print("Cost Breakdown:")
    for category, cost in analysis.cost_breakdown.items():
        print(f"  {category}: ${cost:.2f}")
    print()
    
    print("Optimization Opportunities:")
    for opp in analysis.optimization_opportunities:
        print(f"  • {opp}")
    print()
    
    if analysis.alternative_boms:
        print("Alternative BOMs:")
        for alt in analysis.alternative_boms[:3]:
            print(f"  • {alt['description']}: ${alt['total_cost']:.2f} (save ${alt['savings']:.2f})")
    print()
    
    # TCO calculation
    tco_calc = TCOCalculator()
    tco = tco_calc.calculate_tco(sample_bom, production_volume=1000)
    
    print("=" * 80)
    print("Total Cost of Ownership (1000 units)")
    print("=" * 80)
    print(f"NRE Costs: ${tco['total_nre']:,.2f}")
    print(f"Production Cost: ${tco['total_production_cost']:,.2f}")
    print(f"Support Cost: ${tco['support_cost']:,.2f}")
    print(f"Total TCO: ${tco['total_tco']:,.2f}")
    print(f"TCO per Unit: ${tco['tco_per_unit']:.2f}")
    print(f"Obsolescence Risk: {tco['obsolescence_risk']}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
