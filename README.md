# modify_speeds
Script for modifying Y speed for 3d printers

## Description
The G-Code Speed Modifier is a Python script designed to eliminate 3D printer resonance and vibration issues by modifying printing speeds in G-code files. This tool automatically adjusts speeds that would cause unwanted vibrations in your 3D printer, improving print quality without manual G-code editing.

## Purpose
Many 3D printers experience resonance at specific speeds, which can result in visible artifacts on printed objects ("ghosting" or "ringing"). This script identifies movement commands that would operate within problematic speed ranges and automatically adjusts them to the nearest "safe" speed - either just below the minimum or just above the maximum of the resonance range.

## What It Does
### The script:

Analyzes G-code files to identify movement commands
Calculates the Y-component speed for each movement
Detects when this speed falls within a user-defined resonance range
Automatically adjusts the speed to avoid the problematic range, choosing the closest boundary
Adds comments to the G-code to track modifications
Generates a detailed log file of all changes
By avoiding speeds that cause resonance, the script helps produce cleaner prints with fewer artifacts, without requiring manual editing or slicer reconfiguration.

## Key Features
Simple command-line interface
Customizable resonance speed range
Smart speed adjustment that chooses the nearest boundary
Comprehensive logging
Works with any G-code file regardless of which slicer generated it

Change the path to python and to the script file to your own.
Find it via cmd -> where python

"C:\Users\...\AppData\Local\Programs\Python\Python313\python.exe" "E:\...\modify_speeds.py" -min 90 -max 110;
