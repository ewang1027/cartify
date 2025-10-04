from pathlib import Path
import numpy as np
from PIL import Image
import coremltools as ct

# Paths
mlpkg = Path("models/DepthAnythingV2SmallF16.mlpackage")
img_path = Path("1642701833484.webp")    # change to your test image
out_depth_npy = Path("out_depth.npy")
out_vis_png = Path("out_depth_vis.png")

# Load Core ML model
mlmodel = ct.models.MLModel(str(mlpkg))

# Inspect IO names (print once so you know exact keys)
spec = mlmodel.get_spec()
in_names = [inp.name for inp in spec.description.input]
out_names = [out.name for out in spec.description.output]
print("Inputs:", in_names)
print("Outputs:", out_names)

# Typical Core ML image model expects an RGB image sized to its input shape.
# Get input shape from the first input description
# (Most Depth Anything Core ML packages use an image input ~518x396; confirm via print above.)
input_name = in_names[0]

# Load and resize image to model's expected size
image_type = spec.description.input[0].type.imageType
W = int(image_type.width) if image_type.width else 518
H = int(image_type.height) if image_type.height else 392
img = Image.open(img_path).convert("RGB").resize((W, H), Image.BILINEAR)

# Run prediction
# For image inputs, coremltools accepts PIL Images in a dict keyed by the input name.
pred = mlmodel.predict({input_name: img})

# Get depth output
# The output key is typically "depth" (confirm from the printed keys).
# It’s a HxW float array (relative depth).
out_key = out_names[0]
depth_img = pred[out_key]
depth = np.array(depth_img, dtype=np.float32)

# Save raw depth and a normalized visualization
np.save(out_depth_npy, depth)
vis = (255 * (depth - depth.min()) / (depth.ptp() + 1e-8)).astype(np.uint8)
Image.fromarray(vis).save(out_vis_png)

print(f"Saved {out_depth_npy} (float32, relative depth) and {out_vis_png} (8-bit viz).")
