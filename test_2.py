
import pandas as pd
df = pd.read_csv('test_2.csv')
print(df)

# Sort the data by start position
data = df.sort_values('start')

# Initialize lists to store the cleaned data
cleaned_items = []
cleaned_starts = []
cleaned_ends = []

# Define the correct order of items
correct_order = ['item1a', 'item1b', 'item1c', 'item7', 'item7a', 'item8', 'item9']

# Initialize variables to keep track of the last valid position and item
last_end = 0
last_item = None

# Iterate through the correct order
for item in correct_order:
    # Find all rows for the current item
    item_rows = data[data['item'].str.startswith(item)]
    
    for _, row in item_rows.iterrows():
        # Check if the current start is greater than the last end
        if row['start'] > last_end:
            # For item1b, check if it starts at least 100000 after item1a
            if item == 'item1b' and last_item == 'item1a' and row['start'] < last_end + 100000:
                continue
            
            # Add the item to the cleaned data
            cleaned_items.append(row['item'])
            cleaned_starts.append(row['start'])
            cleaned_ends.append(row['end'])
            
            # Update the last end position and item
            last_end = row['end']
            last_item = item
            
            # Break the loop as we only want one instance of each item
            break

# Create a new DataFrame with the cleaned data
cleaned_data = pd.DataFrame({
    'item': cleaned_items,
    'start': cleaned_starts,
    'end': cleaned_ends
})

# Display the cleaned data
print(cleaned_data)