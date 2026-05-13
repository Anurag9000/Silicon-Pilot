"""
Enhanced Export Features for Silicon-Pilot

Exports BOM and configuration to various CAD and firmware tools:
- Eagle XML
- KiCad CSV
- Altium CSV
- STM32CubeMX .ioc file
- PDF report
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime
import xml.etree.ElementTree as ET
import csv
import io


# ============================================================================
# Eagle XML Export
# ============================================================================

class EagleExporter:
    """Export BOM to Eagle XML format"""
    
    def export(self, bom: List[Dict[str, Any]], project_name: str) -> str:
        """Generate Eagle XML BOM"""
        root = ET.Element("export", version="1.0")
        
        # Design info
        design = ET.SubElement(root, "design")
        ET.SubElement(design, "name").text = project_name
        ET.SubElement(design, "date").text = datetime.now().isoformat()
        
        # Components
        components = ET.SubElement(root, "components")
        
        for idx, item in enumerate(bom, 1):
            comp = ET.SubElement(components, "comp", ref=f"U{idx}")
            ET.SubElement(comp, "value").text = item.get("mpn", "")
            ET.SubElement(comp, "footprint").text = item.get("package", "")
            ET.SubElement(comp, "datasheet").text = item.get("datasheet_url", "")
            ET.SubElement(comp, "description").text = item.get("description", "")
            
            # Fields
            fields = ET.SubElement(comp, "fields")
            ET.SubElement(fields, "field", name="Manufacturer").text = item.get("manufacturer", "")
            ET.SubElement(fields, "field", name="MPN").text = item.get("mpn", "")
            ET.SubElement(fields, "field", name="Price").text = f"${item.get('price_usd', 0):.2f}"
        
        # Convert to string
        tree = ET.ElementTree(root)
        output = io.StringIO()
        tree.write(output, encoding="unicode", xml_declaration=True)
        return output.getvalue()


# ============================================================================
# KiCad CSV Export
# ============================================================================

class KiCadExporter:
    """Export BOM to KiCad CSV format"""
    
    def export(self, bom: List[Dict[str, Any]]) -> str:
        """Generate KiCad CSV BOM"""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "Ref",
            "Qnty",
            "Value",
            "Cmp name",
            "Footprint",
            "Description",
            "Vendor",
            "DNP"
        ])
        
        # Components
        for idx, item in enumerate(bom, 1):
            writer.writerow([
                f"U{idx}",
                item.get("quantity", 1),
                item.get("mpn", ""),
                item.get("category", ""),
                item.get("package", ""),
                item.get("description", ""),
                item.get("manufacturer", ""),
                ""  # DNP (Do Not Place)
            ])
        
        return output.getvalue()


# ============================================================================
# Altium CSV Export
# ============================================================================

class AltiumExporter:
    """Export BOM to Altium CSV format"""
    
    def export(self, bom: List[Dict[str, Any]]) -> str:
        """Generate Altium CSV BOM"""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "Designator",
            "Comment",
            "Description",
            "Footprint",
            "LibRef",
            "Quantity",
            "Manufacturer",
            "Manufacturer Part Number",
            "Supplier",
            "Supplier Part Number",
            "Cost"
        ])
        
        # Components
        for idx, item in enumerate(bom, 1):
            writer.writerow([
                f"U{idx}",
                item.get("mpn", ""),
                item.get("description", ""),
                item.get("package", ""),
                item.get("category", ""),
                item.get("quantity", 1),
                item.get("manufacturer", ""),
                item.get("mpn", ""),
                "",  # Supplier
                "",  # Supplier PN
                f"${item.get('price_usd', 0):.2f}"
            ])
        
        return output.getvalue()


# ============================================================================
# STM32CubeMX .ioc Export
# ============================================================================

class STM32CubeMXExporter:
    """Export configuration to STM32CubeMX .ioc file"""
    
    def export(self, config: Dict[str, Any], mcu_mpn: str) -> str:
        """Generate STM32CubeMX .ioc file"""
        lines = []
        
        # Header
        lines.append("#MicroXplorer Configuration settings - do not modify")
        lines.append(f"File.Version=6")
        lines.append(f"KeepUserPlacement=false")
        lines.append(f"Mcu.Family=STM32F4")
        lines.append(f"Mcu.IP0=NVIC")
        lines.append(f"Mcu.IP1=RCC")
        lines.append(f"Mcu.IPNb=2")
        lines.append(f"Mcu.Name={mcu_mpn}")
        lines.append(f"Mcu.Package={config.get('package', 'LQFP64')}")
        lines.append(f"Mcu.Pin0=PH0-OSC_IN")
        lines.append(f"Mcu.Pin1=PH1-OSC_OUT")
        lines.append(f"Mcu.PinsNb=2")
        lines.append(f"Mcu.ThirdPartyNb=0")
        lines.append(f"Mcu.UserConstants=")
        lines.append(f"Mcu.UserName={mcu_mpn}")
        
        # RCC (Clock configuration)
        if "clock" in config:
            clock = config["clock"]
            lines.append(f"RCC.AHBFreq_Value={clock.get('ahb_mhz', 168)}000000")
            lines.append(f"RCC.APB1Freq_Value={clock.get('apb1_mhz', 42)}000000")
            lines.append(f"RCC.APB2Freq_Value={clock.get('apb2_mhz', 84)}000000")
            lines.append(f"RCC.HSE_VALUE={clock.get('hse_mhz', 8)}000000")
            lines.append(f"RCC.PLLSourceVirtual=RCC_PLLSOURCE_HSE")
            lines.append(f"RCC.SYSCLKFreq_VALUE={clock.get('sysclk_mhz', 168)}000000")
        
        # Pin configuration
        if "pins" in config:
            for pin_name, pin_config in config["pins"].items():
                lines.append(f"{pin_name}.Mode={pin_config.get('mode', 'GPIO_Output')}")
                lines.append(f"{pin_name}.Signal={pin_config.get('signal', 'GPIO_Output')}")
        
        # Peripherals
        if "peripherals" in config:
            for peripheral, peripheral_config in config["peripherals"].items():
                lines.append(f"{peripheral}.IPParameters={','.join(peripheral_config.keys())}")
                for key, value in peripheral_config.items():
                    lines.append(f"{peripheral}.{key}={value}")
        
        lines.append("ProjectManager.ProjectName=Silicon-Pilot_Generated")
        lines.append("ProjectManager.TargetToolchain=STM32CubeIDE")
        
        return "\n".join(lines)


# ============================================================================
# PDF Report Generator
# ============================================================================

class PDFReportGenerator:
    """Generate PDF report (requires reportlab)"""
    
    def export(self, bom: List[Dict[str, Any]], config: Dict[str, Any], project_name: str) -> bytes:
        """Generate PDF report"""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib import colors
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            import io
            
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()
            
            # Title
            story.append(Paragraph(f"<b>{project_name}</b>", styles['Title']))
            story.append(Spacer(1, 0.2*inch))
            
            # BOM Table
            story.append(Paragraph("<b>Bill of Materials</b>", styles['Heading2']))
            story.append(Spacer(1, 0.1*inch))
            
            bom_data = [["#", "Category", "Manufacturer", "MPN", "Qty", "Price"]]
            for idx, item in enumerate(bom, 1):
                bom_data.append([
                    str(idx),
                    item.get("category", ""),
                    item.get("manufacturer", ""),
                    item.get("mpn", ""),
                    str(item.get("quantity", 1)),
                    f"${item.get('price_usd', 0):.2f}"
                ])
            
            bom_table = Table(bom_data)
            bom_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(bom_table)
            story.append(Spacer(1, 0.3*inch))
            
            # Configuration Notes
            if config:
                story.append(Paragraph("<b>Configuration Notes</b>", styles['Heading2']))
                story.append(Spacer(1, 0.1*inch))
                
                for section, content in config.items():
                    story.append(Paragraph(f"<b>{section}</b>", styles['Heading3']))
                    if isinstance(content, dict):
                        for key, value in content.items():
                            story.append(Paragraph(f"{key}: {value}", styles['Normal']))
                    else:
                        story.append(Paragraph(str(content), styles['Normal']))
                    story.append(Spacer(1, 0.1*inch))
            
            doc.build(story)
            return buffer.getvalue()
        
        except ImportError:
            # Fallback to text-based report if reportlab not available
            return self._export_text_report(bom, config, project_name).encode('utf-8')
    
    def _export_text_report(self, bom: List[Dict[str, Any]], config: Dict[str, Any], project_name: str) -> str:
        """Fallback text-based report"""
        lines = []
        lines.append(f"=" * 80)
        lines.append(f"{project_name}")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"=" * 80)
        lines.append("")
        
        lines.append("BILL OF MATERIALS")
        lines.append("-" * 80)
        for idx, item in enumerate(bom, 1):
            lines.append(f"{idx}. {item.get('category', 'Component')}")
            lines.append(f"   Manufacturer: {item.get('manufacturer', 'N/A')}")
            lines.append(f"   MPN: {item.get('mpn', 'N/A')}")
            lines.append(f"   Quantity: {item.get('quantity', 1)}")
            lines.append(f"   Price: ${item.get('price_usd', 0):.2f}")
            lines.append("")
        
        if config:
            lines.append("CONFIGURATION NOTES")
            lines.append("-" * 80)
            for section, content in config.items():
                lines.append(f"\n{section.upper()}")
                if isinstance(content, dict):
                    for key, value in content.items():
                        lines.append(f"  {key}: {value}")
                else:
                    lines.append(f"  {content}")
        
        return "\n".join(lines)


# ============================================================================
# Export Manager
# ============================================================================

class ExportManager:
    """Manage all export formats"""
    
    def __init__(self):
        self.eagle = EagleExporter()
        self.kicad = KiCadExporter()
        self.altium = AltiumExporter()
        self.cubemx = STM32CubeMXExporter()
        self.pdf = PDFReportGenerator()
    
    def export_all(self, bom: List[Dict[str, Any]], config: Dict[str, Any], 
                   project_name: str, output_dir: str = "."):
        """Export to all formats"""
        import os
        
        # Eagle XML
        eagle_xml = self.eagle.export(bom, project_name)
        with open(os.path.join(output_dir, f"{project_name}_eagle.xml"), "w") as f:
            f.write(eagle_xml)
        
        # KiCad CSV
        kicad_csv = self.kicad.export(bom)
        with open(os.path.join(output_dir, f"{project_name}_kicad.csv"), "w") as f:
            f.write(kicad_csv)
        
        # Altium CSV
        altium_csv = self.altium.export(bom)
        with open(os.path.join(output_dir, f"{project_name}_altium.csv"), "w") as f:
            f.write(altium_csv)
        
        # STM32CubeMX (if MCU is STM32)
        mcu = next((item for item in bom if item.get("category") == "MCU"), None)
        if mcu and "STM32" in mcu.get("mpn", ""):
            cubemx_ioc = self.cubemx.export(config, mcu["mpn"])
            with open(os.path.join(output_dir, f"{project_name}.ioc"), "w") as f:
                f.write(cubemx_ioc)
        
        # PDF Report
        pdf_bytes = self.pdf.export(bom, config, project_name)
        with open(os.path.join(output_dir, f"{project_name}_report.pdf"), "wb") as f:
            f.write(pdf_bytes)
        
        print(f"✓ Exported to {output_dir}/")
        print(f"  - {project_name}_eagle.xml")
        print(f"  - {project_name}_kicad.csv")
        print(f"  - {project_name}_altium.csv")
        if mcu and "STM32" in mcu.get("mpn", ""):
            print(f"  - {project_name}.ioc")
        print(f"  - {project_name}_report.pdf")


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    # Sample BOM
    sample_bom = [
        {
            "category": "MCU",
            "manufacturer": "STMicroelectronics",
            "mpn": "STM32F405RGT6",
            "package": "LQFP-64",
            "quantity": 1,
            "price_usd": 5.50,
            "description": "ARM Cortex-M4 MCU, 168MHz, 1MB Flash"
        },
        {
            "category": "Power",
            "manufacturer": "Texas Instruments",
            "mpn": "TPS62160",
            "package": "SOT-23-6",
            "quantity": 1,
            "price_usd": 1.20,
            "description": "Buck converter, 3-17V input, 1A output"
        }
    ]
    
    # Sample config
    sample_config = {
        "clock": {
            "hse_mhz": 8,
            "sysclk_mhz": 168,
            "ahb_mhz": 168,
            "apb1_mhz": 42,
            "apb2_mhz": 84
        },
        "pins": {
            "PA8": {"mode": "TIM1_CH1", "signal": "PWM"},
            "PB8": {"mode": "CAN1_RX", "signal": "CAN"},
            "PB9": {"mode": "CAN1_TX", "signal": "CAN"}
        }
    }
    
    # Export
    manager = ExportManager()
    manager.export_all(sample_bom, sample_config, "MotorController_v1", "./exports")
