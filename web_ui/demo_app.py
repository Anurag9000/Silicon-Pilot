"""
Standalone Web UI for Silicon-Pilot (No Database Required)

Simple demo version that works without database connection.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path
import json

app = FastAPI(title="Silicon-Pilot Demo", version="1.0.0")

# Sample data (would come from database in production)
SAMPLE_TEMPLATES = [
    {
        "id": "can_motor_controller_v1",
        "name": "CAN Motor Controller",
        "device_type": "motor_controller",
        "description": "CAN-based motor controller for BLDC, DC, and stepper motors",
        "tags": ["motor", "can", "bldc", "controller"]
    },
    {
        "id": "iot_sensor_node_v1",
        "name": "IoT Sensor Node",
        "device_type": "sensor_node",
        "description": "Wireless sensor node for environmental monitoring",
        "tags": ["iot", "sensor", "wireless", "battery"]
    },
    {
        "id": "edge_ai_camera_v1",
        "name": "Edge AI Camera",
        "device_type": "edge_ai",
        "description": "Edge AI camera with computer vision and object detection",
        "tags": ["ai", "camera", "computer_vision", "edge"]
    }
]

SAMPLE_BOM = [
    {
        "category": "MCU",
        "manufacturer": "STMicroelectronics",
        "mpn": "STM32F405RGT6",
        "description": "ARM Cortex-M4, 168MHz, 1MB Flash, 192KB RAM",
        "quantity": 1,
        "price_usd": 5.50
    },
    {
        "category": "Power",
        "manufacturer": "Texas Instruments",
        "mpn": "TPS62160",
        "description": "3-17V input, 3.3V/1A output, 95% efficiency",
        "quantity": 1,
        "price_usd": 1.20
    },
    {
        "category": "CAN Transceiver",
        "manufacturer": "Texas Instruments",
        "mpn": "SN65HVD230",
        "description": "3.3V CAN transceiver, 1Mbps",
        "quantity": 1,
        "price_usd": 0.60
    },
    {
        "category": "Protection",
        "manufacturer": "Littelfuse",
        "mpn": "SMBJ24A",
        "description": "24V TVS diode for CAN protection",
        "quantity": 2,
        "price_usd": 0.18
    }
]

@app.get("/", response_class=HTMLResponse)
async def home():
    """Serve the main page"""
    html_file = Path(__file__).parent / "index.html"
    if html_file.exists():
        return HTMLResponse(content=html_file.read_text())
    return HTMLResponse(content=get_inline_html())

@app.post("/api/parse-intent")
async def parse_intent(request: Request):
    """Parse user intent (keyword-based)"""
    data = await request.json()
    user_input = data.get("input", "").lower()
    
    # Simple keyword matching
    matches = []
    for template in SAMPLE_TEMPLATES:
        score = 0
        reasons = []
        
        # Check keywords
        for tag in template["tags"]:
            if tag in user_input:
                score += 20
                reasons.append(f"Keyword match: {tag}")
        
        # Check device type
        if template["device_type"] in user_input:
            score += 30
            reasons.append(f"Device type match")
        
        if score > 0:
            matches.append({
                "template_id": template["id"],
                "confidence": min(score / 100, 1.0),
                "match_reason": ", ".join(reasons) if reasons else "Partial match"
            })
    
    # Sort by confidence
    matches.sort(key=lambda x: x["confidence"], reverse=True)
    
    return {
        "intent": {
            "device_type": "motor_controller" if "motor" in user_input else "unknown",
            "keywords": [word for word in ["motor", "can", "sensor", "iot", "camera"] if word in user_input],
            "extracted_params": {}
        },
        "matches": matches[:5]
    }

@app.get("/api/templates")
async def list_templates():
    """List all templates"""
    return {"templates": SAMPLE_TEMPLATES}

@app.post("/api/build-architecture")
async def build_architecture(request: Request):
    """Build architecture and return BOM"""
    data = await request.json()
    template_id = data.get("template_id")
    
    # Return sample BOM
    return {
        "architecture": {
            "subsystems": ["compute", "power", "communication", "protection"],
            "subsystem_details": {}
        },
        "bom": SAMPLE_BOM,
        "total_cost": sum(item["price_usd"] * item["quantity"] for item in SAMPLE_BOM)
    }

@app.post("/api/export")
async def export_design(request: Request):
    """Export design"""
    data = await request.json()
    format_type = data.get("format", "csv")
    
    # Create simple export
    output_dir = Path(__file__).parent.parent / "exports"
    output_dir.mkdir(exist_ok=True)
    
    filename = f"design_{format_type}.txt"
    filepath = output_dir / filename
    
    # Write simple export
    content = "# Silicon-Pilot Export\n\n"
    content += "## Bill of Materials\n\n"
    for item in SAMPLE_BOM:
        content += f"- {item['mpn']}: {item['description']} (${item['price_usd']})\n"
    
    filepath.write_text(content)
    
    return {
        "success": True,
        "filename": filename,
        "download_url": f"/downloads/{filename}"
    }

@app.get("/downloads/{filename}")
async def download_file(filename: str):
    """Download file"""
    file_path = Path(__file__).parent.parent / "exports" / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, filename=filename)

def get_inline_html():
    """Get inline HTML if file doesn't exist"""
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Silicon-Pilot Demo</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; color: white; margin-bottom: 40px; }
        .header h1 { font-size: 3em; margin-bottom: 10px; }
        .card {
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            margin-bottom: 20px;
        }
        textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 16px;
            margin: 10px 0;
        }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 14px 28px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
        }
        .btn:hover { transform: translateY(-2px); }
        .template-card {
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
            cursor: pointer;
        }
        .template-card:hover { border-color: #667eea; background: #f8f9ff; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #e0e0e0; }
        th { background: #f5f5f5; font-weight: 600; }
        .export-buttons { display: flex; gap: 10px; margin-top: 20px; }
        .export-btn { background: #4caf50; flex: 1; }
        .results { display: none; }
        .results.show { display: block; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1> Silicon-Pilot</h1>
            <p>AI-Powered Hardware Design Assistant (Demo)</p>
        </div>
        
        <div class="card">
            <h2>Describe Your Project</h2>
            <textarea id="user-input" rows="3" placeholder="e.g., I want to build a CAN motor controller for BLDC motors"></textarea>
            <button class="btn" onclick="parseIntent()">Analyze Intent</button>
        </div>
        
        <div class="results" id="results">
            <div class="card">
                <h2>Recommended Templates</h2>
                <div id="templates-list"></div>
            </div>
            
            <div class="card">
                <h2>Bill of Materials</h2>
                <table id="bom-table">
                    <thead>
                        <tr>
                            <th>Category</th>
                            <th>Manufacturer</th>
                            <th>Part Number</th>
                            <th>Qty</th>
                            <th>Price</th>
                        </tr>
                    </thead>
                    <tbody id="bom-tbody"></tbody>
                </table>
                <div class="export-buttons">
                    <button class="btn export-btn" onclick="exportDesign('eagle')">Export Eagle</button>
                    <button class="btn export-btn" onclick="exportDesign('kicad')">Export KiCad</button>
                    <button class="btn export-btn" onclick="exportDesign('pdf')">Export PDF</button>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let currentBOM = [];
        
        async function parseIntent() {
            const input = document.getElementById('user-input').value;
            if (!input.trim()) {
                alert('Please enter a project description');
                return;
            }
            
            try {
                const response = await fetch('/api/parse-intent', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({input})
                });
                
                const data = await response.json();
                displayTemplates(data.matches);
                document.getElementById('results').classList.add('show');
            } catch (error) {
                console.error('Error:', error);
                alert('Error parsing intent');
            }
        }
        
        function displayTemplates(matches) {
            const container = document.getElementById('templates-list');
            if (matches.length === 0) {
                container.innerHTML = '<p>No matching templates found. Try different keywords.</p>';
                return;
            }
            container.innerHTML = matches.map(match => `
                <div class="template-card" onclick="selectTemplate('${match.template_id}')">
                    <h3>${match.template_id}</h3>
                    <p>Confidence: ${(match.confidence * 100).toFixed(0)}%</p>
                    <p>${match.match_reason}</p>
                </div>
            `).join('');
        }
        
        async function selectTemplate(templateId) {
            try {
                const response = await fetch('/api/build-architecture', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({template_id: templateId, answers: {}})
                });
                
                const data = await response.json();
                currentBOM = data.bom;
                displayBOM(data.bom);
            } catch (error) {
                console.error('Error:', error);
                alert('Error building architecture');
            }
        }
        
        function displayBOM(bom) {
            const tbody = document.getElementById('bom-tbody');
            tbody.innerHTML = bom.map(item => `
                <tr>
                    <td>${item.category}</td>
                    <td>${item.manufacturer}</td>
                    <td>${item.mpn}</td>
                    <td>${item.quantity}</td>
                    <td>$${item.price_usd.toFixed(2)}</td>
                </tr>
            `).join('');
        }
        
        async function exportDesign(format) {
            try {
                const response = await fetch('/api/export', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({format, bom: currentBOM, project_name: 'MyDesign'})
                });
                
                const data = await response.json();
                if (data.success) {
                    window.location.href = data.download_url;
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Error exporting design');
            }
        }
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    import uvicorn
    print("=" * 80)
    print("Silicon-Pilot Demo Server Starting...")
    print("=" * 80)
    print()
    print("Access the UI at: http://localhost:8000")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 80)
    uvicorn.run(app, host="0.0.0.0", port=8000)
