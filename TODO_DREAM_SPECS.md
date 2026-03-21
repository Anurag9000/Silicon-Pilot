# HardwareGenius - Remaining Dream Specs TODO

The following features represent the final core intelligence capabilities to be implemented, bringing the system to its ultimate "vision" state.

## 1. Context-Aware Component Selection 
*   **What's missing**: The system currently ranks parts based purely on hardware specs (flash, speed, price). It lacks the "human context" awareness.
*   **The Dream**: The AI should re-rank or override deterministic ML rankings based on qualitative user context—like understanding if you are a student on a tight budget vs. an enterprise team needing long-term supply chain stability, or if you need rapid prototyping (favoring easy ecosystems) vs. high-volume production (favoring raw cost).

## 2. Smart BOM Compatibility Checking
*   **What's missing**: The system recommends parts, but doesn't cross-validate the entire board.
*   **The Dream**: A deep, cross-component validation engine. The LLM needs to look at the entire Bill of Materials and say, *"Warning: The PMIC power sequencing you selected doesn't match the MCU's required power-on reset timings,"* or *"You are missing bootstrap capacitors for this specific LDO."* It should check thermal constraints, electrical interfacing, and signal overlaps.

## 3. LLM-Driven Configuration Generation (CubeMX Integration)
*   **What's missing**: Currently, we only have deterministic static stubs for clock trees and pin assignments.
*   **The Dream**: The LLM intelligence should automatically map the abstract pin assignments and power modes into a concrete, downloadable `.ioc` file (STM32CubeMX format) or generate detailed C/C++ firmware scaffolding ready to be compiled.

## 4. Design Review and Suggestions (AI Peer Review)
*   **What's missing**: There is no final "sanity check" on the overall architecture. 
*   **The Dream**: An automated "Architect's Review" pass. Before you finalize the BOM, an AI agent acting as a Senior Hardware Engineer reviews the entire generated design against common real-world failures and provides an "Architect's Notes" summary (e.g., *"You selected a 480MHz MCU for a simple environmental logger; this is massive overkill and will drain your battery in hours."*).
