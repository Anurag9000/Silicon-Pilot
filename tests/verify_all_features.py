
import asyncio
import aiohttp
import logging
import json
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("tests/verify_internal.log", encoding='utf-8', mode='w')
    ]
)
logger = logging.getLogger("MasterVerify")

BASE_URL = "http://localhost:8000"

async def check_endpoint(session, method, endpoint, payload=None, expected_status=200):
    url = f"{BASE_URL}{endpoint}"
    try:
        if method == "GET":
            async with session.get(url) as resp:
                status = resp.status
                data = await resp.json() if status == 200 else None
        elif method == "POST":
            async with session.post(url, json=payload) as resp:
                status = resp.status
                data = await resp.json() if status == 200 else None
        
        if status == expected_status:
            logger.info(f" {method} {endpoint}: Passed")
            return data
        else:
            logger.error(f" {method} {endpoint}: Failed (Status {status})")
            return None
    except Exception as e:
        logger.error(f" {method} {endpoint}: Error ({str(e)})")
        return None

async def verify_component_search(session):
    logger.info("--- 1. Component Search Verification ---")
    
    scenarios = [
        {"type": "MCU", "query": "STM32", "check_field": "core"},
        {"type": "LDO", "query": "LDL1117", "check_field": "ldo_vout"},
        {"type": "PMIC", "query": "STPMIC1", "check_field": "buck_count"},
        {"type": "CAN", "query": "L9616", "check_field": "data_rate"},
        {"type": "Sensor", "query": "LIS2DH12", "check_field": "interface"},
        {"type": "Passive", "query": "Capacitor", "check_field": "value"},
    ]
    
    passed = 0
    for s in scenarios:
        payload = {"query": s["query"], "limit": 1}
        data = await check_endpoint(session, "POST", "/api/search", payload)
        
        if data and data.get("count", 0) > 0:
            result = data["results"][0]
            if result.get("type_label") == s["type"]:
                # Check specific field existence
                if s["check_field"] in result.get("specs", {}):
                     logger.info(f"   -> Confirmed {s['type']} data integrity")
                     passed += 1
                else:
                    logger.warning(f"   -> {s['type']} missing spec field {s['check_field']}")
            else:
                logger.error(f"   -> Expected {s['type']}, got {result.get('type_label')}")
        else:
            logger.warning(f"   -> No results for {s['type']} query '{s['query']}'")
            
    logger.info(f"Search Scope: {passed}/{len(scenarios)} categories verified")

async def verify_solvers(session):
    logger.info("--- 2. Solver Verification ---")
    
    # 1. Fetch a valid MCU for solver tests
    mcu_search = await check_endpoint(session, "POST", "/api/search", {"query": "STM32F4", "limit": 1})
    if not mcu_search or not mcu_search["results"]:
        logger.error(" Skipping Solver tests: No MCU found")
        return

    mcu_data = mcu_search["results"][0]
    part_id = mcu_data["id"]
    logger.info(f"   Using MCU {mcu_data['mpn']} (ID: {part_id}) for solver tests")

    # 2. Pin Mux Solver
    pins = await check_endpoint(session, "GET", f"/api/parts/{part_id}/pins")
    if pins:
        logger.info(f"   -> Fetched {len(pins)} pins")
        
        # Test Solve
        solve_payload = [
            {"function_type": "UART", "function_name": "USART1_TX", "required": True},
            {"function_type": "UART", "function_name": "USART1_RX", "required": True}
        ]
        solve_res = await check_endpoint(session, "POST", f"/api/parts/{part_id}/solve", solve_payload)
        if solve_res:
            assigned = len(solve_res.get("assignments", []))
            logger.info(f"   -> Pin Mux Solved: {assigned} pins assigned")

    # 3. Power Budget
    power_payload = {
        "run_percent": 50.0,
        "sleep_percent": 40.0,
        "stop_percent": 10.0
    }
    power_res = await check_endpoint(session, "POST", f"/api/parts/{part_id}/power", power_payload)
    if power_res:
        logger.info(f"   -> Power Calc: {power_res.get('total_power_uw')} uW")

    # 4. Architecture Builder
    # Needs a template ID. Fetch templates first.
    templates = await check_endpoint(session, "GET", "/api/templates")
    if templates and templates["templates"]:
        template_id = templates["templates"][0]["id"]
        build_payload = {
            "template_id": template_id,
            "answers": {}
        }
        build_res = await check_endpoint(session, "POST", "/api/build-architecture", build_payload)
        if build_res:
             logger.info(f"   -> Architecture Built: {len(build_res.get('bom', []))} items in BOM")
    else:
        logger.warning("   -> No templates found, skipping Architecture Builder")

    # 5. Export
    export_payload = {
        "format": "json",
        "project_name": "TestProject",
        "bom": [{"mpn": mcu_data["mpn"], "qty": 1}]
    }
    await check_endpoint(session, "POST", "/api/export", export_payload, expected_status=200)

async def verify_system_health(session):
    logger.info("--- 3. System Health ---")
    await check_endpoint(session, "GET", "/health")

async def main():
    logger.info("Starting Master Verification...")
    async with aiohttp.ClientSession() as session:
        await verify_system_health(session)
        await verify_component_search(session)
        await verify_solvers(session)
    logger.info("Master Verification Complete.")

if __name__ == "__main__":
    asyncio.run(main())
