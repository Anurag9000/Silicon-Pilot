# HardwareGenius API Documentation

## Overview
HardwareGenius provides a comprehensive API for hardware component selection, design validation, and optimization.

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication
Currently no authentication required. Future versions will support API keys.

---

## Endpoints

### 1. Search Components

**POST** `/search`

Search for components by text query.

**Request Body**:
```json
{
  "query": "STM32F4 high performance",
  "category": "mcu",
  "limit": 10
}
```

**Response**:
```json
{
  "results": [
    {
      "id": "uuid",
      "mpn": "STM32F407VGT6",
      "manufacturer": "STMicroelectronics",
      "category": "mcu",
      "specs": {
        "flash_kb": 1024,
        "ram_kb": 192,
        "max_freq_mhz": 168
      },
      "score": 95.5
    }
  ],
  "total": 42
}
```

---

### 2. Get Alternatives

**GET** `/parts/{part_id}/alternatives`

Find alternative parts (pin-compatible, functionally equivalent, cost-optimized).

**Query Parameters**:
- `max_results` (int): Maximum number of alternatives (default: 5)
- `type` (string): Alternative type filter (`pin_compatible`, `functionally_equivalent`, `cost_optimized`)

**Response**:
```json
{
  "alternatives": [
    {
      "part_id": "uuid",
      "mpn": "STM32F405RGT6",
      "manufacturer": "STMicroelectronics",
      "alternative_type": "pin_compatible",
      "score": 98.0,
      "match_reasons": ["Pin-compatible", "+128KB Flash"],
      "cost_difference_percent": -5.2
    }
  ]
}
```

---

### 3. Design Rule Check

**POST** `/design/check`

Validate design against 50+ rules.

**Request Body**:
```json
{
  "design_parts": ["uuid1", "uuid2"],
  "pmic_id": "uuid3",
  "required_flash_kb": 512,
  "required_ram_kb": 128,
  "target_freq_mhz": 168,
  "ambient_temp_c": 25
}
```

**Response**:
```json
{
  "success": true,
  "summary": {
    "total": 5,
    "errors": 0,
    "warnings": 3,
    "info": 2
  },
  "violations": [
    {
      "rule_id": "P002",
      "rule_name": "Current Capacity",
      "severity": "warning",
      "component": "TPS65217",
      "message": "PMIC output current has insufficient margin",
      "recommendation": "Add 20% margin for transient loads"
    }
  ]
}
```

---

### 4. Pin Mux Solver

**POST** `/pinmux/solve`

Solve pin assignment conflicts.

**Request Body**:
```json
{
  "part_id": "uuid",
  "requirements": [
    {
      "function_type": "uart",
      "function_name": "USART1_TX",
      "required": true
    },
    {
      "function_type": "spi",
      "function_name": "SPI1_MOSI",
      "required": true
    }
  ]
}
```

**Response**:
```json
{
  "success": true,
  "assignments": {
    "USART1_TX": {
      "pin_name": "PA9",
      "pin_number": 42,
      "alternate_function": 7
    },
    "SPI1_MOSI": {
      "pin_name": "PA7",
      "pin_number": 31,
      "alternate_function": 5
    }
  },
  "conflicts": [],
  "unassigned": []
}
```

---

### 5. Power Budget Calculator

**POST** `/power/calculate`

Calculate system power consumption and battery life.

**Request Body**:
```json
{
  "part_id": "uuid",
  "mode_profiles": [
    {
      "mode": "run",
      "duration_percent": 10,
      "frequency_mhz": 168
    },
    {
      "mode": "sleep",
      "duration_percent": 80
    },
    {
      "mode": "stop",
      "duration_percent": 10
    }
  ],
  "peripheral_usage": [
    {
      "peripheral_type": "uart",
      "peripheral_instance": "USART1",
      "duty_cycle_percent": 5
    }
  ],
  "external_components": [
    {
      "name": "LED",
      "voltage_v": 3.3,
      "current_ma": 2,
      "duty_cycle_percent": 10
    }
  ],
  "battery_capacity_mah": 2000,
  "battery_chemistry": "Li-Ion"
}
```

**Response**:
```json
{
  "budget": {
    "mcu_power_uw": 5200,
    "peripheral_power_uw": 800,
    "external_power_uw": 660,
    "total_power_uw": 6660,
    "total_current_ma": 2.02
  },
  "battery_life": {
    "capacity_mah": 2000,
    "average_current_ma": 2.02,
    "lifetime_hours": 990,
    "lifetime_days": 41.25,
    "recommendations": [
      "Battery life > 30 days - excellent",
      "MCU consumes 78% of power - consider lower power modes"
    ]
  }
}
```

---

### 6. Firmware Stack Recommendations

**POST** `/firmware/recommend`

Recommend RTOS, middleware, and libraries.

**Request Body**:
```json
{
  "part_id": "uuid",
  "requirements": [
    {
      "stack_type": "rtos",
      "required_features": ["preemptive", "tickless"],
      "license_preference": "permissive"
    },
    {
      "stack_type": "tcp_ip",
      "required_protocols": ["IPv4", "TCP", "UDP", "HTTP"]
    }
  ],
  "max_results": 5
}
```

**Response**:
```json
{
  "recommendations": {
    "rtos": [
      {
        "stack_id": "uuid",
        "stack_name": "FreeRTOS",
        "vendor": "Amazon",
        "version": "10.5.1",
        "license": "MIT",
        "flash_typical_kb": 10,
        "ram_typical_kb": 4,
        "score": 95.0,
        "match_reasons": ["Supports: preemptive, tickless", "Low Flash usage (2%)"],
        "documentation_url": "https://freertos.org/docs"
      }
    ],
    "tcp_ip": [
      {
        "stack_name": "lwIP",
        "vendor": "Community",
        "flash_typical_kb": 40,
        "ram_typical_kb": 16,
        "score": 88.0
      }
    ]
  }
}
```

---

### 7. Reference Design Search

**GET** `/reference-designs/search`

Find reference designs.

**Query Parameters**:
- `mcu_id` (uuid): Find designs using this MCU
- `application` (string): Application area (e.g., "Motor Control", "IoT")
- `manufacturer` (string): Filter by manufacturer

**Response**:
```json
{
  "matches": [
    {
      "design_id": "uuid",
      "design_name": "STM32 IoT Discovery Kit",
      "design_code": "B-L475E-IOT01A",
      "manufacturer": "STMicroelectronics",
      "application_area": "IoT",
      "match_score": 100.0,
      "match_reasons": ["Uses STM32L475VG", "Exact MCU match"],
      "schematic_url": "https://...",
      "bom_url": "https://...",
      "key_parts": [
        {
          "mpn": "STM32L475VGT6",
          "category": "mcu",
          "designator": "U1"
        }
      ]
    }
  ]
}
```

---

## Error Responses

All endpoints return standard error responses:

```json
{
  "error": {
    "code": "INVALID_PART_ID",
    "message": "Part ID not found",
    "details": {}
  }
}
```

**HTTP Status Codes**:
- `200`: Success
- `400`: Bad Request (invalid parameters)
- `404`: Not Found
- `500`: Internal Server Error

---

## Rate Limiting

Current limit: 1000 requests/hour per IP

---

## SDK Examples

### Python
```python
import requests

# Search for parts
response = requests.post('http://localhost:8000/api/v1/search', json={
    'query': 'STM32F4',
    'category': 'mcu',
    'limit': 10
})
parts = response.json()['results']

# Get alternatives
part_id = parts[0]['id']
response = requests.get(f'http://localhost:8000/api/v1/parts/{part_id}/alternatives')
alternatives = response.json()['alternatives']
```

### JavaScript
```javascript
// Search for parts
const response = await fetch('http://localhost:8000/api/v1/search', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    query: 'STM32F4',
    category: 'mcu',
    limit: 10
  })
});
const {results} = await response.json();
```

---

## Changelog

### v1.0.0 (2026-02-11)
- Initial release
- Search, alternatives, DRC, pin mux, power budget, firmware recommendations
- Multi-language support (EN, CN, JP, DE)
- ML-based ranking
