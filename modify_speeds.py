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

import re
import sys
import logging
import os
import argparse
import math

# Get the directory where the script is located
script_dir = os.path.dirname(os.path.abspath(__file__))

# Configure logging to save in the script's directory
log_file_path = os.path.join(script_dir, "speed_modifier_log.txt")
logging.basicConfig(
    filename=log_file_path,
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s - %(message)s"
)

def calculate_y_component(dx, dy, f):
    """
    Calculate the Y component of speed for a movement.
    
    Args:
        dx (float): X distance of movement
        dy (float): Y distance of movement
        f (float): Total speed (F value) in mm/min
        
    Returns:
        float: Y component of speed in mm/s
    """
    if dx == 0 and dy == 0:
        return 0
    
    total_distance = math.sqrt(dx**2 + dy**2)
    if total_distance == 0:
        return 0
    
    # Calculate ratio of Y movement to total movement
    y_ratio = abs(dy) / total_distance
    
    # Convert F from mm/min to mm/s and calculate Y component
    f_mm_s = f / 60
    y_speed = f_mm_s * y_ratio
    
    return y_speed

def get_adjusted_speed(current_y_speed, min_speed, max_speed, current_f):
    """
    Determine the new speed to avoid the resonance range.
    Chooses the closest boundary: below min_speed or above max_speed.
    
    Args:
        current_y_speed (float): Current Y component speed in mm/s
        min_speed (float): Minimum Y speed to avoid (mm/s)
        max_speed (float): Maximum Y speed to avoid (mm/s)
        current_f (float): Current total speed in mm/min
        
    Returns:
        float: New adjusted speed in mm/min
    """
    # Calculate distance to each boundary
    distance_to_min = current_y_speed - min_speed
    distance_to_max = max_speed - current_y_speed
    
    # Determine which boundary is closer
    if distance_to_min <= distance_to_max:
        # Closer to min_speed, so go just below it
        adjustment_factor = (min_speed - 0.1) / current_y_speed
    else:
        # Closer to max_speed, so go just above it
        adjustment_factor = (max_speed + 0.1) / current_y_speed
    
    # Apply adjustment to the total speed
    new_f = current_f * adjustment_factor
    
    return new_f

def modify_speeds(input_file, min_speed, max_speed):
    """
    Modifies G-code by replacing speeds that would result in Y-axis speeds
    within the specified range, with a speed just below or above the range.
    
    Args:
        input_file (str): Path to the G-code file.
        min_speed (float): Minimum Y speed to avoid (mm/s).
        max_speed (float): Maximum Y speed to avoid (mm/s).
    """
    logging.info(f"Starting G-code speed modification")
    logging.info(f"Input file: {input_file}")
    logging.info(f"Y-speed range to avoid: {min_speed} - {max_speed} mm/s")
    
    changes_count = 0
    
    # Read the input G-code
    with open(input_file, 'r') as infile:
        lines = infile.readlines()
    
    # Process the G-code
    modified_lines = []
    
    # Keep track of current position and speed
    current_x = 0.0
    current_y = 0.0
    current_f = 0.0
    
    for line in lines:
        original_line = line.strip()
        modified = False
        
        # Look for G0/G1 movement commands
        if line.strip().startswith(("G0 ", "G1 ")):
            # Extract X, Y, and F values if present
            x_match = re.search(r'X([-+]?\d*\.?\d+)', line)
            y_match = re.search(r'Y([-+]?\d*\.?\d+)', line)
            f_match = re.search(r'F([\d.]+)', line)
            
            # Get new coordinates
            new_x = float(x_match.group(1)) if x_match else current_x
            new_y = float(y_match.group(1)) if y_match else current_y
            
            # Get speed (F value)
            if f_match:
                current_f = float(f_match.group(1))
            
            # Calculate movement deltas
            dx = new_x - current_x
            dy = new_y - current_y
            
            # If there's movement and we have a speed
            if (dx != 0 or dy != 0) and current_f > 0:
                # Calculate Y component of speed in mm/s
                y_speed = calculate_y_component(dx, dy, current_f)
                
                # Check if Y speed is in the range to avoid
                if min_speed <= y_speed <= max_speed:
                    # Get adjusted speed
                    original_f = current_f
                    adjusted_f = get_adjusted_speed(y_speed, min_speed, max_speed, current_f)
                    current_f = adjusted_f
                    
                    # Calculate new Y component for logging
                    new_y_speed = calculate_y_component(dx, dy, adjusted_f)
                    
                    # Replace the F value in the line
                    if f_match:
                        line = re.sub(r'F[\d.]+', f'F{current_f:.2f}', line)
                    else:
                        line = line.strip() + f' F{current_f:.2f}\n'
                    
                    # Add a comment about the modification
                    direction = "below" if new_y_speed < min_speed else "above"
                    line = line.strip() + f" ; Y-speed modified from {y_speed:.2f} to {new_y_speed:.2f} mm/s ({direction} resonance range)\n"
                    modified = True
                    changes_count += 1
                    logging.info(f"Changed speed from F{original_f:.2f} to F{current_f:.2f} (Y-component from {y_speed:.2f} to {new_y_speed:.2f} mm/s)")
            
            # Update current position
            current_x = new_x
            current_y = new_y
        
        if not modified:
            modified_lines.append(original_line + "\n")
        else:
            modified_lines.append(line)
    
    # Overwrite the input file with the modified G-code
    with open(input_file, 'w') as outfile:
        outfile.writelines(modified_lines)
    
    logging.info(f"G-code processing completed. {changes_count} speed changes made.")
    logging.info(f"Log file saved at {log_file_path}")

# Main execution
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Modify print speeds in G-code files to avoid specific Y-axis speeds.")
    parser.add_argument("input_file", help="Path to the input G-code file")
    parser.add_argument("-minSpeed", type=float, default=90, help="Minimum Y speed to avoid (mm/s)")
    parser.add_argument("-maxSpeed", type=float, default=100, help="Maximum Y speed to avoid (mm/s)")
    args = parser.parse_args()

    modify_speeds(
        input_file=args.input_file,
        min_speed=args.minSpeed,
        max_speed=args.maxSpeed,
    )