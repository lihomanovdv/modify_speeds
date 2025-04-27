# Speed Modifier Script
# Copyright (c) 2025 Lihomanov Daniil https://github.com/lihomanovdv
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# ADDITIONAL TERMS: Commercial use of this software is explicitly prohibited.
# This restriction applies to the original code and all derivatives.

#!/usr/bin/env python3
import argparse
import logging
import os
import re
import math
import datetime
import sys
from typing import Tuple, List, Optional

# Script setup
script_dir = os.path.dirname(os.path.abspath(__file__))
log_file_path = os.path.join(script_dir, 'y_speed_range_avoidance_log.txt')
logging.basicConfig(
    filename=log_file_path, 
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def parse_g1_command(line: str) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float], Optional[float]]:
    """Parse G1 command to extract X, Y, Z, E, and F parameters."""
    x = re.search(r'X([-+]?\d*\.?\d+)', line)
    y = re.search(r'Y([-+]?\d*\.?\d+)', line)
    z = re.search(r'Z([-+]?\d*\.?\d+)', line)
    e = re.search(r'E([-+]?\d*\.?\d+)', line)
    f = re.search(r'F([-+]?\d*\.?\d+)', line)
    
    return (
        float(x.group(1)) if x else None,
        float(y.group(1)) if y else None,
        float(z.group(1)) if z else None,
        float(e.group(1)) if e else None,
        float(f.group(1)) if f else None
    )

def calculate_y_component_speed(dx: float, dy: float, speed: float) -> float:
    """Calculate Y component of a diagonal move's speed."""
    if dx == 0 and dy == 0:
        return 0
    
    move_distance = math.sqrt(dx**2 + dy**2)
    if move_distance == 0:
        return 0
        
    y_proportion = abs(dy) / move_distance
    y_speed = speed * y_proportion
    
    return y_speed

def adjust_speed_outside_range(speed: float, min_range: float, max_range: float) -> float:
    """Adjust speed to be outside the specified range."""
    if speed < min_range or speed > max_range:
        return speed  # Already outside range
    
    # Calculate distance to each boundary
    dist_to_min = speed - min_range
    dist_to_max = max_range - speed
    
    # Adjust to nearest boundary
    if dist_to_min <= dist_to_max:
        return min_range - 1  # Go below minimum
    else:
        return max_range + 1  # Go above maximum

def adjust_extrusion_for_speed_change(e_value: float, original_speed: float, new_speed: float) -> float:
    """Adjust extrusion amount based on speed change."""
    if original_speed == 0:
        return e_value
    
    ratio = original_speed / new_speed
    return e_value * ratio

def process_gcode(input_file: str, min_range: float, max_range: float) -> None:
    """Process the G-code file to avoid Y speeds in the specified range."""
    logging.info(f'Processing file: {input_file}')
    logging.info(f'Avoiding Y speeds between {min_range} and {max_range} mm/s')
    
    # Variables to track state
    last_x, last_y = 0.0, 0.0
    last_speed = 0.0
    modifications_count = 0
    
    try:
        # Read all lines from the file
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Process lines and modify as needed
        for i in range(len(lines)):
            line = lines[i]
            
            # Skip comments and non-movement commands
            if not line.strip() or line.strip().startswith(';') or not line.strip().startswith('G1'):
                continue
                
            x, y, z, e, f = parse_g1_command(line)
            
            # Update speed if specified
            if f is not None:
                last_speed = f / 60  # Convert from mm/min to mm/s
            
            # Only process movement commands with Y component and speed
            if y is not None and last_speed > 0:
                dx = 0 if x is None else x - last_x
                dy = y - last_y
                
                # Calculate Y component of speed
                y_speed = calculate_y_component_speed(dx, dy, last_speed)
                
                # If Y speed is in the avoided range, adjust the overall speed
                if min_range <= y_speed <= max_range:
                    new_speed = adjust_speed_outside_range(y_speed, min_range, max_range)
                    speed_ratio = new_speed / y_speed
                    new_overall_speed = last_speed * speed_ratio
                    
                    # Adjust extrusion if present
                    if e is not None:
                        new_e = adjust_extrusion_for_speed_change(e, last_speed, new_overall_speed)
                        e_str = f'E{new_e:.5f}'
                        line = re.sub(r'E[-+]?\d*\.?\d+', e_str, line)
                    
                    # Update speed in the G-code
                    new_f = new_overall_speed * 60  # Convert back to mm/min
                    f_str = f'F{new_f:.1f}'
                    
                    if 'F' in line:
                        line = re.sub(r'F[-+]?\d*\.?\d+', f_str, line)
                    else:
                        line = line.rstrip() + f' {f_str}\n'
                    
                    # Add comment about modification
                    line = line.rstrip() + f' ; Y-speed adjusted from {y_speed:.2f} to {new_speed:.2f} mm/s\n'
                    lines[i] = line
                    
                    modifications_count += 1
                    logging.info(f'Line modified: Y-speed {y_speed:.2f} → {new_speed:.2f} mm/s')
            
            # Update position tracking
            if x is not None:
                last_x = x
            if y is not None:
                last_y = y
        
        # Write modified content back to file
        with open(input_file, 'w', encoding='utf-8') as f:
            f.writelines(lines)
            
        logging.info(f'Processing complete. Made {modifications_count} modifications.')
        
    except Exception as e:
        logging.error(f'Error processing file: {str(e)}')
        print(f'Error: {str(e)}')
        sys.exit(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Modify G-code to avoid specific Y-axis speed range')
    parser.add_argument('input_file', help='Input G-code file')
    parser.add_argument('-min', type=float, default=90, help='Minimum speed to avoid (mm/s)')
    parser.add_argument('-max', type=float, default=110, help='Maximum speed to avoid (mm/s)')
    
    args = parser.parse_args()
    
    logging.info('='*50)
    logging.info(f'Script started at {datetime.datetime.now()}')
    
    process_gcode(args.input_file, args.min, args.max)
