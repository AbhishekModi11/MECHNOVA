# CNC Manufacturing & CAD Geometry Concepts for Beginners

Welcome to the **CAD-to-CNC Optimization Engine**. This guide explains the core concepts in plain, beginner-friendly terms.

---

## 1. Boundary Representation (B-Rep) vs Meshes

### Meshes (Like STL files used in 3D Printing)
A mesh breaks 3D objects into thousands of tiny flat triangles.
- **Problem for CNC**: A cylinder becomes a faceted polygon. The computer loses the exact mathematical radius, center, and axis of a drilled hole.

### B-Rep (Like STEP files used in CNC & CAD)
B-Rep stores shapes using exact analytic equations:
- A flat face is defined by a true plane.
- A hole is defined by an exact mathematical cylinder with a precise radius (e.g., $5.000$ mm) and axis vector.
- **Why this matters**: A CNC drill requires the exact center point and diameter to match physical drill bits. B-Rep retains this mathematical truth.

---

## 2. Faces, Edges, and the Adjacency Graph

A 3D CAD solid is assembled like a paper origami sculpture:
- **Face**: A smooth surface bounded by edges.
- **Edge**: The boundary line where two faces touch.
- **Face Adjacency Graph**: A network map where each face is a node (dot) and each shared edge is a connection (line).
Our engine scans this network map to find recognizable engineering shapes.

---

## 3. Concave vs Convex Edges

When two faces meet at an edge:
- **Convex Edge (Outer Edge)**: Points outward like the corner of a table. If you run your hand along it, you could bump into it.
- **Concave Edge (Inner Corner)**: Points inward like the corner of a room where the wall meets the floor.
- **Why this matters**:
  - The floor of a pocket is surrounded by **concave edges** meeting the side walls.
  - The outer boundary of a raw block is made of **convex edges**.

---

## 4. Holes vs Shafts (Bosses)

Both a hole and a cylindrical boss (shaft) have cylindrical surfaces. How does the software tell them apart?
- **Hole (Internal)**: Material is **outside** the cylinder; the inside is hollow air. The surface normal (pointing away from material) points towards the central axis.
- **Shaft / Boss (External)**: Material is **inside** the cylinder; the outside is open air. The surface normal points away from the central axis.
- **Classification probe**: We mathematically probe a point slightly off the surface to confirm whether it is inside or outside the solid body.

---

## 5. From Features to CNC Operations

Machining cannot happen all at once; it happens in steps called **operations**:

| Detected Feature | CNC Operation | Tool Used | Action |
|---|---|---|---|
| Top planar face | **Facing** | Face Mill / Large End Mill | Skims top raw stock flat to set Z zero. |
| Cylindrical hole ($D \le 12$ mm) | **Drilling / Pecking** | Twist Drill | Plunges down the center axis. |
| Recessed area with floor & walls | **Pocket Clearing** | Flat End Mill | Spiral/offset toolpaths remove material inside walls. |
| Narrow channel | **Slot Milling** | Flat End Mill | Single or dual pass along channel centerline. |
| Sharp internal vertical corner | **Corner Warning** | Smaller End Mill | Circular rotating tools cannot cut square inside corners. |

---

## 6. Speeds and Feeds

Cutting metal or plastic requires balancing tool rotation and movement:
- **Spindle Speed ($S$, RPM)**: How fast the motor spins the tool. Too fast burns the tool; too slow dulls it.
  $$S = \frac{1000 \times V_c}{\pi \times D}$$
  ($V_c$ is surface cutting speed in m/min; $D$ is tool diameter in mm).
- **Feed Rate ($F$, mm/min)**: How fast the table slides the part into the spinning cutter.
  $$F = S \times z \times f_z$$
  ($z$ is number of cutting teeth; $f_z$ is the thickness of each bite/chip).
- **Stepdown ($\Delta Z$)**: How deep the cutter bites on each horizontal layer (e.g., 2 mm per level).
- **Stepover ($\Delta XY$)**: How much the cutter overlaps its previous pass (typically 40% to 70% of cutter diameter).

---

## 7. The Traveling Salesperson Problem (2-Opt)

When drilling 20 holes, in what order should the CNC machine drill them?
- If drilled randomly, the machine spends minutes flying back and forth in empty air (**rapid travel**).
- We use the **Nearest Neighbor** algorithm followed by **2-Opt route optimization** to find the shortest travel path, reducing air-time and cycle time.
