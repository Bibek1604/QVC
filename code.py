import pandas as pd
import barcode
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont
import os

# Output directory setup
output_dir = 'new'
final_design_dir = os.path.join(output_dir, 'final_design')  # Final designs folder
os.makedirs(final_design_dir, exist_ok=True)

# Load data from Excel
try:
    data = pd.read_excel('ALDAR-Barcode-1st Lot.xlsx')  # Path to your Excel file
except Exception as e:
    print(f"Error loading Excel file: {e}")
    exit()

# Limit data to the first 10,000 entries
data = data.head(10000)

# Design file
designs = {'back': 'practise.png'}
for part, design in designs.items():
    if not os.path.exists(design):
        print(f"Warning: {part.capitalize()} design file {design} does not exist.")
        exit()

# Function to create a barcode without a unique ID below it
def create_barcode_without_id(unique_number):
    try:
        code128 = barcode.get_barcode_class('code128')
        barcode_instance = code128(str(unique_number), writer=ImageWriter())
        options = {
            "module_width": 4,
            "module_height": 60.0,
            "quiet_zone": 8,
            "dpi": 300
        }
        barcode_img = barcode_instance.render(writer_options=options)
        return barcode_img
    except Exception as e:
        print(f"Error creating barcode for {unique_number}: {e}")
        return None

# Function to create the back design with barcode and REFNO
def create_design_with_barcode(refno, back_design_path):
    try:
        back_design = Image.open(back_design_path).convert('RGB')
        barcode_img = create_barcode_without_id(refno)
        if barcode_img is None:
            return None

        # Resize barcode image
        barcode_img = barcode_img.resize((260, 120), Image.Resampling.LANCZOS)

        design_width, design_height = back_design.size
        barcode_width, barcode_height = barcode_img.size

        # Adjust barcode position
        barcode_position = (
            (design_width - barcode_width) // 2 + 20,
            (design_height - barcode_height) // 2 - 50
        )

        # Paste barcode image on the back design
        back_design.paste(barcode_img, barcode_position)

        # Draw the REFNO below the barcode
        draw = ImageDraw.Draw(back_design)
        try:
            font = ImageFont.truetype("arial.ttf", 30)
        except IOError:
            font = ImageFont.load_default()

        text = str(refno)
        text_width, text_height = draw.textbbox((0, 0), text, font=font)[2:]

        text_position = (
            (design_width - text_width) // 2 + 20,
            barcode_position[1] + barcode_height + 10
        )

        draw.text(text_position, text, fill="black", font=font)

        # Save the design
        output_path = os.path.join(final_design_dir, f"{refno}_back.png")
        back_design.save(output_path, quality=100, optimize=True)
        return output_path
    except Exception as e:
        print(f"Error creating design for {refno}: {e}")
        return None

# Function to generate a 12x18-inch page with designs
def generate_pages(data, designs, batch_size=200):
    PAGE_WIDTH = 12 * 300
    PAGE_HEIGHT = 18 * 300
    DESIGN_WIDTH = int(92 * 300 / 25.4)
    DESIGN_HEIGHT = int(54 * 300 / 25.4)
    MARGIN = 20

    columns = (PAGE_WIDTH - MARGIN) // (DESIGN_WIDTH + MARGIN)
    rows = (PAGE_HEIGHT - MARGIN) // (DESIGN_HEIGHT + MARGIN)
    designs_per_page = columns * rows

    current_page = 1
    generated_barcodes = []

    for batch_start in range(0, len(data), batch_size):
        batch = data.iloc[batch_start:batch_start + batch_size]
        page = Image.new("RGB", (PAGE_WIDTH, PAGE_HEIGHT), "white")
        current_row, current_col = 0, 0

        for index, row in batch.iterrows():
            refno = row.get('REFNO')  # Updated from 'UNIQUENUMBER'
            if pd.isna(refno):
                print(f"Skipping row {index}: 'REFNO' is missing.")
                continue

            design_path = create_design_with_barcode(refno, designs['back'])
            if not design_path:
                continue

            try:
                design = Image.open(design_path)
                design = design.resize((DESIGN_WIDTH, DESIGN_HEIGHT), Image.Resampling.LANCZOS)
                generated_barcodes.append({'REFNO': refno, 'DesignPath': design_path})  # Updated column name
            except Exception as e:
                print(f"Error loading design for {refno}: {e}")
                continue

            x_pos = MARGIN + current_col * (DESIGN_WIDTH + MARGIN)
            y_pos = MARGIN + current_row * (DESIGN_HEIGHT + MARGIN)
            page.paste(design, (x_pos, y_pos))

            current_col += 1
            if current_col >= columns:
                current_col = 0
                current_row += 1

            if current_row >= rows:
                output_path = os.path.join(output_dir, f"Final_Design_Page_{current_page}.png")
                page.save(output_path, quality=100)
                print(f"Page {current_page} saved at {output_path}")
                page = Image.new("RGB", (PAGE_WIDTH, PAGE_HEIGHT), "white")
                current_row, current_col = 0, 0
                current_page += 1

        if current_row > 0 or current_col > 0:
            output_path = os.path.join(output_dir, f"Final_Design_Page_{current_page}.png")
            page.save(output_path, quality=100)
            print(f"Page {current_page} saved at {output_path}")
            current_page += 1

    output_mapping = os.path.join(output_dir, 'barcode_mapping.csv')
    pd.DataFrame(generated_barcodes).to_csv(output_mapping, index=False)
    print(f"Mapping saved at {output_mapping}")

# Generate designs and pages
generate_pages(data, designs)
