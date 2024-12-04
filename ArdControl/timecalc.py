from datetime import timedelta

# Define the working hours and minutes for one working day
hours_per_day = 7
minutes_per_day = 24

# Calculate the total time for 4 working days
total_days = 20 * 0.8
total_hours = total_days * hours_per_day
total_minutes = total_days * minutes_per_day

# Convert the total time to hours and minutes
total_time = timedelta(hours=total_hours, minutes=total_minutes)

# Extract hours and minutes from the timedelta
total_seconds = total_time.total_seconds()
hours, remainder = divmod(total_seconds, 3600)
minutes = remainder // 60

# Format the result as HH:MM
formatted_time = f"{int(hours):02}:{int(minutes):02}"

print(formatted_time)
