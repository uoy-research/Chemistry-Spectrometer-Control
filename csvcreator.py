import csv
from pathlib import Path
import argparse

def create_motor_sequence(start_pos: float, increment: float, num_steps: int,
                         time_per_step: float, output_path: str = r"C:\motor_sequence.csv"):
    """Create a motor sequence CSV file with recursive steps.
    
    Args:
        start_pos: Starting position in mm
        increment: Position increment in mm
        num_steps: Number of steps to generate
        time_per_step: Time per step in seconds
        output_path: Path to save CSV file
    """
    try:
        # Generate sequence
        sequence = []
        current_pos = start_pos
        
        for _ in range(num_steps):
            sequence.append([round(current_pos, 3), round(time_per_step, 3)])
            current_pos -= increment
        
        # Write to CSV
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(sequence)
            
        print(f"Created sequence with {len(sequence)} steps")
        print(f"Saved to: {output_file}")
        
    except Exception as e:
        print(f"Error creating sequence: {e}")

def main():
    parser = argparse.ArgumentParser(description='Create a motor sequence CSV file')
    parser.add_argument('--start', type=float, required=True, help='Starting position (mm)')
    parser.add_argument('--increment', type=float, required=True, help='Position increment (mm)')
    parser.add_argument('--steps', type=int, required=True, help='Number of steps')
    parser.add_argument('--time', type=float, required=True, help='Time per step (seconds)')
    parser.add_argument('--output', type=str, default=r"C:\ssbubble\motor_sequence.csv",
                       help='Output file path')

    args = parser.parse_args()
    
    create_motor_sequence(
        start_pos=args.start,
        increment=args.increment,
        num_steps=args.steps,
        time_per_step=args.time,
        output_path=args.output
    )

if __name__ == "__main__":
    main()
